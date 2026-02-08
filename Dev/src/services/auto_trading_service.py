"""
Auto-Trading Service - Main service loop for automated trading.

Coordinates scanner, executor, and emergency controller to run
continuous automated trading.

Usage:
    from src.services.auto_trading_service import AutoTradingService

    service = AutoTradingService()
    await service.start()
    # ... service runs in background ...
    await service.stop()
"""

import asyncio
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Callable, Dict, Any
from dataclasses import dataclass, field

from src.trading.mt5_client import MT5Client, MT5Error
from src.trading.orders import OrderManager
from src.trading.risk_manager import RiskManager
from src.trading.auto_scanner import MarketScanner, TradingSignal
from src.trading.auto_executor import AutoExecutor, ExecutionResult
from src.trading.emergency import emergency_controller
from src.core.auto_config import (
    AutoTradingConfig,
    load_auto_config,
    save_auto_config
)
from src.utils.database import db
from src.utils.logger import logger
from src.services.heartbeat import heartbeat_manager
from src.upgrade.upgrade_manager import UpgradeManager, UpgradeConfig


@dataclass
class ServiceStatus:
    """Current status of the auto-trading service."""
    running: bool = False
    enabled: bool = False
    last_scan_time: Optional[datetime] = None
    last_execution_time: Optional[datetime] = None
    scans_today: int = 0
    signals_found_today: int = 0
    trades_executed_today: int = 0
    errors_today: int = 0
    current_state: str = "STOPPED"  # STOPPED, STARTING, SCANNING, WAITING, EXECUTING, COOLDOWN, ERROR

    # Smart interval tracking
    scans_without_signals: int = 0
    last_rejection_reasons: List[str] = field(default_factory=list)
    current_interval: int = 60  # Current active interval


class AutoTradingService:
    """
    Main auto-trading service.

    Runs a continuous loop that:
    1. Scans all configured instruments
    2. Filters signals based on criteria
    3. Executes trades automatically
    4. Monitors for emergency conditions
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize auto-trading service.

        Args:
            config_path: Path to auto_trading.json (uses default if None)
        """
        # Load configuration
        self.config = load_auto_config(config_path)

        # Initialize components
        self.client: Optional[MT5Client] = None
        self.order_manager: Optional[OrderManager] = None
        self.risk_manager = RiskManager()
        self.scanner: Optional[MarketScanner] = None
        self.executor: Optional[AutoExecutor] = None

        # Service state
        self._status = ServiceStatus()
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()

        # Callbacks
        self._on_signal_callbacks: List[Callable[[TradingSignal], None]] = []
        self._on_execution_callbacks: List[Callable[[ExecutionResult], None]] = []
        self._on_status_change_callbacks: List[Callable[[ServiceStatus], None]] = []

        # Self-Upgrade System
        self.upgrade_manager: Optional[UpgradeManager] = None
        self._last_upgrade_check: Optional[datetime] = self._load_last_upgrade_check()

        logger.info("AutoTradingService initialized")

    async def start(self) -> bool:
        """
        Start the auto-trading service.

        Returns:
            True if started successfully
        """
        if self._running:
            logger.warning("Service already running")
            return False

        try:
            self._update_state("STARTING")

            # Connect to MT5
            self.client = MT5Client()
            if not self.client.is_connected():
                logger.error("Cannot start: MT5 not connected")
                self._update_state("ERROR")
                return False

            # Initialize components
            self.order_manager = OrderManager(self.client, self.risk_manager)
            self.scanner = MarketScanner(self.client, self.config)
            self.executor = AutoExecutor(self.order_manager, self.risk_manager, self.config)

            # Initialize Self-Upgrade System if enabled
            if self.config.self_upgrade.enabled:
                upgrade_config = UpgradeConfig(
                    enabled=self.config.self_upgrade.enabled,
                    analysis_interval_hours=self.config.self_upgrade.analysis_interval_hours,
                    min_trades_for_analysis=self.config.self_upgrade.min_trades_for_analysis,
                    max_proposals_per_cycle=self.config.self_upgrade.max_proposals_per_cycle,
                    min_robustness_score=self.config.self_upgrade.min_robustness_score,
                    auto_rollback_threshold=self.config.self_upgrade.auto_rollback_threshold
                )
                self.upgrade_manager = UpgradeManager(upgrade_config)
                logger.info("Self-Upgrade System initialized")

            # Start the main loop
            self._running = True
            self._status.running = True
            self._status.enabled = self.config.enabled

            # Start heartbeat for watchdog monitoring
            heartbeat_manager.start_background_beats()
            heartbeat_manager.update_state("STARTING")

            self._loop_task = asyncio.create_task(self._main_loop())

            logger.info("AutoTradingService started")
            self._update_state("WAITING" if not self.config.enabled else "SCANNING")

            return True

        except Exception as e:
            logger.exception("Failed to start auto-trading service")
            self._update_state("ERROR")
            return False

    async def stop(self) -> None:
        """Stop the auto-trading service."""
        logger.info("Stopping AutoTradingService...")
        self._running = False

        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        self._status.running = False
        self._update_state("STOPPED")

        # Stop heartbeat and clear file
        heartbeat_manager.stop_background_beats()
        heartbeat_manager.clear_heartbeat()

        logger.info("AutoTradingService stopped")

    def _check_stop_signal(self) -> bool:
        """Check if stop signal file exists."""
        from pathlib import Path
        stop_file = Path(__file__).parent.parent.parent / "data" / ".stop_service"
        return stop_file.exists()

    def _clear_stop_signal(self) -> None:
        """Clear the stop signal file."""
        from pathlib import Path
        stop_file = Path(__file__).parent.parent.parent / "data" / ".stop_service"
        if stop_file.exists():
            stop_file.unlink()

    async def _main_loop(self) -> None:
        """Main trading loop."""
        logger.info("Auto-trading loop started")

        # Clear any existing stop signal
        self._clear_stop_signal()

        while self._running:
            try:
                # Check for stop signal file
                if self._check_stop_signal():
                    logger.info("Stop signal received, stopping service")
                    self._running = False
                    self._clear_stop_signal()
                    break

                # Reload config to pick up changes
                self.config = load_auto_config()

                # Check if enabled
                if not self.config.enabled:
                    self._update_state("WAITING")
                    await asyncio.sleep(1)
                    continue

                # Check emergency stop
                if emergency_controller.is_stopped():
                    self._update_state("STOPPED")
                    logger.warning("Auto-trading paused: Emergency stop active")
                    await asyncio.sleep(5)
                    continue

                # Check if executor is in cooldown
                if self.executor and self.executor._is_in_cooldown():
                    self._update_state("COOLDOWN")
                    await asyncio.sleep(5)
                    continue

                # Run scan cycle
                self._update_state("SCANNING")
                await self._scan_cycle()

                # Sync closed positions and run learning (every 5th scan)
                if self._status.scans_today % 5 == 0:
                    await self._sync_and_learn()

                # Run Self-Upgrade cycle if it's time (daily)
                if self._should_run_upgrade_cycle():
                    await self._run_upgrade_cycle()

                # Wait for next scan interval (smart or fixed)
                self._update_state("WAITING")
                interval = self._get_smart_interval()
                self._status.current_interval = interval
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in auto-trading loop")
                self._status.errors_today += 1
                heartbeat_manager.increment_errors()
                self._update_state("ERROR")
                await asyncio.sleep(10)  # Wait before retrying

        logger.info("Auto-trading loop ended")

    async def _scan_cycle(self) -> None:
        """Run one scan cycle."""
        if not self.scanner or not self.executor:
            return

        scan_start = datetime.now(timezone.utc)

        try:
            # Check pending limit order status before scanning
            if self.executor._pending_orders:
                pending_events = self.executor.check_pending_orders()
                for event in pending_events:
                    if event["type"] == "FILLED":
                        self._status.trades_executed_today += 1
                        heartbeat_manager.increment_trades()
                        logger.info(f"Pending order filled: {event['instrument']} {event['direction']}")
                    elif event["type"] == "EXPIRED":
                        logger.info(f"Pending order expired: {event['instrument']} {event['direction']}")

            # Scan all instruments
            signals = self.scanner.scan_all_instruments()

            self._status.scans_today += 1
            self._status.last_scan_time = scan_start
            self._status.signals_found_today += len(signals)

            # Update heartbeat stats
            heartbeat_manager.increment_scans()
            heartbeat_manager.update_stats(
                scans=self._status.scans_today,
                errors=self._status.errors_today
            )

            # Track for smart interval
            if signals:
                self._status.scans_without_signals = 0
            else:
                self._status.scans_without_signals += 1

            # Check if news is blocking (for smart interval)
            self._update_rejection_reasons()

            if not signals:
                return

            # Notify callbacks about signals
            for signal in signals:
                for callback in self._on_signal_callbacks:
                    try:
                        callback(signal)
                    except Exception as e:
                        logger.error(f"Signal callback error: {e}")

            # Sort by confidence (highest first)
            signals.sort(key=lambda s: s.confidence, reverse=True)

            # Execute best signals
            self._update_state("EXECUTING")

            for signal in signals:
                if not self._running or emergency_controller.is_stopped():
                    break

                result = self.executor.execute_signal(signal)

                if result.executed:
                    self._status.trades_executed_today += 1
                    self._status.last_execution_time = datetime.now(timezone.utc)
                    # Update heartbeat with trade execution
                    heartbeat_manager.increment_trades()

                # Update auto_signals with execution result
                try:
                    db.update_auto_signal_result(
                        instrument=signal.instrument,
                        direction=signal.direction,
                        executed=result.executed,
                        skip_reason=result.skip_reason,
                        trade_id=result.order_result.trade_id if result.order_result else None
                    )
                except Exception as e:
                    logger.warning(f"Failed to update auto_signal: {e}")

                # Notify callbacks
                for callback in self._on_execution_callbacks:
                    try:
                        callback(result)
                    except Exception as e:
                        logger.error(f"Execution callback error: {e}")

                # Small delay between executions
                await asyncio.sleep(0.5)

        except MT5Error as e:
            logger.error(f"MT5 error during scan: {e}")
            self._status.errors_today += 1
            heartbeat_manager.increment_errors()
        except Exception as e:
            logger.exception("Scan cycle error")
            self._status.errors_today += 1
            heartbeat_manager.increment_errors()

    def _update_state(self, state: str) -> None:
        """Update service state and notify callbacks."""
        self._status.current_state = state

        # Update heartbeat state for watchdog
        heartbeat_manager.update_state(state)

        for callback in self._on_status_change_callbacks:
            try:
                callback(self._status)
            except Exception as e:
                logger.error(f"Status callback error: {e}")

    def _get_smart_interval(self) -> int:
        """
        Calculate dynamic scan interval based on market conditions.

        Returns:
            Interval in seconds
        """
        si = self.config.smart_interval

        # If smart interval disabled, use fixed config value
        if not si.enabled:
            return self.config.scan_interval_seconds

        # Check last rejection reasons for news blocking
        news_blocked = any(
            "news" in reason.lower() or "calendar" in reason.lower()
            for reason in self._status.last_rejection_reasons[-5:]
        )

        if news_blocked:
            # News is blocking most signals - no point scanning often
            logger.debug(f"Smart interval: {si.news_blocking_interval}s (news blocking)")
            return si.news_blocking_interval

        # Check if signals were found recently
        if self._status.scans_without_signals == 0:
            # Just found signals - market is active
            logger.debug(f"Smart interval: {si.active_market_interval}s (active market)")
            return si.active_market_interval

        # Check for quiet market
        if self._status.scans_without_signals >= si.quiet_threshold_scans:
            # No signals for a while - quiet market
            logger.debug(f"Smart interval: {si.quiet_market_interval}s (quiet market)")
            return si.quiet_market_interval

        # Default base interval
        logger.debug(f"Smart interval: {si.base_interval_seconds}s (default)")
        return si.base_interval_seconds

    def _update_rejection_reasons(self) -> None:
        """
        Update last rejection reasons from activity log.

        Used by smart interval to detect news blocking patterns.
        """
        try:
            # Get recent SIGNAL_REJECTED entries
            import sqlite3
            db_path = db.db_path
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            cur.execute("""
                SELECT details FROM activity_log
                WHERE activity_type = 'SIGNAL_REJECTED'
                ORDER BY id DESC LIMIT 10
            """)

            reasons = []
            for row in cur.fetchall():
                if row[0]:
                    # Details is JSON string, extract reason
                    import json
                    try:
                        details = json.loads(row[0])
                        if "news_event" in details:
                            reasons.append("news")
                        elif "spread" in str(details).lower():
                            reasons.append("spread")
                        elif "regime" in str(details).lower():
                            reasons.append("regime")
                        else:
                            reasons.append("other")
                    except:
                        reasons.append("unknown")

            conn.close()
            self._status.last_rejection_reasons = reasons

        except Exception as e:
            logger.debug(f"Failed to update rejection reasons: {e}")

    async def _sync_and_learn(self) -> None:
        """Sync closed positions from MT5 and run learning/self-tuning."""
        try:
            from src.utils.mt5_sync import sync_mt5_history
            from src.analysis.adaptive_settings import adaptive_settings

            logger.info("Running position sync and learning...")

            # Sync closed trades from MT5
            result = sync_mt5_history(days=1)
            if result.get("trades_analyzed", 0) > 0:
                logger.info(f"Learned from {result['trades_analyzed']} newly closed trades")

            # Run self-tuning optimization
            try:
                optimization = adaptive_settings.analyze_and_optimize()
                if optimization.get("adjustments_made"):
                    for adj in optimization["adjustments_made"]:
                        logger.info(f"SELF-TUNED: {adj['setting']} -> {adj['new_value']} ({adj['reason']})")
            except Exception as e:
                logger.warning(f"Self-tuning error: {e}")

        except Exception as e:
            logger.warning(f"Sync and learn error: {e}")

    _UPGRADE_CHECK_FILE = Path("data/.last_upgrade_check")

    def _load_last_upgrade_check(self) -> Optional[datetime]:
        """Load last upgrade check time from disk (survives restarts)."""
        try:
            if self._UPGRADE_CHECK_FILE.exists():
                data = json.loads(self._UPGRADE_CHECK_FILE.read_text())
                return datetime.fromisoformat(data["last_check"])
        except Exception:
            pass
        return None

    def _save_last_upgrade_check(self, dt: datetime) -> None:
        """Save last upgrade check time to disk."""
        try:
            self._UPGRADE_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
            self._UPGRADE_CHECK_FILE.write_text(json.dumps({
                "last_check": dt.isoformat()
            }))
        except Exception as e:
            logger.warning(f"Failed to save upgrade check time: {e}")

    def _should_run_upgrade_cycle(self) -> bool:
        """Check if it's time to run the Self-Upgrade cycle."""
        if not self.upgrade_manager or not self.config.self_upgrade.enabled:
            return False

        if self._last_upgrade_check is None:
            return True

        hours_since = (datetime.now(timezone.utc) - self._last_upgrade_check).total_seconds() / 3600
        return hours_since >= self.config.self_upgrade.analysis_interval_hours

    async def _run_upgrade_cycle(self) -> None:
        """Run the Self-Upgrade System's daily cycle."""
        if not self.upgrade_manager:
            return

        try:
            logger.info("Starting Self-Upgrade cycle...")
            self._last_upgrade_check = datetime.now(timezone.utc)
            self._save_last_upgrade_check(self._last_upgrade_check)

            result = await self.upgrade_manager.run_daily_upgrade_cycle()

            if result.filters_deployed > 0:
                logger.info(f"Self-Upgrade: Deployed {result.filters_deployed} new filters: {result.deployed_filters}")

            if result.filters_rolled_back > 0:
                logger.warning(f"Self-Upgrade: Rolled back {result.filters_rolled_back} filters: {result.rolled_back_filters}")

            if result.errors:
                for err in result.errors[:3]:  # Log first 3 errors
                    logger.error(f"Self-Upgrade error: {err}")

        except Exception as e:
            logger.error(f"Self-Upgrade cycle failed: {e}")

    def enable(self) -> bool:
        """Enable auto-trading."""
        self.config.enabled = True
        self._status.enabled = True
        logger.info("Auto-trading ENABLED")
        return save_auto_config(self.config)

    def disable(self) -> bool:
        """Disable auto-trading."""
        self.config.enabled = False
        self._status.enabled = False
        logger.info("Auto-trading DISABLED")
        return save_auto_config(self.config)

    def toggle(self) -> bool:
        """Toggle auto-trading on/off."""
        if self.config.enabled:
            return self.disable()
        else:
            return self.enable()

    def update_config(self, updates: Dict[str, Any]) -> bool:
        """
        Update configuration.

        Args:
            updates: Dictionary of config updates

        Returns:
            True if saved successfully
        """
        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        # Validate
        is_valid, errors = self.config.validate()
        if not is_valid:
            logger.error(f"Config validation failed: {errors}")
            return False

        # Save
        if save_auto_config(self.config):
            # Update components with new config
            if self.scanner:
                self.scanner.config = self.config
            if self.executor:
                self.executor.config = self.config

            logger.info(f"Config updated: {list(updates.keys())}")
            return True

        return False

    def get_status(self) -> Dict[str, Any]:
        """Get current service status."""
        executor_stats = self.executor.get_stats() if self.executor else {}

        return {
            "running": self._status.running,
            "enabled": self._status.enabled,
            "state": self._status.current_state,
            "last_scan": self._status.last_scan_time.isoformat() if self._status.last_scan_time else None,
            "last_execution": self._status.last_execution_time.isoformat() if self._status.last_execution_time else None,
            "scans_today": self._status.scans_today,
            "signals_found_today": self._status.signals_found_today,
            "trades_executed_today": self._status.trades_executed_today,
            "errors_today": self._status.errors_today,
            "emergency_stopped": emergency_controller.is_stopped(),
            "executor_stats": executor_stats,
            "config": {
                "mode": self.config.mode,
                "instruments": self.config.instruments,
                "scan_interval": self.config.scan_interval_seconds,
                "risk_per_trade": self.config.risk_per_trade_percent,
                "min_confidence": self.config.min_confidence_threshold,
                "dry_run": self.config.dry_run
            }
        }

    def get_recent_signals(self, limit: int = 20) -> List[Dict]:
        """Get recent signals from scanner."""
        # This would need scanner to track signals
        return []

    def get_recent_executions(self, limit: int = 20) -> List[Dict]:
        """Get recent execution results."""
        if self.executor:
            return self.executor.get_recent_executions(limit)
        return []

    def reset_daily_stats(self) -> None:
        """Reset daily statistics."""
        self._status.scans_today = 0
        self._status.signals_found_today = 0
        self._status.trades_executed_today = 0
        self._status.errors_today = 0

        if self.executor:
            self.executor.reset_stats()

        # Reset heartbeat daily stats
        heartbeat_manager.reset_daily_stats()

        logger.info("Daily stats reset")

    # Callback registration
    def on_signal(self, callback: Callable[[TradingSignal], None]) -> None:
        """Register callback for new signals."""
        self._on_signal_callbacks.append(callback)

    def on_execution(self, callback: Callable[[ExecutionResult], None]) -> None:
        """Register callback for trade executions."""
        self._on_execution_callbacks.append(callback)

    def on_status_change(self, callback: Callable[[ServiceStatus], None]) -> None:
        """Register callback for status changes."""
        self._on_status_change_callbacks.append(callback)


# Global service instance
_service_instance: Optional[AutoTradingService] = None


def get_auto_trading_service() -> AutoTradingService:
    """Get or create the global auto-trading service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AutoTradingService()
    return _service_instance


async def start_auto_trading() -> bool:
    """Start the global auto-trading service."""
    service = get_auto_trading_service()
    return await service.start()


async def stop_auto_trading() -> None:
    """Stop the global auto-trading service."""
    service = get_auto_trading_service()
    await service.stop()
