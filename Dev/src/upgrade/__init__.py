"""
Self-Upgrade System for AI Trader.

This module provides automated learning and filter generation capabilities:
- Performance analysis to identify losing patterns
- AI-powered filter generation with safety constraints
- Code validation and sandboxed execution
- Walk-forward backtesting before deployment
- Auto-rollback on performance degradation

Usage:
    from src.upgrade import UpgradeManager

    manager = UpgradeManager()
    await manager.run_daily_upgrade_cycle()
"""

from src.upgrade.base_filter import BaseFilter, FilterResult
from src.upgrade.filter_registry import FilterRegistry, get_filter_registry
from src.upgrade.upgrade_manager import UpgradeManager

__all__ = [
    "BaseFilter",
    "FilterResult",
    "FilterRegistry",
    "get_filter_registry",
    "UpgradeManager",
]
