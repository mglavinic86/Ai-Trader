"""
Tuning Configuration - Defines adjustable settings and their limits.

This module defines which settings AI can adjust via override,
and the hard limits it CANNOT touch (risk management).

Usage:
    from src.core.tuning_config import TunableSettings, HARD_LIMITS

    # Check if a setting can be adjusted
    if TunableSettings.can_adjust("max_spread_pips"):
        bounds = TunableSettings.get_bounds("max_spread_pips")
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class SettingBounds:
    """Defines min/max bounds for an adjustable setting."""
    min_value: float
    max_value: float
    default_value: float
    description: str
    setting_type: str = "float"  # float, int, bool

    def is_valid(self, value: Any) -> bool:
        """Check if value is within bounds."""
        if self.setting_type == "bool":
            return isinstance(value, bool)
        try:
            num_value = float(value)
            return self.min_value <= num_value <= self.max_value
        except (TypeError, ValueError):
            return False

    def clamp(self, value: Any) -> Any:
        """Clamp value to bounds."""
        if self.setting_type == "bool":
            return bool(value)
        try:
            num_value = float(value)
            clamped = max(self.min_value, min(self.max_value, num_value))
            return int(clamped) if self.setting_type == "int" else clamped
        except (TypeError, ValueError):
            return self.default_value


class HardLimits:
    """
    ABSOLUTE SAFETY LIMITS - AI CANNOT OVERRIDE THESE.

    These protect against catastrophic losses and are enforced
    at multiple levels in the system.
    """
    MAX_RISK_PER_TRADE = 0.03      # 3% - NEVER OVERRIDE
    MAX_DAILY_DRAWDOWN = 0.05      # 5% - NEVER OVERRIDE
    MAX_WEEKLY_DRAWDOWN = 0.10     # 10% - NEVER OVERRIDE
    MAX_CONCURRENT_POSITIONS = 10  # NEVER OVERRIDE
    MIN_CONFIDENCE = 50            # Below this is gambling

    # List of setting names that are NEVER adjustable
    PROTECTED_SETTINGS = frozenset([
        "risk_per_trade_percent",
        "max_daily_drawdown_percent",
        "max_weekly_drawdown_percent",
        "max_concurrent_positions",
        "emergency_stop",
    ])

    @classmethod
    def is_protected(cls, setting_name: str) -> bool:
        """Check if a setting is protected (cannot be overridden)."""
        return setting_name in cls.PROTECTED_SETTINGS


class TunableSettings:
    """
    Settings that AI CAN adjust via override.

    Each setting has defined min/max bounds to prevent
    extreme adjustments even when overriding.
    """

    # Adjustable settings with their bounds
    SETTINGS: Dict[str, SettingBounds] = {
        # Spread
        "max_spread_pips": SettingBounds(
            min_value=1.5,
            max_value=3.5,
            default_value=2.0,
            description="Maximum spread in pips to accept trade",
            setting_type="float"
        ),

        # ATR (volatility)
        "min_atr_pips": SettingBounds(
            min_value=2.0,
            max_value=5.0,
            default_value=3.0,
            description="Minimum ATR in pips for sufficient volatility",
            setting_type="float"
        ),

        # Risk:Reward
        "target_rr": SettingBounds(
            min_value=1.3,
            max_value=3.0,
            default_value=2.0,
            description="Target risk-to-reward ratio",
            setting_type="float"
        ),

        # Confidence threshold
        "min_confidence_threshold": SettingBounds(
            min_value=50,
            max_value=70,
            default_value=55,
            description="Minimum confidence score to trade",
            setting_type="int"
        ),

        # MTF alignment
        "mtf_strength_threshold": SettingBounds(
            min_value=40,
            max_value=80,
            default_value=60,
            description="HTF trend strength threshold for MTF conflict",
            setting_type="int"
        ),

        # Session filter
        "session_filter_enabled": SettingBounds(
            min_value=0,
            max_value=1,
            default_value=1,
            description="Whether to enforce trading session filter",
            setting_type="bool"
        ),

        # Cooldown
        "cooldown_minutes": SettingBounds(
            min_value=5,
            max_value=30,
            default_value=10,
            description="Cooldown period after losses",
            setting_type="int"
        ),
    }

    @classmethod
    def can_adjust(cls, setting_name: str) -> bool:
        """Check if a setting can be adjusted by AI."""
        if HardLimits.is_protected(setting_name):
            return False
        return setting_name in cls.SETTINGS

    @classmethod
    def get_bounds(cls, setting_name: str) -> Optional[SettingBounds]:
        """Get bounds for a setting."""
        return cls.SETTINGS.get(setting_name)

    @classmethod
    def validate_adjustment(cls, setting_name: str, new_value: Any) -> tuple[bool, str]:
        """
        Validate a proposed adjustment.

        Returns:
            (is_valid, error_message)
        """
        # Check if protected
        if HardLimits.is_protected(setting_name):
            return False, f"Setting '{setting_name}' is protected and cannot be overridden"

        # Check if adjustable
        bounds = cls.SETTINGS.get(setting_name)
        if not bounds:
            return False, f"Setting '{setting_name}' is not in the adjustable settings list"

        # Check bounds
        if not bounds.is_valid(new_value):
            return False, f"Value {new_value} is outside bounds [{bounds.min_value}, {bounds.max_value}]"

        return True, ""

    @classmethod
    def get_safe_value(cls, setting_name: str, proposed_value: Any) -> Any:
        """Get a safe (clamped) value for a setting."""
        bounds = cls.SETTINGS.get(setting_name)
        if not bounds:
            return proposed_value
        return bounds.clamp(proposed_value)

    @classmethod
    def get_all_adjustable(cls) -> List[str]:
        """Get list of all adjustable setting names."""
        return list(cls.SETTINGS.keys())


@dataclass
class OverrideAdjustment:
    """Represents a single setting adjustment from an override."""
    setting_name: str
    original_value: Any
    new_value: Any
    reason: str

    def to_dict(self) -> dict:
        return {
            "setting": self.setting_name,
            "from": self.original_value,
            "to": self.new_value,
            "reason": self.reason
        }


@dataclass
class OverrideContext:
    """Context for an override decision."""
    instrument: str
    direction: str
    skip_reason: str
    confidence: int
    technical_data: Dict[str, Any] = field(default_factory=dict)
    sentiment_score: float = 0.0
    spread_pips: float = 0.0
    atr_pips: float = 0.0

    def to_prompt_context(self) -> str:
        """Format context for AI prompt."""
        lines = [
            f"Instrument: {self.instrument}",
            f"Direction: {self.direction}",
            f"Skip Reason: {self.skip_reason}",
            f"Confidence Score: {self.confidence}%",
            f"Spread: {self.spread_pips:.1f} pips",
            f"ATR: {self.atr_pips:.1f} pips",
            f"Sentiment: {self.sentiment_score:.2f}",
        ]

        if self.technical_data:
            lines.append("\nTechnical Data:")
            for key, value in self.technical_data.items():
                lines.append(f"  - {key}: {value}")

        return "\n".join(lines)
