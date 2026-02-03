"""
Trading Signal Filters for AI Trader.

This module contains filters that run after signal generation
but before trade execution. Filters can block signals that
match certain criteria.

Subdirectories:
- builtin/: Built-in filters (spread, session, regime)
- ai_generated/: AI-generated filters from self-upgrade system
"""

from src.upgrade.base_filter import BaseFilter, FilterResult
from src.upgrade.filter_registry import FilterRegistry, get_filter_registry

__all__ = ["BaseFilter", "FilterResult", "FilterRegistry", "get_filter_registry"]
