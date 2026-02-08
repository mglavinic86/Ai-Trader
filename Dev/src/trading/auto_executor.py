"""
Auto-Executor - Automatic trade execution for auto-trading.

Receives signals from MarketScanner and executes them automatically
after passing all safety checks.

Usage:
    from src.trading.auto_executor import AutoExecutor

    executor = AutoExecutor(order_manager, risk_manager, config)
    result = executor.execute_signal(signal)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from collections import deque

from src.trading.orders import OrderManager, OrderResult
from src.trading.risk_manager import RiskManager, ValidationResult
from src.trading.emergency import emergency_controller
from src.trading.auto_scanner import TradingSignal
from src.trading.position_sizer import calculate_position_size
from src.core.auto_config import AutoTradingConfig, HardLimits, save_auto_config
from src.analysis.llm_engine import LLMEngine, SignalValidation
from src.utils.database import db
from src.utils.logger import logger


@dataclass
class ExecutionResult:
    """Result of an auto-execution attempt."""
    signal: TradingSignal
    executed: bool
    order_result: Optional[OrderResult] = None
    skip_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "instrument": self.signal.instrument,
            "direction": self.signal.direction,
            "confidence": self.signal.confidence,
            "executed": self.executed,
            "order_id": self.order_result.order_id if self.order_result else None,
            "skip_reason": self.skip_reason,
            "timestamp": self.timestamp.isoformat()
        }


class AutoExecutor:
    """
    Automatic trade executor for auto-trading.

    Receives signals and executes them after validation.
    Tracks execution history and manages cooldown.
    """

    def __init__(
        self,
        order_manager: OrderManager,
        risk_manager: RiskManager,
        config: AutoTradingConfig
    ):
        """
        Initialize executor.

        Args:
            order_manager: OrderManager for trade execution
            risk_manager: RiskManager for validation
            config: Auto-trading configuration
        """
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.config = config

        # AI validation engine
        self.llm_engine = LLMEngine()
        if self.config.ai_validation.enabled:
            available, reason = self.llm_engine.status()
            if available:
                logger.info("AI Validation ENABLED - Claude will validate each trade")
            else:
                logger.warning(f"AI Validation configured but unavailable: {reason}")

        # Execution tracking
        self._execution_history: deque = deque(maxlen=100)
        self._daily_trades: Dict[str, int] = {}  # instrument -> count today
        self._loss_streak = 0
        self._cooldown_until: Optional[datetime] = None
        self._last_reset_date: Optional[datetime] = None

        # STOP DAY tracking
        self._daily_losses: int = 0
        self._stop_day_active: bool = False

        # Pending limit orders tracking: instrument -> {order_ticket, signal, placed_at, expiry_minutes}
        self._pending_orders: Dict[str, dict] = {}

        # Rebuild pending orders from MT5 on startup
        self._rebuild_pending_orders()

        # Statistics
        self._stats = {
            "total_executed": 0,
            "total_skipped": 0,
            "total_pnl": 0.0,
            "wins": 0,
            "losses": 0
        }

        logger.info("AutoExecutor initialized")

    def execute_signal(self, signal: TradingSignal) -> ExecutionResult:
        """
        Execute a trading signal.

        Args:
            signal: Signal from MarketScanner

        Returns:
            ExecutionResult with execution details
        """
        # Reset daily counters if new day
        self._check_daily_reset()

        # 1. Check emergency stop
        if emergency_controller.is_stopped():
            return self._create_skip_result(signal, "Emergency stop active")

        # 2. Check STOP DAY
        if self._stop_day_active:
            return self._create_skip_result(
                signal,
                f"STOP DAY active ({self._daily_losses} losses today). Trading resumes tomorrow."
            )

        # 3. Check dry run mode
        if self.config.dry_run:
            logger.info(f"DRY RUN: Would execute {signal.instrument} {signal.direction}")
            return self._create_skip_result(signal, "Dry run mode - not executing")

        # 4. Check cooldown
        if self._is_in_cooldown():
            return self._create_skip_result(
                signal,
                f"In cooldown until {self._cooldown_until.isoformat()}"
            )

        # 5. Check daily trade limits
        can_trade, limit_reason = self._check_trade_limits(signal.instrument)
        if not can_trade:
            return self._create_skip_result(signal, limit_reason)

        # 6. Run full validation
        validation_ok, validation_reason = self._validate_signal(signal)
        if not validation_ok:
            return self._create_skip_result(signal, validation_reason)

        # 7. Calculate position size
        size_result = self._calculate_position_size(signal)
        if not size_result["can_trade"]:
            return self._create_skip_result(signal, f"Position sizing: {size_result['reason']}")

        units = size_result["units"]
        if signal.direction == "SHORT":
            units = -units

        # 8. AI VALIDATION - Claude decides!
        if self.config.should_use_ai_validation():
            ai_result = self._validate_with_ai(signal)
            if ai_result is None:
                # AI call failed
                if self.config.ai_validation.reject_on_failure:
                    return self._create_skip_result(signal, "AI validation failed (API error)")
                else:
                    logger.warning("AI validation failed, proceeding without it")
            elif not ai_result.approved:
                # AI rejected the trade
                db.log_activity({
                    "activity_type": "AI_REJECTED",
                    "instrument": signal.instrument,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "decision": "REJECT",
                    "reasoning": f"AI REJECTED: {ai_result.reasoning}",
                    "details": {
                        "ai_decision": ai_result.decision,
                        "ai_reasoning": ai_result.reasoning,
                        "ai_confidence_adjustment": ai_result.confidence_adjustment,
                        "ai_model": ai_result.model,
                        "ai_latency_ms": ai_result.latency_ms
                    }
                })
                return self._create_skip_result(signal, f"AI REJECTED: {ai_result.reasoning}")
            else:
                # AI approved!
                logger.info(f"AI APPROVED: {signal.instrument} {signal.direction} - {ai_result.reasoning}")
                db.log_activity({
                    "activity_type": "AI_APPROVED",
                    "instrument": signal.instrument,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "decision": "APPROVE",
                    "reasoning": f"AI APPROVED: {ai_result.reasoning}",
                    "details": {
                        "ai_decision": ai_result.decision,
                        "ai_reasoning": ai_result.reasoning,
                        "ai_confidence_adjustment": ai_result.confidence_adjustment,
                        "ai_model": ai_result.model,
                        "ai_latency_ms": ai_result.latency_ms
                    }
                })

        # 9. Execute trade (limit or market)
        try:
            if signal.use_limit_entry and signal.limit_price:
                # === LIMIT ENTRY: Place pending order ===
                expiry_minutes = self.config.limit_entry.expiry_minutes if hasattr(self.config, 'limit_entry') else 60

                if self.config.dry_run:
                    logger.info(
                        f"DRY RUN: Would place LIMIT ORDER {signal.instrument} {signal.direction} "
                        f"@ {signal.limit_price:.5f} (expiry {expiry_minutes}min)"
                    )
                    return self._create_skip_result(signal, "Dry run mode - would place limit order")

                order_result = self.order_manager.place_pending_order(
                    instrument=signal.instrument,
                    units=units,
                    limit_price=signal.limit_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    expiry_minutes=expiry_minutes,
                    confidence=signal.confidence,
                    risk_amount=size_result["risk_amount"],
                )

                if order_result.success:
                    # Track the pending order
                    self._pending_orders[signal.instrument] = {
                        "order_ticket": int(order_result.order_id),
                        "instrument": signal.instrument,
                        "direction": signal.direction,
                        "limit_price": signal.limit_price,
                        "stop_loss": signal.stop_loss,
                        "take_profit": signal.take_profit,
                        "units": units,
                        "confidence": signal.confidence,
                        "placed_at": datetime.now(timezone.utc).isoformat(),
                        "expiry_minutes": expiry_minutes,
                    }

                    logger.info(
                        f"LIMIT ORDER PLACED: {signal.instrument} {signal.direction} "
                        f"@ {signal.limit_price:.5f} order=#{order_result.order_id}"
                    )

                    db.log_activity({
                        "activity_type": "LIMIT_ORDER_PLACED",
                        "instrument": signal.instrument,
                        "direction": signal.direction,
                        "confidence": signal.confidence,
                        "decision": "LIMIT_ORDER",
                        "reasoning": f"Limit order placed @ {signal.limit_price:.5f}, expires in {expiry_minutes}min",
                        "details": {
                            "order_id": order_result.order_id,
                            "limit_price": signal.limit_price,
                            "entry_zone": list(signal.entry_zone) if signal.entry_zone else None,
                            "stop_loss": signal.stop_loss,
                            "take_profit": signal.take_profit,
                            "risk_reward": signal.risk_reward,
                            "expiry_minutes": expiry_minutes,
                        }
                    })

                    # Record as execution (pending)
                    self._record_execution(signal, order_result)
                    self._handle_learning_mode_increment()

                    return ExecutionResult(
                        signal=signal,
                        executed=True,
                        order_result=order_result
                    )
                else:
                    return self._create_skip_result(
                        signal,
                        f"Limit order failed: {order_result.error}"
                    )

            else:
                # === MARKET ENTRY: Existing behavior ===
                order_result = self.order_manager.open_position(
                    instrument=signal.instrument,
                    units=units,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    confidence=signal.confidence,
                    risk_amount=size_result["risk_amount"]
                )

                if order_result.success:
                    self._record_execution(signal, order_result)
                    logger.info(
                        f"AUTO TRADE EXECUTED: {signal.instrument} {signal.direction} "
                        f"units={units} conf={signal.confidence}%"
                    )

                    # Log to activity - TRADE EXECUTED
                    db.log_activity({
                        "activity_type": "TRADE_EXECUTED",
                        "instrument": signal.instrument,
                        "direction": signal.direction,
                        "confidence": signal.confidence,
                        "decision": "EXECUTE",
                        "reasoning": f"Trade opened successfully! Order #{order_result.order_id}, Units: {abs(units)}, Risk: {size_result['risk_amount']:.2f}",
                        "trade_id": order_result.trade_id,
                        "details": {
                            "order_id": order_result.order_id,
                            "trade_id": order_result.trade_id,
                            "units": abs(units),
                            "entry_price": signal.entry_price,
                            "stop_loss": signal.stop_loss,
                            "take_profit": signal.take_profit,
                            "risk_reward": signal.risk_reward,
                            "risk_amount": size_result["risk_amount"],
                            "confidence": signal.confidence
                        }
                    })

                    # Update trade source to AUTO_SCALPING (trade already logged by orders.py)
                    try:
                        db.update_trade_source(order_result.trade_id, "AUTO_SCALPING")
                    except Exception as e:
                        logger.warning(f"Could not update trade source: {e}")

                    # Increment learning mode trade counter
                    self._handle_learning_mode_increment()

                    return ExecutionResult(
                        signal=signal,
                        executed=True,
                        order_result=order_result
                    )
                else:
                    return self._create_skip_result(
                        signal,
                        f"Order failed: {order_result.error}"
                    )

        except Exception as e:
            logger.exception(f"Execution error for {signal.instrument}")
            return self._create_skip_result(signal, f"Exception: {e}")

    def _validate_with_ai(self, signal: TradingSignal) -> Optional[SignalValidation]:
        """
        Validate signal using Claude AI.

        Args:
            signal: The trading signal to validate

        Returns:
            SignalValidation or None if failed
        """
        try:
            # Build signal data for AI (with SMC data)
            signal_data = {
                "instrument": signal.instrument,
                "direction": signal.direction,
                "confidence": signal.confidence,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "risk_reward": signal.risk_reward,
                "technical": {
                    "trend": signal.technical.trend if hasattr(signal.technical, 'trend') else "N/A",
                    "rsi": signal.technical.rsi if hasattr(signal.technical, 'rsi') else 0,
                    "macd_trend": signal.technical.macd_trend if hasattr(signal.technical, 'macd_trend') else "N/A",
                    "atr_pips": signal.technical.atr_pips if hasattr(signal.technical, 'atr_pips') else 0,
                },
                "sentiment": signal.sentiment.sentiment_score if hasattr(signal.sentiment, 'sentiment_score') else 0,
                "bull_case": signal.confidence_result.bull_case if hasattr(signal.confidence_result, 'bull_case') else "",
                "bear_case": signal.confidence_result.bear_case if hasattr(signal.confidence_result, 'bear_case') else "",
                "smc": signal.smc_analysis.to_dict() if hasattr(signal, 'smc_analysis') and signal.smc_analysis else {},
            }

            logger.info(f"Requesting AI validation for {signal.instrument} {signal.direction}...")
            result = self.llm_engine.validate_signal(signal_data)

            if result:
                logger.info(
                    f"AI Validation: {result.decision} ({result.latency_ms}ms) - {result.reasoning[:50]}..."
                )
            return result

        except Exception as e:
            logger.error(f"AI validation error: {e}")
            return None

    def _handle_learning_mode_increment(self) -> None:
        """Increment learning mode trade counter and handle graduation."""
        if not self.config.learning_mode.is_in_learning():
            return

        graduated = self.config.learning_mode.increment_trade_count()

        # Save updated config
        if save_auto_config(self.config):
            logger.info(
                f"Learning mode: {self.config.learning_mode.current_trades}/"
                f"{self.config.learning_mode.target_trades} trades"
            )
        else:
            logger.warning("Failed to save learning mode progress")

        if graduated:
            logger.info(
                f"LEARNING MODE GRADUATED! Completed {self.config.learning_mode.target_trades} trades. "
                f"Switching to production settings."
            )
            db.log_activity({
                "activity_type": "LEARNING_GRADUATED",
                "reasoning": f"Learning mode complete! Reached {self.config.learning_mode.target_trades} trades.",
                "details": {
                    "total_trades": self.config.learning_mode.current_trades,
                    "target_trades": self.config.learning_mode.target_trades,
                    "new_threshold": self.config.learning_mode.production_settings.get("min_confidence_threshold"),
                    "new_cooldown_minutes": self.config.learning_mode.production_settings.get("cooldown_minutes")
                }
            })

    def _rebuild_pending_orders(self) -> None:
        """Rebuild pending orders tracking from MT5 on startup."""
        try:
            pending = self.order_manager.get_pending_orders()
            for order in pending:
                if order.get("instrument"):
                    self._pending_orders[order["instrument"]] = {
                        "order_ticket": order["order_ticket"],
                        "instrument": order["instrument"],
                        "direction": order.get("direction", "UNKNOWN"),
                        "limit_price": order["price"],
                        "stop_loss": order.get("sl"),
                        "take_profit": order.get("tp"),
                        "units": 0,
                        "confidence": 0,
                        "placed_at": order.get("time_setup", datetime.now(timezone.utc).isoformat()),
                        "expiry_minutes": 60,
                    }
            if pending:
                logger.info(f"Rebuilt {len(pending)} pending orders from MT5")
        except Exception as e:
            logger.warning(f"Could not rebuild pending orders: {e}")

    def check_pending_orders(self) -> List[dict]:
        """
        Check status of all tracked pending orders.

        Returns:
            List of events: {"type": "FILLED"/"EXPIRED", "instrument": ..., ...}
        """
        events = []
        instruments_to_remove = []

        for instrument, pending in self._pending_orders.items():
            order_ticket = pending["order_ticket"]
            try:
                # Check if order still exists in MT5
                import MetaTrader5 as mt5
                orders = mt5.orders_get(ticket=order_ticket)
                order_exists = orders is not None and len(orders) > 0

                if order_exists:
                    # Order still pending - check internal expiry as backup
                    continue

                # Order gone - check if it was filled (position exists)
                symbol = self.order_manager.client._convert_symbol(instrument)
                positions = mt5.positions_get(symbol=symbol)
                position_exists = positions is not None and len(positions) > 0

                if position_exists:
                    # FILLED: Order converted to position
                    event = {
                        "type": "FILLED",
                        "instrument": instrument,
                        "direction": pending["direction"],
                        "order_ticket": order_ticket,
                        "limit_price": pending["limit_price"],
                    }
                    events.append(event)
                    instruments_to_remove.append(instrument)

                    logger.info(
                        f"LIMIT ORDER FILLED: {instrument} {pending['direction']} "
                        f"@ {pending['limit_price']:.5f} (order #{order_ticket})"
                    )

                    db.log_activity({
                        "activity_type": "LIMIT_ORDER_FILLED",
                        "instrument": instrument,
                        "direction": pending["direction"],
                        "confidence": pending.get("confidence", 0),
                        "reasoning": f"Limit order #{order_ticket} filled at {pending['limit_price']:.5f}",
                        "details": pending,
                    })

                    # Update trade source
                    try:
                        # Find the position ticket
                        for pos in positions:
                            trade_id = str(pos.ticket)
                            db.update_trade_source(trade_id, "AUTO_SCALPING_LIMIT")
                            break
                    except Exception as e:
                        logger.warning(f"Could not update trade source for filled limit: {e}")

                else:
                    # EXPIRED: Order gone, no position
                    event = {
                        "type": "EXPIRED",
                        "instrument": instrument,
                        "direction": pending["direction"],
                        "order_ticket": order_ticket,
                        "limit_price": pending["limit_price"],
                    }
                    events.append(event)
                    instruments_to_remove.append(instrument)

                    logger.info(
                        f"LIMIT ORDER EXPIRED: {instrument} {pending['direction']} "
                        f"@ {pending['limit_price']:.5f} (order #{order_ticket})"
                    )

                    db.log_activity({
                        "activity_type": "LIMIT_ORDER_EXPIRED",
                        "instrument": instrument,
                        "direction": pending["direction"],
                        "reasoning": f"Limit order #{order_ticket} expired (price never reached {pending['limit_price']:.5f})",
                        "details": pending,
                    })

            except Exception as e:
                logger.warning(f"Error checking pending order for {instrument}: {e}")

        # Cleanup removed orders
        for instrument in instruments_to_remove:
            del self._pending_orders[instrument]

        return events

    def _check_daily_reset(self) -> None:
        """Reset daily counters if new day."""
        today = datetime.now(timezone.utc).date()
        if self._last_reset_date != today:
            self._daily_trades = {}
            self._daily_losses = 0
            if self._stop_day_active:
                logger.info("STOP DAY cleared - new trading day")
            self._stop_day_active = False
            self._last_reset_date = today
            logger.info("Daily trade counters reset")

    def _is_in_cooldown(self) -> bool:
        """Check if executor is in cooldown."""
        if self._cooldown_until is None:
            return False
        if datetime.now(timezone.utc) >= self._cooldown_until:
            self._cooldown_until = None
            self._loss_streak = 0
            logger.info("Cooldown period ended")

            # Log cooldown end
            db.log_activity({
                "activity_type": "COOLDOWN_END",
                "reasoning": "Cooldown period ended, trading resumed",
                "details": {"loss_streak_reset": True}
            })

            return False
        return True

    def _check_trade_limits(self, instrument: str) -> tuple[bool, str]:
        """
        Check if trade limits allow new trade.

        Uses learning mode active settings for limits.

        Returns:
            (can_trade, reason)
        """
        # Get active limits from learning mode
        max_daily, max_per_instrument = self.config.get_active_trade_limits()

        # Max daily trades
        total_today = sum(self._daily_trades.values())
        if total_today >= max_daily:
            mode = "LEARNING" if self.config.learning_mode.is_in_learning() else "PRODUCTION"
            return False, f"Daily trade limit reached ({total_today}/{max_daily}) [{mode}]"

        # Max trades per instrument
        instrument_trades = self._daily_trades.get(instrument, 0)
        if instrument_trades >= max_per_instrument:
            mode = "LEARNING" if self.config.learning_mode.is_in_learning() else "PRODUCTION"
            return False, f"Instrument limit reached for {instrument} ({instrument_trades}/{max_per_instrument}) [{mode}]"

        # Check if there's already a pending limit order for this instrument
        if instrument in self._pending_orders:
            return False, f"Pending limit order already exists for {instrument}"

        # Max concurrent positions - check BOTH MT5 and database
        try:
            # Check MT5 positions
            mt5_positions = self.order_manager.client.get_positions()

            # Sync stale DB trades with MT5 (close trades that are OPEN in DB but not in MT5)
            sync_result = db.sync_trades_with_mt5(mt5_positions)
            if sync_result["closed"]:
                logger.info(f"Synced DB: closed {len(sync_result['closed'])} stale trades")

            if len(mt5_positions) >= self.config.max_concurrent_positions:
                return False, f"Max positions reached ({len(mt5_positions)})"

            # Check if already have position in this instrument (MT5)
            for pos in mt5_positions:
                if pos["instrument"] == instrument:
                    return False, f"Already have MT5 position in {instrument}"

            # Also check database for open trades (more reliable)
            db_open = db.get_open_trades()
            db_instrument_count = sum(1 for t in db_open if t.get("instrument") == instrument)
            if db_instrument_count >= self.config.max_trades_per_instrument:
                return False, f"Already have {db_instrument_count} open trades in {instrument}"

        except Exception as e:
            logger.error(f"Failed to check positions: {e}")
            return False, "Cannot verify positions"

        return True, "OK"

    def _validate_signal(self, signal: TradingSignal) -> tuple[bool, str]:
        """
        Validate signal against risk limits.

        Returns:
            (is_valid, reason)
        """
        try:
            # Get account info
            account = self.order_manager.client.get_account()
            equity = account["nav"]

            # Get P/L from database
            daily_pnl = db.get_daily_pnl()
            weekly_pnl = db.get_weekly_pnl()

            # Get current positions
            positions = self.order_manager.client.get_positions()

            # Get spread
            price = self.order_manager.client.get_price(signal.instrument)
            spread_pips = price.get("spread_pips", 0)

            # Calculate risk amount
            risk_percent = self.config.risk_per_trade_percent / 100
            risk_amount = equity * risk_percent

            # Run validation
            result = self.risk_manager.validate_trade(
                equity=equity,
                risk_amount=risk_amount,
                confidence=signal.confidence,
                open_positions=len(positions),
                spread_pips=spread_pips,
                daily_pnl=daily_pnl,
                weekly_pnl=weekly_pnl
            )

            if not result.valid:
                failed = result.get_failed_checks()
                reasons = [c.message for c in failed]
                return False, "; ".join(reasons)

            # Additional check: Emergency drawdown
            emergency_controller.check_and_stop_if_needed(
                equity=equity,
                daily_pnl=daily_pnl,
                weekly_pnl=weekly_pnl,
                daily_limit=HardLimits.MAX_DAILY_DRAWDOWN,
                weekly_limit=HardLimits.MAX_WEEKLY_DRAWDOWN
            )

            if emergency_controller.is_stopped():
                return False, "Emergency stop triggered by drawdown"

            return True, "OK"

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Validation error: {e}"

    def _calculate_position_size(self, signal: TradingSignal) -> dict:
        """
        Calculate position size for signal.

        Returns:
            Dict with units, risk_amount, can_trade, reason
        """
        try:
            account = self.order_manager.client.get_account()
            equity = account["nav"]

            result = calculate_position_size(
                equity=equity,
                confidence=signal.confidence,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                instrument=signal.instrument
            )

            # Override with config risk percentage
            risk_percent = min(
                self.config.risk_per_trade_percent / 100,
                HardLimits.MAX_RISK_PER_TRADE
            )
            risk_amount = equity * risk_percent

            return {
                "units": result.units,
                "risk_amount": risk_amount,
                "can_trade": result.can_trade,
                "reason": result.reason if not result.can_trade else "OK"
            }

        except Exception as e:
            return {
                "units": 0,
                "risk_amount": 0,
                "can_trade": False,
                "reason": str(e)
            }

    def _record_execution(self, signal: TradingSignal, order_result: OrderResult) -> None:
        """Record successful execution."""
        self._stats["total_executed"] += 1

        # Update daily trades counter
        instrument = signal.instrument
        self._daily_trades[instrument] = self._daily_trades.get(instrument, 0) + 1

        # Add to history
        self._execution_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "instrument": instrument,
            "direction": signal.direction,
            "confidence": signal.confidence,
            "order_id": order_result.order_id
        })

    def _create_skip_result(self, signal: TradingSignal, reason: str) -> ExecutionResult:
        """Create a skip result."""
        self._stats["total_skipped"] += 1
        logger.info(f"Signal skipped: {signal.instrument} - {reason}")

        # Log to activity
        db.log_activity({
            "activity_type": "TRADE_SKIPPED",
            "instrument": signal.instrument,
            "direction": signal.direction,
            "confidence": signal.confidence,
            "decision": "SKIP",
            "reasoning": reason,
            "details": {
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "risk_reward": signal.risk_reward
            }
        })

        return ExecutionResult(
            signal=signal,
            executed=False,
            skip_reason=reason
        )

    def record_trade_result(self, pnl: float, is_win: bool) -> None:
        """
        Record result of a closed trade.

        Called by trade lifecycle handler to track wins/losses for cooldown.
        Also triggers STOP DAY if daily loss limit reached.
        """
        self._stats["total_pnl"] += pnl

        if is_win:
            self._stats["wins"] += 1
            # Reset loss streak on win
            if self.config.cooldown.reset_on_win:
                self._loss_streak = 0
        else:
            self._stats["losses"] += 1
            self._loss_streak += 1
            self._daily_losses += 1

            # Check STOP DAY trigger
            if (self.config.stop_day.enabled and
                    self._daily_losses >= self.config.stop_day.loss_trigger and
                    not self._stop_day_active):
                self._stop_day_active = True
                logger.warning(
                    f"STOP DAY ACTIVATED: {self._daily_losses} losses today "
                    f"(trigger: {self.config.stop_day.loss_trigger}). "
                    f"No more trades until tomorrow."
                )
                db.log_activity({
                    "activity_type": "STOP_DAY",
                    "reasoning": f"STOP DAY: {self._daily_losses} losses today. Trading stopped.",
                    "details": {
                        "daily_losses": self._daily_losses,
                        "loss_trigger": self.config.stop_day.loss_trigger,
                        "total_pnl": self._stats["total_pnl"]
                    }
                })

            # Check if should enter cooldown (uses learning mode settings)
            loss_trigger, cooldown_minutes = self.config.get_active_cooldown_settings()
            if self._loss_streak >= loss_trigger:
                self._cooldown_until = datetime.now(timezone.utc).replace(
                    second=0, microsecond=0
                )
                from datetime import timedelta
                self._cooldown_until += timedelta(minutes=cooldown_minutes)
                mode = "LEARNING" if self.config.learning_mode.is_in_learning() else "PRODUCTION"
                logger.warning(
                    f"Entering cooldown [{mode}]: {self._loss_streak} consecutive losses. "
                    f"Until {self._cooldown_until.isoformat()}"
                )

                # Log cooldown start
                db.log_activity({
                    "activity_type": "COOLDOWN_START",
                    "reasoning": f"Entering {cooldown_minutes} min cooldown due to {self._loss_streak} consecutive losses",
                    "details": {
                        "loss_streak": self._loss_streak,
                        "cooldown_minutes": cooldown_minutes,
                        "cooldown_until": self._cooldown_until.isoformat(),
                        "total_pnl": self._stats["total_pnl"]
                    }
                })

                # Also log to cooldown_log table
                db.log_cooldown({
                    "reason": f"{self._loss_streak} consecutive losses",
                    "loss_streak": self._loss_streak,
                    "pnl_at_start": self._stats["total_pnl"]
                })

    def get_stats(self) -> dict:
        """Get execution statistics."""
        total = self._stats["wins"] + self._stats["losses"]
        win_rate = (self._stats["wins"] / total * 100) if total > 0 else 0

        return {
            **self._stats,
            "win_rate": win_rate,
            "loss_streak": self._loss_streak,
            "in_cooldown": self._is_in_cooldown(),
            "cooldown_until": self._cooldown_until.isoformat() if self._cooldown_until else None,
            "trades_today": sum(self._daily_trades.values()),
            "trades_by_instrument": dict(self._daily_trades)
        }

    def get_recent_executions(self, limit: int = 20) -> List[dict]:
        """Get recent execution history."""
        return list(self._execution_history)[-limit:]

    def reset_stats(self) -> None:
        """Reset all statistics and counters."""
        self._stats = {
            "total_executed": 0,
            "total_skipped": 0,
            "total_pnl": 0.0,
            "wins": 0,
            "losses": 0
        }
        self._daily_trades = {}
        self._loss_streak = 0
        self._cooldown_until = None
        self._execution_history.clear()
        logger.info("AutoExecutor stats reset")
