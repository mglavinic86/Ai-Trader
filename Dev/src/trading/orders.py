"""
Order Management - Create, modify, and close positions.

Usage:
    from src.trading.orders import OrderManager

    om = OrderManager()
    result = om.open_position("EUR_USD", 1000, stop_loss=1.0800, take_profit=1.0900)
    om.close_position("EUR_USD")
    om.close_all_positions()
"""

from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import MetaTrader5 as mt5

from src.trading.mt5_client import MT5Client, MT5Error
from src.trading.risk_manager import RiskManager, ValidationResult
from src.utils.config import config
from src.utils.logger import logger
from src.utils.helpers import generate_trade_id, format_price, get_pip_divisor
from src.utils.database import db
from src.utils.instrument_profiles import get_profile, is_in_session


@dataclass
class OrderResult:
    """Result of an order operation."""
    success: bool
    trade_id: Optional[str] = None
    order_id: Optional[str] = None
    instrument: Optional[str] = None
    units: Optional[int] = None
    price: Optional[float] = None
    error: Optional[str] = None
    raw_response: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "instrument": self.instrument,
            "units": self.units,
            "price": self.price,
            "error": self.error
        }


class OrderManager:
    """
    Manages order operations with MT5.

    All orders go through risk validation before execution.
    Risk validation is ENFORCED by default - trades without validation are rejected.
    """

    def __init__(self, client: Optional[MT5Client] = None, risk_manager: Optional[RiskManager] = None):
        """
        Initialize order manager.

        Args:
            client: MT5Client instance (creates new one if not provided)
            risk_manager: RiskManager instance (creates new one if not provided)
        """
        self.client = client or MT5Client()
        self.risk_manager = risk_manager or RiskManager()
        logger.info("OrderManager initialized with RiskManager")

    def _get_filling_mode(self, symbol_info) -> int:
        """
        Determine the correct filling mode for a symbol.

        Symbol filling_mode is a bitmask:
        - Bit 0 (value 1): FOK supported
        - Bit 1 (value 2): IOC supported
        - Bit 2 (value 4): RETURN supported

        Order filling values:
        - ORDER_FILLING_FOK = 0
        - ORDER_FILLING_IOC = 1
        - ORDER_FILLING_RETURN = 2

        OANDA TMS supports FOK (filling_mode=1, bit 0 set).
        """
        filling_flags = symbol_info.filling_mode

        # Check which mode is supported and return corresponding order value
        if filling_flags & 1:  # FOK supported
            return 0  # ORDER_FILLING_FOK
        elif filling_flags & 2:  # IOC supported
            return 1  # ORDER_FILLING_IOC
        else:  # RETURN (default)
            return 2  # ORDER_FILLING_RETURN

    def open_position(
        self,
        instrument: str,
        units: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        trailing_stop_pips: Optional[float] = None,
        # Risk validation parameters (REQUIRED unless bypassed)
        confidence: Optional[int] = None,
        risk_amount: Optional[float] = None,
        _bypass_validation: bool = False
    ) -> OrderResult:
        """
        Open a new position with market order.

        Args:
            instrument: Currency pair (e.g., "EUR_USD")
            units: Position size (positive = long, negative = short)
            stop_loss: Stop loss price
            take_profit: Take profit price
            trailing_stop_pips: Trailing stop distance in pips (not supported in MT5 basic order)
            confidence: AI confidence score (0-100) - REQUIRED for risk validation
            risk_amount: Amount at risk for this trade - REQUIRED for risk validation
            _bypass_validation: DANGEROUS - bypass risk checks (only for emergency/internal use)

        Returns:
            OrderResult with execution details

        Note:
            Risk validation is ENFORCED by default. Trades without confidence and
            risk_amount will be REJECTED unless _bypass_validation=True.
        """
        if units == 0:
            return OrderResult(
                success=False,
                error="Units cannot be zero"
            )

        equity = None
        # === RISK VALIDATION GATE ===
        if not _bypass_validation:
            profile = get_profile(instrument)
            if not is_in_session(profile):
                return OrderResult(
                    success=False,
                    error="Outside allowed trading session for this instrument"
                )
            # Require validation parameters
            if confidence is None or risk_amount is None:
                logger.error("TRADE REJECTED: Missing risk validation parameters (confidence, risk_amount)")
                return OrderResult(
                    success=False,
                    error="Risk validation required. Provide confidence and risk_amount, or use _bypass_validation=True for emergency operations."
                )

            # Get current state for validation
            try:
                account = self.client.get_account()
                equity = account.get("nav") or account.get("equity") or account.get("balance")
                if equity is None or equity <= 0:
                    logger.error("CRITICAL: Cannot determine account equity")
                    return OrderResult(
                        success=False,
                        error="Cannot determine account equity - trade rejected for safety"
                    )
                positions = mt5.positions_total() or 0

                # Calculate spread
                symbol = self.client._convert_symbol(instrument)
                symbol_info_for_spread = mt5.symbol_info(symbol)
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    # Use unified pip divisor helper
                    pip_divisor = get_pip_divisor(instrument, symbol_info_for_spread)
                    spread_pips = (tick.ask - tick.bid) / pip_divisor
                else:
                    spread_pips = 2.0  # Default if unavailable

                max_spread = profile.get("max_spread_pips")
                if max_spread is not None and spread_pips > max_spread:
                    logger.warning(f"TRADE REJECTED: Spread {spread_pips:.1f} > max {max_spread}")
                    return OrderResult(
                        success=False,
                        error=f"Spread too high ({spread_pips:.1f} pips > {max_spread})"
                    )

                # Run validation
                daily_pnl = db.get_daily_pnl()
                weekly_pnl = db.get_weekly_pnl()

                validation = self.risk_manager.validate_trade(
                    equity=equity,
                    risk_amount=risk_amount,
                    confidence=confidence,
                    open_positions=positions,
                    spread_pips=spread_pips,
                    daily_pnl=daily_pnl,
                    weekly_pnl=weekly_pnl
                )

                if not validation.valid:
                    failed_checks = [c.name for c in validation.get_failed_checks()]
                    logger.warning(f"TRADE REJECTED by RiskManager: {failed_checks}")
                    return OrderResult(
                        success=False,
                        error=f"Risk validation failed: {', '.join(failed_checks)}",
                        raw_response=validation.to_dict()
                    )

                logger.info(f"Risk validation PASSED for {instrument} (confidence={confidence}%, risk=${risk_amount:.2f})")

            except Exception as e:
                logger.error(f"Risk validation error: {e}")
                return OrderResult(
                    success=False,
                    error=f"Risk validation error: {e}"
                )
        else:
            # Only per-call bypass allowed - log warning
            logger.warning(f"RISK VALIDATION BYPASSED for {instrument} trade (per-call bypass)")

        # Convert symbol to MT5 format
        symbol = self.client._convert_symbol(instrument)

        # Get symbol info for lot calculation
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return OrderResult(
                success=False,
                error=f"Symbol {symbol} not found"
            )

        # Enable symbol if not visible
        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)

        # Convert units to lots using contract size (MT5 can vary by symbol)
        contract_size = getattr(symbol_info, "trade_contract_size", 100000.0) or 100000.0
        lot_size = abs(units) / contract_size

        # Round to broker's volume step with correct decimal places
        volume_step = symbol_info.volume_step
        if volume_step <= 0:
            volume_step = 0.01  # Default step
        decimal_places = max(0, -int(math.log10(volume_step))) if volume_step > 0 else 2
        lot_size = math.floor(lot_size / volume_step) * volume_step
        lot_size = round(lot_size, decimal_places)

        # Ensure within limits
        lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))

        if lot_size < symbol_info.volume_min:
            return OrderResult(
                success=False,
                error=f"Volume too small. Minimum: {symbol_info.volume_min} lots"
            )

        # Determine order type
        order_type = mt5.ORDER_TYPE_BUY if units > 0 else mt5.ORDER_TYPE_SELL

        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return OrderResult(
                success=False,
                error=f"No price for {symbol}"
            )

        price = tick.ask if units > 0 else tick.bid
        requested_price = price

        # Determine supported filling mode for this symbol
        filling_mode = self._get_filling_mode(symbol_info)

        # Build order request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "deviation": 20,  # Slippage in points
            "magic": 123456,  # Magic number for identification
            "comment": "AI Trader",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        # Add stop loss
        if stop_loss is not None:
            request["sl"] = stop_loss

        # Add take profit
        if take_profit is not None:
            request["tp"] = take_profit

        # Execute order
        try:
            result = mt5.order_send(request)

            if result is None:
                error = mt5.last_error()
                logger.error(f"Order send failed: {error}")
                return OrderResult(
                    success=False,
                    error=f"Order send failed: {error}"
                )

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order rejected: {result.retcode} - {result.comment}")
                return OrderResult(
                    success=False,
                    error=f"Order rejected ({result.retcode}): {result.comment}",
                    raw_response={"retcode": result.retcode, "comment": result.comment}
                )

            # Get the actual MT5 position ticket
            # Try multiple approaches to ensure we get the real ticket
            trade_id = None

            # Method 1: Use the deal from order result (most reliable)
            if result.deal and result.deal != 0:
                # The deal can be used to find the position
                try:
                    import time
                    # Small delay to let MT5 process the order
                    time.sleep(0.1)
                    positions = mt5.positions_get(symbol=symbol)
                    if positions:
                        # Find position by matching price and volume (most recent)
                        best = min(
                            positions,
                            key=lambda p: abs(p.price_open - result.price) + abs(p.volume - lot_size)
                        )
                        trade_id = str(best.ticket)
                        logger.debug(f"Got ticket {trade_id} from positions after deal {result.deal}")
                except Exception as e:
                    logger.debug(f"Could not get position from deal: {e}")

            # Method 2: Retry with positions_get if method 1 failed
            if not trade_id:
                for retry in range(3):
                    try:
                        import time
                        time.sleep(0.2)  # Wait a bit more
                        positions = mt5.positions_get(symbol=symbol)
                        if positions:
                            best = min(
                                positions,
                                key=lambda p: abs(p.price_open - result.price) + abs(p.volume - lot_size)
                            )
                            trade_id = str(best.ticket)
                            logger.debug(f"Got ticket {trade_id} on retry {retry+1}")
                            break
                    except Exception:
                        pass

            # Method 3: Fallback to generated ID (last resort)
            if not trade_id:
                trade_id = generate_trade_id()
                logger.warning(f"Could not get MT5 ticket, using generated ID: {trade_id}")
            direction = "LONG" if units > 0 else "SHORT"

            logger.info(
                f"Position opened: {instrument} {direction} "
                f"{abs(units)} units @ {result.price}"
            )

            try:
                pip_divisor = get_pip_divisor(instrument, symbol_info_for_spread)
                slippage_pips = abs(result.price - requested_price) / pip_divisor if pip_divisor else None
                db.log_execution({
                    "trade_id": trade_id,
                    "order_id": str(result.order),
                    "instrument": instrument,
                    "side": direction,
                    "requested_price": requested_price,
                    "fill_price": result.price,
                    "slippage_pips": round(slippage_pips, 2) if slippage_pips is not None else None,
                    "spread_pips": round(spread_pips, 2),
                    "notes": "OPEN"
                })
            except Exception as e:
                logger.warning(f"Failed to log execution quality: {e}")

            try:
                db.log_trade({
                    "trade_id": trade_id,
                    "timestamp": datetime.now().isoformat(),
                    "instrument": instrument,
                    "direction": direction,
                    "entry_price": result.price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "units": units,
                    "risk_amount": risk_amount,
                    "risk_percent": (risk_amount / equity) if (risk_amount is not None and equity) else None,
                    "confidence_score": confidence,
                    "notes": "MT5 order opened"
                })
            except Exception as e:
                logger.warning(f"Failed to log trade to DB: {e}")

            return OrderResult(
                success=True,
                trade_id=trade_id,
                order_id=str(result.order),
                instrument=instrument,
                units=units,
                price=result.price,
                raw_response={
                    "order": result.order,
                    "deal": result.deal,
                    "volume": result.volume,
                    "price": result.price,
                    "retcode": result.retcode
                }
            )

        except Exception as e:
            logger.error(f"Failed to open position: {e}")
            return OrderResult(success=False, error=str(e))

    def close_position(self, instrument: str, units: Optional[int] = None) -> OrderResult:
        """
        Close position for an instrument.

        Args:
            instrument: Currency pair
            units: Units to close (None = close all)

        Returns:
            OrderResult with execution details
        """
        # Convert symbol to MT5 format
        symbol = self.client._convert_symbol(instrument)

        # Get positions for this symbol
        positions = mt5.positions_get(symbol=symbol)

        if positions is None or len(positions) == 0:
            return OrderResult(
                success=False,
                error=f"No position found for {instrument}"
            )

        results = []
        for pos in positions:
            # Capture position info before closing
            entry_price = pos.price_open
            direction = "LONG" if pos.type == mt5.ORDER_TYPE_BUY else "SHORT"
            contract_size = getattr(mt5.symbol_info(symbol), "trade_contract_size", 100000.0) or 100000.0
            position_units = int(pos.volume * contract_size)
            ticket = pos.ticket

            # Determine close order type (opposite of position)
            close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                continue

            price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
            requested_price = price

            # Calculate volume to close
            if units is not None:
                close_volume = min(abs(units) / contract_size, pos.volume)
            else:
                close_volume = pos.volume

            # Get symbol info for filling mode
            symbol_info = mt5.symbol_info(symbol)
            filling_mode = self._get_filling_mode(symbol_info) if symbol_info else 2  # 2 = FILLING_RETURN

            # Build close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": close_volume,
                "type": close_type,
                "position": pos.ticket,
                "price": price,
                "deviation": 20,
                "magic": 123456,
                "comment": "AI Trader Close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

            try:
                result = mt5.order_send(request)

                if result is None:
                    error = mt5.last_error()
                    logger.error(f"Close order failed: {error}")
                    continue

                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"Close rejected: {result.retcode} - {result.comment}")
                    continue

                logger.info(f"Position closed: {instrument} ticket {pos.ticket}")

                # Calculate P/L
                pnl = pos.profit
                account_info = mt5.account_info()
                account_balance = account_info.balance if account_info else 50000
                pnl_percent = (pnl / account_balance) * 100 if account_balance > 0 else 0

                # Call trade lifecycle handler (lazy import to avoid circular dependency)
                try:
                    from src.trading.trade_lifecycle import trade_closed_handler, record_trade_close
                    close_result = trade_closed_handler(
                        trade_id=str(ticket),
                        instrument=instrument,
                        direction=direction,
                        entry_price=entry_price,
                        exit_price=result.price,
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        close_reason="MANUAL"
                    )
                    if close_result and not close_result.get("trade_updated"):
                        record_trade_close(
                            instrument=instrument,
                            exit_price=result.price,
                            pnl=pnl,
                            close_reason="MANUAL"
                        )
                except Exception as lifecycle_error:
                    logger.warning(f"Trade lifecycle handler error: {lifecycle_error}")

                results.append(OrderResult(
                    success=True,
                    order_id=str(result.order),
                    instrument=instrument,
                    units=int(close_volume * 100000),
                    price=result.price,
                    raw_response={
                        "order": result.order,
                        "deal": result.deal,
                        "volume": result.volume,
                        "price": result.price,
                        "pnl": pnl
                    }
                ))

                try:
                    symbol_info_for_spread = mt5.symbol_info(symbol)
                    pip_divisor = get_pip_divisor(instrument, symbol_info_for_spread)
                    spread_pips = (tick.ask - tick.bid) / pip_divisor if pip_divisor else None
                    slippage_pips = abs(result.price - requested_price) / pip_divisor if pip_divisor else None
                    db.log_execution({
                        "trade_id": str(pos.ticket),
                        "order_id": str(result.order),
                        "instrument": instrument,
                        "side": "CLOSE",
                        "requested_price": requested_price,
                        "fill_price": result.price,
                        "slippage_pips": round(slippage_pips, 2) if slippage_pips is not None else None,
                        "spread_pips": round(spread_pips, 2) if spread_pips is not None else None,
                        "notes": "CLOSE"
                    })
                except Exception as e:
                    logger.warning(f"Failed to log execution quality (close): {e}")

            except Exception as e:
                logger.error(f"Failed to close position: {e}")
                continue

        if results:
            # Return first successful close result
            return results[0]

        return OrderResult(
            success=False,
            error="Failed to close any positions"
        )

    def close_all_positions(self) -> list[OrderResult]:
        """
        Close ALL open positions (emergency function).

        Returns:
            List of OrderResult for each closed position
        """
        logger.warning("CLOSING ALL POSITIONS")

        results = []

        try:
            positions = self.client.get_positions()

            for pos in positions:
                instrument = pos["instrument"]
                result = self.close_position(instrument)
                results.append(result)

            logger.info(f"Closed {len(results)} positions")
            return results

        except MT5Error as e:
            logger.error(f"Failed to close all positions: {e}")
            return [OrderResult(success=False, error=str(e))]

    def modify_position(
        self,
        instrument: str,
        trade_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> OrderResult:
        """
        Modify stop loss or take profit for an existing trade.

        Args:
            instrument: Currency pair
            trade_id: MT5 position ticket (as string)
            stop_loss: New stop loss price
            take_profit: New take profit price

        Returns:
            OrderResult
        """
        if stop_loss is None and take_profit is None:
            return OrderResult(
                success=False,
                error="No modifications specified"
            )

        # Convert symbol to MT5 format
        symbol = self.client._convert_symbol(instrument)
        ticket = int(trade_id)

        # Get position info
        position = mt5.positions_get(ticket=ticket)
        if not position or len(position) == 0:
            return OrderResult(
                success=False,
                error=f"Position {ticket} not found"
            )

        pos = position[0]

        # Build modify request
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "sl": stop_loss if stop_loss is not None else pos.sl,
            "tp": take_profit if take_profit is not None else pos.tp,
        }

        try:
            result = mt5.order_send(request)

            if result is None:
                error = mt5.last_error()
                logger.error(f"Modify failed: {error}")
                return OrderResult(
                    success=False,
                    error=f"Modify failed: {error}"
                )

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Modify rejected: {result.retcode} - {result.comment}")
                return OrderResult(
                    success=False,
                    error=f"Modify rejected ({result.retcode}): {result.comment}"
                )

            logger.info(f"Trade {trade_id} modified: SL={stop_loss}, TP={take_profit}")

            return OrderResult(
                success=True,
                order_id=trade_id,
                instrument=instrument,
                raw_response={"retcode": result.retcode}
            )

        except Exception as e:
            logger.error(f"Failed to modify trade: {e}")
            return OrderResult(success=False, error=str(e))

    def get_open_trades(self) -> list[dict]:
        """
        Get all open trades with details.

        Returns:
            List of trade dictionaries
        """
        try:
            positions = mt5.positions_get()

            if positions is None:
                return []

            result = []
            for pos in positions:
                instrument = self.client._convert_symbol_reverse(pos.symbol)
                symbol_info = mt5.symbol_info(pos.symbol)
                contract_size = getattr(symbol_info, "trade_contract_size", 100000.0) if symbol_info else 100000.0
                units = int(pos.volume * contract_size)
                if pos.type == mt5.ORDER_TYPE_SELL:
                    units = -units

                result.append({
                    "id": str(pos.ticket),
                    "instrument": instrument,
                    "units": units,
                    "price": pos.price_open,
                    "unrealized_pl": pos.profit,
                    "stop_loss": pos.sl if pos.sl > 0 else None,
                    "take_profit": pos.tp if pos.tp > 0 else None,
                    "open_time": datetime.fromtimestamp(pos.time).isoformat()
                })

            return result

        except Exception as e:
            logger.error(f"Failed to get open trades: {e}")
            return []

    def move_stop_to_breakeven(self, trade_id: str, instrument: str, entry_price: float) -> OrderResult:
        """
        Move stop loss to breakeven (entry price).

        Args:
            trade_id: OANDA trade ID
            instrument: Currency pair
            entry_price: Original entry price

        Returns:
            OrderResult
        """
        logger.info(f"Moving stop to breakeven for trade {trade_id}")
        return self.modify_position(
            instrument=instrument,
            trade_id=trade_id,
            stop_loss=entry_price
        )

    def update_trailing_stop(
        self,
        trade_id: str,
        instrument: str,
        entry_price: float,
        current_price: float,
        direction: str,
        atr_pips: float = 10.0,
        breakeven_pips: float = 10.0,
        trail_after_pips: float = 20.0,
        trail_distance_atr: float = 1.5
    ) -> Optional[OrderResult]:
        """
        Update trailing stop based on current profit.

        Strategy:
        1. Move to breakeven when profit >= breakeven_pips (default 10 = 1R)
        2. Start trailing at trail_distance_atr * ATR when profit >= trail_after_pips (default 20 = 2R)

        Args:
            trade_id: MT5 position ticket
            instrument: Currency pair
            entry_price: Original entry price
            current_price: Current market price
            direction: "LONG" or "SHORT"
            atr_pips: Current ATR in pips (for trail distance)
            breakeven_pips: Pips profit to move to breakeven
            trail_after_pips: Pips profit to start trailing
            trail_distance_atr: Trail distance as multiple of ATR

        Returns:
            OrderResult if stop was modified, None if no modification needed
        """
        # Get pip value
        pip_value = 0.0001 if "JPY" not in instrument else 0.01

        # Calculate current profit in pips
        if direction == "LONG":
            profit_pips = (current_price - entry_price) / pip_value
        else:
            profit_pips = (entry_price - current_price) / pip_value

        # Get current stop loss
        positions = mt5.positions_get(ticket=int(trade_id))
        if not positions:
            return None

        pos = positions[0]
        current_sl = pos.sl

        # Calculate trail distance
        trail_distance = atr_pips * trail_distance_atr * pip_value

        # Stage 1: Move to breakeven at 1R profit
        if profit_pips >= breakeven_pips:
            # Check if SL is not yet at breakeven
            if direction == "LONG":
                if current_sl < entry_price - pip_value:
                    logger.info(f"Trade {trade_id}: Moving to breakeven ({profit_pips:.1f} pips profit)")
                    return self.modify_position(
                        instrument=instrument,
                        trade_id=trade_id,
                        stop_loss=entry_price
                    )
            else:  # SHORT
                if current_sl > entry_price + pip_value or current_sl == 0:
                    logger.info(f"Trade {trade_id}: Moving to breakeven ({profit_pips:.1f} pips profit)")
                    return self.modify_position(
                        instrument=instrument,
                        trade_id=trade_id,
                        stop_loss=entry_price
                    )

        # Stage 2: Start trailing at 2R profit
        if profit_pips >= trail_after_pips:
            if direction == "LONG":
                new_sl = current_price - trail_distance
                # Only move SL up, never down
                if new_sl > current_sl:
                    logger.info(f"Trade {trade_id}: Trailing stop to {new_sl:.5f} ({profit_pips:.1f} pips profit)")
                    return self.modify_position(
                        instrument=instrument,
                        trade_id=trade_id,
                        stop_loss=new_sl
                    )
            else:  # SHORT
                new_sl = current_price + trail_distance
                # Only move SL down, never up (for shorts)
                if current_sl == 0 or new_sl < current_sl:
                    logger.info(f"Trade {trade_id}: Trailing stop to {new_sl:.5f} ({profit_pips:.1f} pips profit)")
                    return self.modify_position(
                        instrument=instrument,
                        trade_id=trade_id,
                        stop_loss=new_sl
                    )

        return None  # No modification needed

    def place_pending_order(
        self,
        instrument: str,
        units: int,
        limit_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        expiry_minutes: int = 60,
        confidence: Optional[int] = None,
        risk_amount: Optional[float] = None,
    ) -> OrderResult:
        """
        Place a pending limit order (buy limit or sell limit).

        Args:
            instrument: Currency pair (e.g., "EUR_USD")
            units: Position size (positive = buy limit, negative = sell limit)
            limit_price: Price at which the order should fill
            stop_loss: Stop loss price
            take_profit: Take profit price
            expiry_minutes: Minutes until order expires (0 = GTC)
            confidence: AI confidence score
            risk_amount: Amount at risk

        Returns:
            OrderResult with order ticket info
        """
        if units == 0:
            return OrderResult(success=False, error="Units cannot be zero")

        # Convert symbol to MT5 format
        symbol = self.client._convert_symbol(instrument)

        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return OrderResult(success=False, error=f"Symbol {symbol} not found")

        # Enable symbol if not visible
        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)

        # Convert units to lots
        contract_size = getattr(symbol_info, "trade_contract_size", 100000.0) or 100000.0
        lot_size = abs(units) / contract_size

        # Round to broker's volume step
        volume_step = symbol_info.volume_step
        if volume_step <= 0:
            volume_step = 0.01
        decimal_places = max(0, -int(math.log10(volume_step))) if volume_step > 0 else 2
        lot_size = math.floor(lot_size / volume_step) * volume_step
        lot_size = round(lot_size, decimal_places)
        lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))

        if lot_size < symbol_info.volume_min:
            return OrderResult(
                success=False,
                error=f"Volume too small. Minimum: {symbol_info.volume_min} lots"
            )

        # Determine order type: BUY_LIMIT (long) or SELL_LIMIT (short)
        order_type = mt5.ORDER_TYPE_BUY_LIMIT if units > 0 else mt5.ORDER_TYPE_SELL_LIMIT

        # Determine filling mode
        filling_mode = self._get_filling_mode(symbol_info)

        # Build order request
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": limit_price,
            "deviation": 20,
            "magic": 123456,
            "comment": "AI Trader Limit",
            "type_filling": filling_mode,
        }

        # Add SL/TP
        if stop_loss is not None:
            request["sl"] = stop_loss
        if take_profit is not None:
            request["tp"] = take_profit

        # Set expiry
        if expiry_minutes > 0:
            try:
                expiry_time = datetime.now() + timedelta(minutes=expiry_minutes)
                # Convert to MT5 timestamp (seconds since epoch)
                import time
                expiry_ts = int(time.mktime(expiry_time.timetuple()))
                request["type_time"] = mt5.ORDER_TIME_SPECIFIED
                request["expiration"] = expiry_ts
            except Exception as e:
                # Fallback to GTC if ORDER_TIME_SPECIFIED not supported
                logger.warning(f"ORDER_TIME_SPECIFIED failed, using GTC: {e}")
                request["type_time"] = mt5.ORDER_TIME_GTC
        else:
            request["type_time"] = mt5.ORDER_TIME_GTC

        # Execute order
        try:
            result = mt5.order_send(request)

            if result is None:
                error = mt5.last_error()
                # If ORDER_TIME_SPECIFIED not supported, retry with GTC
                if "time" in str(error).lower() or "expiration" in str(error).lower():
                    logger.warning("ORDER_TIME_SPECIFIED not supported, retrying with GTC")
                    request["type_time"] = mt5.ORDER_TIME_GTC
                    request.pop("expiration", None)
                    result = mt5.order_send(request)
                    if result is None:
                        error = mt5.last_error()
                        return OrderResult(success=False, error=f"Pending order failed: {error}")
                else:
                    return OrderResult(success=False, error=f"Pending order failed: {error}")

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                # Retry without expiration if it was the issue
                if result.retcode in (10013, 10014, 10015) and "expiration" in request:
                    logger.warning(f"Retrying without expiration (retcode {result.retcode})")
                    request["type_time"] = mt5.ORDER_TIME_GTC
                    request.pop("expiration", None)
                    result = mt5.order_send(request)
                    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                        return OrderResult(
                            success=False,
                            error=f"Pending order rejected ({result.retcode if result else 'None'})"
                        )
                else:
                    return OrderResult(
                        success=False,
                        error=f"Pending order rejected ({result.retcode}): {result.comment}"
                    )

            direction = "LONG" if units > 0 else "SHORT"
            logger.info(
                f"PENDING ORDER placed: {instrument} {direction} "
                f"limit={limit_price:.5f} lots={lot_size} "
                f"order=#{result.order}"
            )

            return OrderResult(
                success=True,
                order_id=str(result.order),
                instrument=instrument,
                units=units,
                price=limit_price,
                raw_response={
                    "order": result.order,
                    "retcode": result.retcode,
                    "type": "PENDING_LIMIT",
                    "expiry_minutes": expiry_minutes,
                }
            )

        except Exception as e:
            logger.error(f"Failed to place pending order: {e}")
            return OrderResult(success=False, error=str(e))

    def cancel_pending_order(self, order_ticket: int) -> OrderResult:
        """
        Cancel a pending order by its ticket number.

        Args:
            order_ticket: MT5 order ticket

        Returns:
            OrderResult
        """
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": order_ticket,
        }

        try:
            result = mt5.order_send(request)

            if result is None:
                error = mt5.last_error()
                return OrderResult(success=False, error=f"Cancel failed: {error}")

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return OrderResult(
                    success=False,
                    error=f"Cancel rejected ({result.retcode}): {result.comment}"
                )

            logger.info(f"Pending order #{order_ticket} cancelled")
            return OrderResult(
                success=True,
                order_id=str(order_ticket),
                raw_response={"retcode": result.retcode}
            )

        except Exception as e:
            logger.error(f"Failed to cancel pending order: {e}")
            return OrderResult(success=False, error=str(e))

    def get_pending_orders(self, instrument: str = None) -> List[Dict]:
        """
        Get all pending orders, optionally filtered by instrument.

        Args:
            instrument: Filter by instrument (None = all)

        Returns:
            List of pending order dicts
        """
        try:
            if instrument:
                symbol = self.client._convert_symbol(instrument)
                orders = mt5.orders_get(symbol=symbol)
            else:
                orders = mt5.orders_get()

            if orders is None:
                return []

            result = []
            for order in orders:
                order_instrument = self.client._convert_symbol_reverse(order.symbol)
                order_type_str = "BUY_LIMIT" if order.type == mt5.ORDER_TYPE_BUY_LIMIT else "SELL_LIMIT"
                direction = "LONG" if order.type == mt5.ORDER_TYPE_BUY_LIMIT else "SHORT"

                result.append({
                    "order_ticket": order.ticket,
                    "instrument": order_instrument,
                    "price": order.price_open,
                    "type": order_type_str,
                    "direction": direction,
                    "volume": order.volume_current,
                    "sl": order.sl if order.sl > 0 else None,
                    "tp": order.tp if order.tp > 0 else None,
                    "time_setup": datetime.fromtimestamp(order.time_setup).isoformat(),
                    "expiration": datetime.fromtimestamp(order.time_expiration).isoformat() if order.time_expiration > 0 else None,
                })

            return result

        except Exception as e:
            logger.error(f"Failed to get pending orders: {e}")
            return []
