# Core Module
from src.core.settings_manager import settings_manager, SettingsManager

# Lazy import for interface to avoid circular imports with trading module
# Use: from src.core.interface import TradingInterface, run_interface

__all__ = [
    "settings_manager",
    "SettingsManager"
]
