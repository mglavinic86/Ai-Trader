"""
Emergency Controller for Auto-Trading.

Provides emergency stop functionality that immediately halts all
auto-trading activity and optionally closes all positions.

SAFETY FIRST: This module takes priority over all other trading operations.

Usage:
    from src.trading.emergency import EmergencyController, emergency_controller

    # Global singleton
    if emergency_controller.is_stopped():
        return  # Don't trade

    # Emergency stop
    emergency_controller.stop("Daily drawdown limit reached")
"""

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Callable
from pathlib import Path

from src.utils.logger import logger


@dataclass
class EmergencyEvent:
    """Record of an emergency event."""
    timestamp: datetime
    reason: str
    positions_closed: int
    pnl_at_stop: float


class EmergencyController:
    """
    Emergency stop controller for auto-trading.

    Thread-safe singleton that can be accessed from anywhere in the codebase.
    When stopped, all auto-trading operations should check is_stopped() and halt.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize emergency controller."""
        if self._initialized:
            return

        self._stopped = False
        self._stop_reason: Optional[str] = None
        self._stop_time: Optional[datetime] = None
        self._event_history: List[EmergencyEvent] = []
        self._callbacks: List[Callable[[str], None]] = []
        self._state_lock = threading.Lock()
        self._initialized = True

        logger.info("EmergencyController initialized")

    def stop(self, reason: str, close_positions: bool = False) -> dict:
        """
        Activate emergency stop.

        Args:
            reason: Why emergency stop was triggered
            close_positions: If True, close all open positions

        Returns:
            Dict with stop details
        """
        with self._state_lock:
            if self._stopped:
                logger.warning(f"Emergency stop already active: {self._stop_reason}")
                return {
                    "success": True,
                    "already_stopped": True,
                    "reason": self._stop_reason
                }

            self._stopped = True
            self._stop_reason = reason
            self._stop_time = datetime.now(timezone.utc)

            logger.critical(f"EMERGENCY STOP ACTIVATED: {reason}")

        # Close positions if requested (outside lock to avoid deadlock)
        positions_closed = 0
        pnl = 0.0

        if close_positions:
            try:
                positions_closed, pnl = self._close_all_positions()
            except Exception as e:
                logger.error(f"Failed to close positions during emergency: {e}")

        # Record event
        event = EmergencyEvent(
            timestamp=self._stop_time,
            reason=reason,
            positions_closed=positions_closed,
            pnl_at_stop=pnl
        )
        self._event_history.append(event)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(reason)
            except Exception as e:
                logger.error(f"Emergency callback error: {e}")

        return {
            "success": True,
            "already_stopped": False,
            "reason": reason,
            "positions_closed": positions_closed,
            "pnl": pnl
        }

    def _close_all_positions(self) -> tuple[int, float]:
        """
        Close all open positions.

        Returns:
            (number_closed, total_pnl)
        """
        try:
            from src.trading.mt5_client import MT5Client
            from src.trading.orders import OrderManager

            client = MT5Client()
            if not client.is_connected():
                logger.error("Cannot close positions: MT5 not connected")
                return 0, 0.0

            order_manager = OrderManager(client)
            positions = client.get_positions()

            if not positions:
                logger.info("No positions to close")
                return 0, 0.0

            total_pnl = 0.0
            closed = 0

            for pos in positions:
                try:
                    result = order_manager.close_position(
                        pos["instrument"],
                        _bypass_validation=True  # Emergency override
                    )
                    if result.success:
                        closed += 1
                        if result.raw_response:
                            total_pnl += result.raw_response.get("pnl", 0)
                except Exception as e:
                    logger.error(f"Failed to close {pos['instrument']}: {e}")

            logger.info(f"Emergency close: {closed}/{len(positions)} positions, P/L: {total_pnl:.2f}")
            return closed, total_pnl

        except Exception as e:
            logger.error(f"Emergency close failed: {e}")
            return 0, 0.0

    def reset(self, confirmation: str = "") -> bool:
        """
        Reset emergency stop.

        Requires confirmation string "CONFIRM_RESET" to prevent accidental reset.

        Args:
            confirmation: Must be "CONFIRM_RESET" to proceed

        Returns:
            True if reset successful
        """
        if confirmation != "CONFIRM_RESET":
            logger.warning("Emergency reset requires confirmation='CONFIRM_RESET'")
            return False

        with self._state_lock:
            if not self._stopped:
                logger.info("Emergency stop not active, nothing to reset")
                return True

            previous_reason = self._stop_reason
            self._stopped = False
            self._stop_reason = None
            self._stop_time = None

            logger.warning(f"Emergency stop RESET. Previous reason: {previous_reason}")
            return True

    def is_stopped(self) -> bool:
        """Check if emergency stop is active."""
        return self._stopped

    def get_status(self) -> dict:
        """Get current emergency status."""
        with self._state_lock:
            return {
                "stopped": self._stopped,
                "reason": self._stop_reason,
                "stop_time": self._stop_time.isoformat() if self._stop_time else None,
                "event_count": len(self._event_history)
            }

    def get_history(self, limit: int = 10) -> List[dict]:
        """Get emergency event history."""
        events = self._event_history[-limit:]
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "reason": e.reason,
                "positions_closed": e.positions_closed,
                "pnl": e.pnl_at_stop
            }
            for e in events
        ]

    def register_callback(self, callback: Callable[[str], None]) -> None:
        """
        Register callback to be called on emergency stop.

        Args:
            callback: Function that takes reason string
        """
        self._callbacks.append(callback)

    def check_and_stop_if_needed(
        self,
        equity: float,
        daily_pnl: float,
        weekly_pnl: float,
        daily_limit: float = 0.05,
        weekly_limit: float = 0.10
    ) -> bool:
        """
        Check if emergency stop should be triggered based on drawdown.

        Args:
            equity: Current equity
            daily_pnl: Today's P/L (negative for loss)
            weekly_pnl: This week's P/L
            daily_limit: Daily drawdown limit (0.05 = 5%)
            weekly_limit: Weekly drawdown limit

        Returns:
            True if emergency stop was triggered
        """
        if self._stopped:
            return True

        # Check daily drawdown
        if equity > 0 and daily_pnl < 0:
            daily_dd = abs(daily_pnl) / equity
            if daily_dd >= daily_limit:
                self.stop(
                    f"Daily drawdown limit reached: {daily_dd*100:.1f}% >= {daily_limit*100:.1f}%",
                    close_positions=True
                )
                return True

        # Check weekly drawdown
        if equity > 0 and weekly_pnl < 0:
            weekly_dd = abs(weekly_pnl) / equity
            if weekly_dd >= weekly_limit:
                self.stop(
                    f"Weekly drawdown limit reached: {weekly_dd*100:.1f}% >= {weekly_limit*100:.1f}%",
                    close_positions=True
                )
                return True

        return False


# Global singleton instance
emergency_controller = EmergencyController()


# Convenience functions
def emergency_stop(reason: str, close_positions: bool = False) -> dict:
    """Activate emergency stop."""
    return emergency_controller.stop(reason, close_positions)


def is_emergency_stopped() -> bool:
    """Check if emergency stop is active."""
    return emergency_controller.is_stopped()


def reset_emergency(confirmation: str = "") -> bool:
    """Reset emergency stop."""
    return emergency_controller.reset(confirmation)
