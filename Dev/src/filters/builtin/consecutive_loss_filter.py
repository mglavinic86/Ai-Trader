"""
Consecutive Loss Filter - Blocks trading after consecutive losses.

This filter prevents trading on instruments that have had
multiple consecutive losses, giving time for conditions to change.

Example:
    If EUR_USD has 3 consecutive losses, block further EUR_USD signals
    until a winning trade or cooldown period expires.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict

from src.upgrade.base_filter import BaseFilter, FilterResult


@dataclass
class InstrumentLossTracker:
    """Track consecutive losses per instrument."""
    consecutive_losses: int = 0
    last_loss_time: datetime = field(default_factory=datetime.now)
    blocked_until: datetime = field(default_factory=datetime.now)


class ConsecutiveLossFilter(BaseFilter):
    """
    Blocks signals for instruments with too many consecutive losses.

    Configuration:
        max_consecutive_losses: Block after this many losses (default: 3)
        cooldown_hours: Hours to block after max losses (default: 2)
    """

    def __init__(
        self,
        max_consecutive_losses: int = 3,
        cooldown_hours: int = 2
    ):
        super().__init__(
            name="consecutive_loss",
            description=f"Blocks after {max_consecutive_losses} consecutive losses",
            priority=10,  # Run early
            filter_type="builtin"
        )
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_hours = cooldown_hours
        self._trackers: Dict[str, InstrumentLossTracker] = {}

    def check(self, signal_data: dict) -> FilterResult:
        """Check if instrument is blocked due to consecutive losses."""
        instrument = signal_data.get("instrument", "")

        if instrument not in self._trackers:
            return FilterResult(passed=True)

        tracker = self._trackers[instrument]
        now = datetime.now()

        # Check if still in cooldown
        if tracker.blocked_until > now:
            remaining = tracker.blocked_until - now
            return FilterResult(
                passed=False,
                reason=f"Blocked: {tracker.consecutive_losses} consecutive losses, {remaining.seconds // 60}min remaining",
                details={
                    "consecutive_losses": tracker.consecutive_losses,
                    "blocked_until": tracker.blocked_until.isoformat(),
                    "remaining_minutes": remaining.seconds // 60
                }
            )

        # Not blocked
        return FilterResult(passed=True)

    def record_trade_result(self, instrument: str, is_win: bool) -> None:
        """
        Record a trade result to update loss tracking.

        Args:
            instrument: The instrument that was traded
            is_win: True if trade was profitable
        """
        if instrument not in self._trackers:
            self._trackers[instrument] = InstrumentLossTracker()

        tracker = self._trackers[instrument]

        if is_win:
            # Reset on win
            tracker.consecutive_losses = 0
        else:
            # Increment on loss
            tracker.consecutive_losses += 1
            tracker.last_loss_time = datetime.now()

            # Check if should block
            if tracker.consecutive_losses >= self.max_consecutive_losses:
                tracker.blocked_until = datetime.now() + timedelta(hours=self.cooldown_hours)

    def get_blocked_instruments(self) -> Dict[str, dict]:
        """Get all currently blocked instruments."""
        now = datetime.now()
        blocked = {}

        for instrument, tracker in self._trackers.items():
            if tracker.blocked_until > now:
                blocked[instrument] = {
                    "consecutive_losses": tracker.consecutive_losses,
                    "blocked_until": tracker.blocked_until.isoformat(),
                    "remaining_minutes": (tracker.blocked_until - now).seconds // 60
                }

        return blocked

    def reset_instrument(self, instrument: str) -> None:
        """Reset loss tracking for an instrument."""
        if instrument in self._trackers:
            del self._trackers[instrument]
