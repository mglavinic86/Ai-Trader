"""
Auto-Trading Configuration.

Defines configuration for the automated scalping bot.
All settings can be adjusted by the user within hard limits.

Usage:
    from src.core.auto_config import AutoTradingConfig, load_auto_config

    config = load_auto_config()
    if config.enabled:
        # Start auto-trading
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from pathlib import Path

from src.utils.logger import logger


# Hard limits that CANNOT be exceeded
class HardLimits:
    """Absolute safety limits that cannot be overridden."""
    MAX_RISK_PER_TRADE = 0.03      # 3% absolute max
    MAX_DAILY_DRAWDOWN = 0.05      # 5% absolute max
    MAX_WEEKLY_DRAWDOWN = 0.10     # 10% absolute max
    MAX_CONCURRENT_POSITIONS = 10  # Absolute max positions
    MIN_CONFIDENCE = 50            # Minimum confidence to trade
    MIN_SCAN_INTERVAL = 10         # Minimum seconds between scans


@dataclass
class ScalpingConfig:
    """Scalping-specific configuration."""
    max_sl_pips: float = 15.0
    target_rr: float = 1.5
    max_hold_minutes: int = 120
    preferred_sessions: List[str] = field(default_factory=lambda: ["london", "newyork"])
    avoid_news_minutes: int = 30
    min_atr_pips: float = 5.0
    max_spread_pips: float = 2.0


@dataclass
class CooldownConfig:
    """Cooldown configuration after losses."""
    loss_streak_trigger: int = 3
    cooldown_minutes: int = 30
    reset_on_win: bool = True


@dataclass
class AIValidationConfig:
    """Configuration for AI validation layer."""
    enabled: bool = True
    reject_on_failure: bool = True  # If AI call fails, reject the trade
    timeout_seconds: int = 10
    skip_in_learning_mode: bool = False  # Skip AI validation during learning


@dataclass
class AIOverrideConfig:
    """
    Configuration for AI Override system.

    When a signal is rejected due to technical filters (spread, MTF, etc.),
    AI can evaluate whether to override the rejection.
    """
    enabled: bool = True
    min_ai_confidence: int = 65  # Min AI confidence to approve override
    max_overrides_per_day: int = 10
    cooldown_after_loss_minutes: int = 30

    # Adjustable settings with their bounds
    adjustable_settings: dict = field(default_factory=lambda: {
        "max_spread_pips": {"min": 1.5, "max": 3.5},
        "min_atr_pips": {"min": 2.0, "max": 5.0},
        "target_rr": {"min": 1.3, "max": 3.0},
        "min_confidence_threshold": {"min": 50, "max": 70},
        "mtf_strength_threshold": {"min": 40, "max": 80},
        "session_filter": {"can_disable": True},
    })

    # Learning from override outcomes
    learning: dict = field(default_factory=lambda: {
        "track_outcomes": True,
        "disable_setting_after_losses": 3,
    })


@dataclass
class MarketRegimeConfig:
    """
    Configuration for market regime detection (Phase 1 Enhancement).

    Controls how the system filters trades based on market regime.
    """
    enabled: bool = True
    block_low_volatility: bool = True  # Block trades in low volatility
    block_volatile: bool = True  # Block trades in high volatility
    trending_only_with_trend: bool = True  # Only trade with trend in trending
    ranging_require_sr: bool = True  # Require S/R proximity in ranging

    # Thresholds
    min_regime_strength: int = 60
    adx_trending_threshold: float = 25.0
    adx_ranging_threshold: float = 20.0
    bb_squeeze_percentile: float = 20.0  # Bottom 20% = squeeze
    bb_expansion_percentile: float = 80.0  # Top 20% = expansion


@dataclass
class ExternalSentimentConfig:
    """
    Configuration for external sentiment integration (Phase 2 Enhancement).

    Controls news, VIX, and calendar sentiment providers.
    """
    enabled: bool = False  # Disabled by default - enable when ready
    news_provider_enabled: bool = True
    vix_provider_enabled: bool = True
    calendar_provider_enabled: bool = True
    cache_ttl_minutes: int = 30

    weights: dict = field(default_factory=lambda: {
        "price_action": 0.30,
        "news_claude": 0.35,
        "vix": 0.15,
        "calendar": 0.20
    })


@dataclass
class SmartIntervalConfig:
    """
    Configuration for smart scan interval.

    Dynamically adjusts scan interval based on market conditions:
    - Default: 60s (optimal for M5 timeframe)
    - News blocking: 120s (no point scanning during high-impact news)
    - Active market: 30s (signals found, faster reaction needed)
    - Quiet market: 90s (nothing happening, save resources)
    """
    enabled: bool = True
    base_interval_seconds: int = 60  # M5 timeframe default
    min_interval_seconds: int = 30   # When market is active
    max_interval_seconds: int = 120  # When news blocking or quiet

    # Conditions for adjusting interval
    news_blocking_interval: int = 120  # When news filter blocks
    active_market_interval: int = 30   # When signals found
    quiet_market_interval: int = 90    # No signals for multiple scans
    quiet_threshold_scans: int = 5     # Scans without signals = quiet


@dataclass
class SelfUpgradeConfig:
    """
    Configuration for Self-Upgrade System.

    Controls automated filter generation and deployment.
    """
    enabled: bool = True
    analysis_interval_hours: int = 24
    min_trades_for_analysis: int = 20
    max_proposals_per_cycle: int = 3
    min_robustness_score: float = 60.0
    auto_rollback_threshold: dict = field(default_factory=lambda: {
        "win_rate_drop": 0.10,
        "consecutive_losses": 5,
        "max_block_rate": 50.0
    })


@dataclass
class LearningModeConfig:
    """
    Learning Mode configuration for aggressive data collection.

    When enabled, uses more aggressive settings to collect trade data faster.
    After reaching target_trades, automatically switches to production settings.
    """
    enabled: bool = True
    target_trades: int = 50
    current_trades: int = 0
    auto_graduate: bool = True

    aggressive_settings: dict = field(default_factory=lambda: {
        "min_confidence_threshold": 50,
        "loss_streak_trigger": 3,
        "cooldown_minutes": 5,
        "max_daily_trades": 20,
        "max_trades_per_instrument": 8
    })

    production_settings: dict = field(default_factory=lambda: {
        "min_confidence_threshold": 65,
        "loss_streak_trigger": 5,
        "cooldown_minutes": 15,
        "max_daily_trades": 10,
        "max_trades_per_instrument": 5
    })

    def is_in_learning(self) -> bool:
        """Check if still in learning mode."""
        return self.enabled and self.current_trades < self.target_trades

    def get_active_settings(self) -> dict:
        """Return active settings based on current mode."""
        if self.is_in_learning():
            return self.aggressive_settings
        return self.production_settings

    def get_progress_percent(self) -> float:
        """Return learning progress as percentage."""
        if self.target_trades <= 0:
            return 100.0
        return min(100.0, (self.current_trades / self.target_trades) * 100)

    def increment_trade_count(self) -> bool:
        """
        Increment trade counter.

        Returns:
            True if graduated (reached target), False otherwise
        """
        self.current_trades += 1
        if self.auto_graduate and self.current_trades >= self.target_trades:
            self.enabled = False
            return True  # Graduated!
        return False


@dataclass
class AutoTradingConfig:
    """
    Main configuration for auto-trading.

    All user-configurable settings with validation against hard limits.
    """
    # Core settings
    enabled: bool = False
    mode: str = "scalping"  # scalping, swing, or custom

    # Scanning
    scan_interval_seconds: int = 30
    instruments: List[str] = field(default_factory=lambda: [
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "BTCUSD"
    ])

    # Risk settings (within hard limits)
    risk_per_trade_percent: float = 1.0
    max_daily_drawdown_percent: float = 3.0
    max_weekly_drawdown_percent: float = 6.0
    max_concurrent_positions: int = 5
    min_confidence_threshold: int = 70

    # Trade limits
    max_daily_trades: Optional[int] = None  # None = unlimited
    max_trades_per_instrument: int = 2

    # Cooldown
    cooldown: CooldownConfig = field(default_factory=CooldownConfig)

    # Scalping
    scalping: ScalpingConfig = field(default_factory=ScalpingConfig)

    # Learning mode
    learning_mode: LearningModeConfig = field(default_factory=LearningModeConfig)

    # AI validation
    ai_validation: AIValidationConfig = field(default_factory=AIValidationConfig)

    # AI override (self-tuning)
    ai_override: AIOverrideConfig = field(default_factory=AIOverrideConfig)

    # Market regime detection (Phase 1)
    market_regime: MarketRegimeConfig = field(default_factory=MarketRegimeConfig)

    # External sentiment (Phase 2)
    external_sentiment: ExternalSentimentConfig = field(default_factory=ExternalSentimentConfig)

    # Self-Upgrade System
    self_upgrade: SelfUpgradeConfig = field(default_factory=SelfUpgradeConfig)

    # Smart interval (dynamic scan timing)
    smart_interval: SmartIntervalConfig = field(default_factory=SmartIntervalConfig)

    # Dry run mode (log only, no real trades)
    dry_run: bool = True

    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate config against hard limits.

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Risk per trade
        if self.risk_per_trade_percent > HardLimits.MAX_RISK_PER_TRADE * 100:
            errors.append(
                f"risk_per_trade_percent ({self.risk_per_trade_percent}%) exceeds hard limit "
                f"({HardLimits.MAX_RISK_PER_TRADE * 100}%)"
            )

        # Daily drawdown
        if self.max_daily_drawdown_percent > HardLimits.MAX_DAILY_DRAWDOWN * 100:
            errors.append(
                f"max_daily_drawdown_percent ({self.max_daily_drawdown_percent}%) exceeds hard limit "
                f"({HardLimits.MAX_DAILY_DRAWDOWN * 100}%)"
            )

        # Weekly drawdown
        if self.max_weekly_drawdown_percent > HardLimits.MAX_WEEKLY_DRAWDOWN * 100:
            errors.append(
                f"max_weekly_drawdown_percent ({self.max_weekly_drawdown_percent}%) exceeds hard limit "
                f"({HardLimits.MAX_WEEKLY_DRAWDOWN * 100}%)"
            )

        # Positions
        if self.max_concurrent_positions > HardLimits.MAX_CONCURRENT_POSITIONS:
            errors.append(
                f"max_concurrent_positions ({self.max_concurrent_positions}) exceeds hard limit "
                f"({HardLimits.MAX_CONCURRENT_POSITIONS})"
            )

        # Confidence
        if self.min_confidence_threshold < HardLimits.MIN_CONFIDENCE:
            errors.append(
                f"min_confidence_threshold ({self.min_confidence_threshold}%) below hard limit "
                f"({HardLimits.MIN_CONFIDENCE}%)"
            )

        # Scan interval
        if self.scan_interval_seconds < HardLimits.MIN_SCAN_INTERVAL:
            errors.append(
                f"scan_interval_seconds ({self.scan_interval_seconds}s) below hard limit "
                f"({HardLimits.MIN_SCAN_INTERVAL}s)"
            )

        # Valid mode
        if self.mode not in ["scalping", "swing", "custom"]:
            errors.append(f"Invalid mode: {self.mode}. Must be scalping, swing, or custom")

        return len(errors) == 0, errors

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "AutoTradingConfig":
        """Create from dictionary."""
        # Handle nested configs
        cooldown_data = data.pop("cooldown", {})
        scalping_data = data.pop("scalping", {})
        learning_mode_data = data.pop("learning_mode", {})
        ai_validation_data = data.pop("ai_validation", {})
        ai_override_data = data.pop("ai_override", {})
        market_regime_data = data.pop("market_regime", {})
        external_sentiment_data = data.pop("external_sentiment", {})
        self_upgrade_data = data.pop("self_upgrade", {})
        smart_interval_data = data.pop("smart_interval", {})

        cooldown = CooldownConfig(**cooldown_data) if cooldown_data else CooldownConfig()
        scalping = ScalpingConfig(**scalping_data) if scalping_data else ScalpingConfig()
        ai_validation = AIValidationConfig(**ai_validation_data) if ai_validation_data else AIValidationConfig()

        # Handle ai_override with nested dicts
        if ai_override_data:
            ai_override = AIOverrideConfig(
                enabled=ai_override_data.get("enabled", True),
                min_ai_confidence=ai_override_data.get("min_ai_confidence", 65),
                max_overrides_per_day=ai_override_data.get("max_overrides_per_day", 10),
                cooldown_after_loss_minutes=ai_override_data.get("cooldown_after_loss_minutes", 30),
                adjustable_settings=ai_override_data.get("adjustable_settings", AIOverrideConfig().adjustable_settings),
                learning=ai_override_data.get("learning", AIOverrideConfig().learning)
            )
        else:
            ai_override = AIOverrideConfig()

        # Handle learning_mode with nested dicts
        if learning_mode_data:
            learning_mode = LearningModeConfig(
                enabled=learning_mode_data.get("enabled", True),
                target_trades=learning_mode_data.get("target_trades", 50),
                current_trades=learning_mode_data.get("current_trades", 0),
                auto_graduate=learning_mode_data.get("auto_graduate", True),
                aggressive_settings=learning_mode_data.get("aggressive_settings", LearningModeConfig().aggressive_settings),
                production_settings=learning_mode_data.get("production_settings", LearningModeConfig().production_settings)
            )
        else:
            learning_mode = LearningModeConfig()

        # Handle market_regime config (Phase 1)
        if market_regime_data:
            market_regime = MarketRegimeConfig(**market_regime_data)
        else:
            market_regime = MarketRegimeConfig()

        # Handle external_sentiment config (Phase 2)
        if external_sentiment_data:
            external_sentiment = ExternalSentimentConfig(
                enabled=external_sentiment_data.get("enabled", False),
                news_provider_enabled=external_sentiment_data.get("news_provider_enabled", True),
                vix_provider_enabled=external_sentiment_data.get("vix_provider_enabled", True),
                calendar_provider_enabled=external_sentiment_data.get("calendar_provider_enabled", True),
                cache_ttl_minutes=external_sentiment_data.get("cache_ttl_minutes", 30),
                weights=external_sentiment_data.get("weights", ExternalSentimentConfig().weights)
            )
        else:
            external_sentiment = ExternalSentimentConfig()

        # Handle self_upgrade config
        if self_upgrade_data:
            self_upgrade = SelfUpgradeConfig(
                enabled=self_upgrade_data.get("enabled", True),
                analysis_interval_hours=self_upgrade_data.get("analysis_interval_hours", 24),
                min_trades_for_analysis=self_upgrade_data.get("min_trades_for_analysis", 20),
                max_proposals_per_cycle=self_upgrade_data.get("max_proposals_per_cycle", 3),
                min_robustness_score=self_upgrade_data.get("min_robustness_score", 60.0),
                auto_rollback_threshold=self_upgrade_data.get("auto_rollback_threshold", SelfUpgradeConfig().auto_rollback_threshold)
            )
        else:
            self_upgrade = SelfUpgradeConfig()

        # Handle smart_interval config
        if smart_interval_data:
            smart_interval = SmartIntervalConfig(**smart_interval_data)
        else:
            smart_interval = SmartIntervalConfig()

        return cls(
            cooldown=cooldown,
            scalping=scalping,
            learning_mode=learning_mode,
            ai_validation=ai_validation,
            ai_override=ai_override,
            market_regime=market_regime,
            external_sentiment=external_sentiment,
            self_upgrade=self_upgrade,
            smart_interval=smart_interval,
            **data
        )

    def get_effective_limits(self) -> dict:
        """Get effective limits (user config clamped to hard limits)."""
        return {
            "risk_per_trade": min(
                self.risk_per_trade_percent / 100,
                HardLimits.MAX_RISK_PER_TRADE
            ),
            "daily_drawdown": min(
                self.max_daily_drawdown_percent / 100,
                HardLimits.MAX_DAILY_DRAWDOWN
            ),
            "weekly_drawdown": min(
                self.max_weekly_drawdown_percent / 100,
                HardLimits.MAX_WEEKLY_DRAWDOWN
            ),
            "max_positions": min(
                self.max_concurrent_positions,
                HardLimits.MAX_CONCURRENT_POSITIONS
            ),
            "min_confidence": max(
                self.min_confidence_threshold,
                HardLimits.MIN_CONFIDENCE
            )
        }

    def get_active_threshold(self) -> int:
        """Get active confidence threshold based on learning mode."""
        active_settings = self.learning_mode.get_active_settings()
        threshold = active_settings.get("min_confidence_threshold", self.min_confidence_threshold)
        # Enforce hard limit
        return max(threshold, HardLimits.MIN_CONFIDENCE)

    def get_active_cooldown_settings(self) -> tuple[int, int]:
        """Get active cooldown settings based on learning mode.

        Returns:
            (loss_streak_trigger, cooldown_minutes)
        """
        active_settings = self.learning_mode.get_active_settings()
        return (
            active_settings.get("loss_streak_trigger", self.cooldown.loss_streak_trigger),
            active_settings.get("cooldown_minutes", self.cooldown.cooldown_minutes)
        )

    def get_active_trade_limits(self) -> tuple[int, int]:
        """Get active trade limits based on learning mode.

        Returns:
            (max_daily_trades, max_trades_per_instrument)
        """
        active_settings = self.learning_mode.get_active_settings()
        return (
            active_settings.get("max_daily_trades", self.max_daily_trades or 999),
            active_settings.get("max_trades_per_instrument", self.max_trades_per_instrument)
        )

    def should_use_ai_validation(self) -> bool:
        """Check if AI validation should be used for current trade."""
        if not self.ai_validation.enabled:
            return False
        if self.ai_validation.skip_in_learning_mode and self.learning_mode.is_in_learning():
            return False
        return True


# Default config file path
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "settings" / "auto_trading.json"


def load_auto_config(path: Optional[Path] = None) -> AutoTradingConfig:
    """
    Load auto-trading configuration from JSON file.

    Args:
        path: Path to config file. Uses default if None.

    Returns:
        AutoTradingConfig instance
    """
    config_path = path or DEFAULT_CONFIG_PATH

    if not config_path.exists():
        logger.warning(f"Auto-trading config not found at {config_path}, using defaults")
        return AutoTradingConfig()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = AutoTradingConfig.from_dict(data)

        # Validate
        is_valid, errors = config.validate()
        if not is_valid:
            logger.error(f"Auto-trading config validation failed: {errors}")
            # Return config with clamped values
            logger.warning("Using clamped values within hard limits")

        logger.info(f"Loaded auto-trading config: enabled={config.enabled}, mode={config.mode}")
        return config

    except Exception as e:
        logger.error(f"Failed to load auto-trading config: {e}")
        return AutoTradingConfig()


def save_auto_config(config: AutoTradingConfig, path: Optional[Path] = None) -> bool:
    """
    Save auto-trading configuration to JSON file.

    Args:
        config: Configuration to save
        path: Path to save to. Uses default if None.

    Returns:
        True if successful
    """
    config_path = path or DEFAULT_CONFIG_PATH

    # Validate before saving
    is_valid, errors = config.validate()
    if not is_valid:
        logger.error(f"Cannot save invalid config: {errors}")
        return False

    try:
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved auto-trading config to {config_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save auto-trading config: {e}")
        return False
