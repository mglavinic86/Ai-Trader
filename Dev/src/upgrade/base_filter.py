"""
Base Filter class for AI Trader Self-Upgrade System.

All filters (builtin and AI-generated) must inherit from BaseFilter
and implement the check() method.

Usage:
    from src.upgrade.base_filter import BaseFilter, FilterResult

    class MyFilter(BaseFilter):
        def check(self, signal_data: dict) -> FilterResult:
            if some_condition:
                return FilterResult(passed=False, reason="Condition not met")
            return FilterResult(passed=True)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class FilterResult:
    """Result of a filter check."""
    passed: bool
    reason: str = ""
    filter_name: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FilterStats:
    """Statistics for a filter's performance."""
    signals_checked: int = 0
    signals_blocked: int = 0
    true_positives: int = 0  # Blocked signal that would have lost
    false_positives: int = 0  # Blocked signal that would have won
    last_checked: Optional[datetime] = None
    estimated_pnl_saved: float = 0.0

    @property
    def block_rate(self) -> float:
        """Percentage of signals blocked."""
        if self.signals_checked == 0:
            return 0.0
        return (self.signals_blocked / self.signals_checked) * 100

    @property
    def accuracy(self) -> float:
        """Accuracy of blocking (true positives / total blocked)."""
        total_blocked = self.true_positives + self.false_positives
        if total_blocked == 0:
            return 0.0
        return (self.true_positives / total_blocked) * 100


class BaseFilter(ABC):
    """
    Abstract base class for all trading signal filters.

    Filters are used to block signals that match certain criteria.
    They run after the main signal generation but before execution.

    Attributes:
        name: Unique identifier for the filter
        description: Human-readable description
        priority: Execution order (lower = earlier, default 50)
        enabled: Whether the filter is active
        filter_type: 'builtin' or 'ai_generated'
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        priority: int = 50,
        enabled: bool = True,
        filter_type: str = "builtin"
    ):
        self.name = name
        self.description = description
        self.priority = priority
        self.enabled = enabled
        self.filter_type = filter_type
        self.stats = FilterStats()

    @abstractmethod
    def check(self, signal_data: dict) -> FilterResult:
        """
        Check if a signal should be allowed or blocked.

        Args:
            signal_data: Dictionary containing signal information:
                - instrument: str (e.g., "EUR_USD")
                - direction: str ("LONG" or "SHORT")
                - confidence: int (0-100)
                - entry_price: float
                - stop_loss: float
                - take_profit: float
                - risk_reward: float
                - technical: dict (trend, rsi, macd_trend, atr_pips, etc.)
                - sentiment: float (-1 to 1)
                - market_regime: str (TRENDING, RANGING, etc.)
                - session: str (london, newyork, tokyo, sydney)
                - timestamp: datetime

        Returns:
            FilterResult indicating whether signal passed or was blocked
        """
        pass

    def get_name(self) -> str:
        """Return the filter's unique name."""
        return self.name

    def get_priority(self) -> int:
        """Return the filter's execution priority."""
        return self.priority

    def get_description(self) -> str:
        """Return human-readable description."""
        return self.description

    def is_enabled(self) -> bool:
        """Check if filter is active."""
        return self.enabled

    def enable(self) -> None:
        """Enable the filter."""
        self.enabled = True

    def disable(self) -> None:
        """Disable the filter."""
        self.enabled = False

    def update_stats(self, result: FilterResult, trade_outcome: Optional[str] = None, pnl: Optional[float] = None) -> None:
        """
        Update filter statistics after a check.

        Args:
            result: The FilterResult from check()
            trade_outcome: 'WIN', 'LOSS', or None if trade wasn't taken
            pnl: Profit/loss if trade was taken
        """
        self.stats.signals_checked += 1
        self.stats.last_checked = datetime.now()

        if not result.passed:
            self.stats.signals_blocked += 1

            # If we know the outcome of the trade (from simulation/backtest)
            if trade_outcome == "LOSS":
                self.stats.true_positives += 1
                if pnl is not None:
                    self.stats.estimated_pnl_saved += abs(pnl)
            elif trade_outcome == "WIN":
                self.stats.false_positives += 1
                if pnl is not None:
                    self.stats.estimated_pnl_saved -= pnl  # Lost opportunity

    def get_stats(self) -> Dict[str, Any]:
        """Get filter statistics as dictionary."""
        return {
            "name": self.name,
            "type": self.filter_type,
            "enabled": self.enabled,
            "signals_checked": self.stats.signals_checked,
            "signals_blocked": self.stats.signals_blocked,
            "block_rate": f"{self.stats.block_rate:.1f}%",
            "true_positives": self.stats.true_positives,
            "false_positives": self.stats.false_positives,
            "accuracy": f"{self.stats.accuracy:.1f}%",
            "estimated_pnl_saved": round(self.stats.estimated_pnl_saved, 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize filter configuration."""
        return {
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "enabled": self.enabled,
            "filter_type": self.filter_type,
        }

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"<{self.__class__.__name__}(name='{self.name}', priority={self.priority}, {status})>"
