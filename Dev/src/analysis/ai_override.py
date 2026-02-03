"""
AI Override Evaluator - Evaluates rejected signals for potential override.

When a signal is rejected due to technical filters (spread, MTF conflict, etc.),
this module asks Claude AI whether the signal is still worth taking despite
the technical filter rejection.

Usage:
    from src.analysis.ai_override import AIOverrideEvaluator

    evaluator = AIOverrideEvaluator(config)
    result = evaluator.evaluate_override(context, signal_data, skip_reason)

    if result and result.override_recommended:
        # Apply temporary adjustment and re-evaluate
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from src.core.tuning_config import (
    TunableSettings,
    HardLimits,
    OverrideContext,
    OverrideAdjustment,
)
from src.utils.logger import logger
from src.utils.database import db

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class OverrideResult:
    """Result of AI override evaluation."""
    override_recommended: bool
    ai_confidence: int  # 0-100
    reasoning: str
    suggested_adjustment: Optional[OverrideAdjustment] = None

    # Metadata
    model: str = ""
    latency_ms: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    evaluated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "override_recommended": self.override_recommended,
            "ai_confidence": self.ai_confidence,
            "reasoning": self.reasoning,
            "suggested_adjustment": self.suggested_adjustment.to_dict() if self.suggested_adjustment else None,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass
class AIOverrideConfig:
    """Configuration for AI Override system."""
    enabled: bool = True
    min_ai_confidence: int = 65  # Min AI confidence to approve override
    max_overrides_per_day: int = 10
    cooldown_after_loss_minutes: int = 30

    # Adjustable settings with their bounds
    adjustable_settings: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "max_spread_pips": {"min": 1.5, "max": 3.5},
        "min_atr_pips": {"min": 2.0, "max": 5.0},
        "target_rr": {"min": 1.3, "max": 3.0},
        "min_confidence_threshold": {"min": 50, "max": 70},
        "mtf_strength_threshold": {"min": 40, "max": 80},
        "session_filter": {"can_disable": True},
    })

    # Learning from override outcomes
    learning: Dict[str, Any] = field(default_factory=lambda: {
        "track_outcomes": True,
        "disable_setting_after_losses": 3,  # Disable setting override after N consecutive losses
    })

    @classmethod
    def from_dict(cls, data: dict) -> "AIOverrideConfig":
        """Create config from dictionary."""
        return cls(
            enabled=data.get("enabled", True),
            min_ai_confidence=data.get("min_ai_confidence", 65),
            max_overrides_per_day=data.get("max_overrides_per_day", 10),
            cooldown_after_loss_minutes=data.get("cooldown_after_loss_minutes", 30),
            adjustable_settings=data.get("adjustable_settings", cls().adjustable_settings),
            learning=data.get("learning", cls().learning),
        )


class AIOverrideEvaluator:
    """
    Evaluates rejected signals for potential AI override.

    When a signal is rejected due to technical filters, this evaluator
    asks Claude whether the trade should be taken anyway.
    """

    # Skip reasons that can be overridden
    OVERRIDABLE_REASONS = frozenset([
        "MTF conflict",
        "Spread too high",
        "ATR too low",
        "R:R",
        "Confidence",
        "Outside trading session",
        "Scalping criteria",
    ])

    def __init__(self, config: AIOverrideConfig):
        """
        Initialize override evaluator.

        Args:
            config: AI Override configuration
        """
        self.config = config
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")

        # Track daily overrides
        self._daily_override_count = 0
        self._last_reset_date = datetime.now().date()

        # Track recent losses for cooldown
        self._last_loss_time: Optional[datetime] = None

        # Track losses per setting for learning
        self._setting_losses: Dict[str, int] = {}

        logger.info(f"AIOverrideEvaluator initialized (enabled={config.enabled})")

    def is_available(self) -> bool:
        """Check if evaluator is available."""
        if not self.config.enabled:
            return False
        if not ANTHROPIC_AVAILABLE:
            return False
        if not self.api_key:
            return False
        return True

    def can_override(self, skip_reason: str) -> bool:
        """
        Check if a skip reason can potentially be overridden.

        Args:
            skip_reason: The reason the signal was rejected

        Returns:
            True if this type of rejection can be overridden
        """
        if not self.is_available():
            return False

        # Reset daily counter if new day
        today = datetime.now().date()
        if today != self._last_reset_date:
            self._daily_override_count = 0
            self._last_reset_date = today

        # Check daily limit
        if self._daily_override_count >= self.config.max_overrides_per_day:
            logger.info(f"Daily override limit reached ({self.config.max_overrides_per_day})")
            return False

        # Check cooldown after loss
        if self._last_loss_time:
            cooldown_end = self._last_loss_time + timedelta(minutes=self.config.cooldown_after_loss_minutes)
            if datetime.now() < cooldown_end:
                remaining = (cooldown_end - datetime.now()).seconds // 60
                logger.info(f"Override cooldown active ({remaining} min remaining)")
                return False

        # Check if skip reason is overridable
        for overridable in self.OVERRIDABLE_REASONS:
            if overridable.lower() in skip_reason.lower():
                return True

        return False

    def _identify_setting_to_adjust(self, skip_reason: str) -> Optional[str]:
        """
        Identify which setting needs adjustment based on skip reason.

        Args:
            skip_reason: The rejection reason

        Returns:
            Setting name to adjust, or None
        """
        reason_lower = skip_reason.lower()

        if "spread" in reason_lower:
            return "max_spread_pips"
        elif "atr" in reason_lower:
            return "min_atr_pips"
        elif "r:r" in reason_lower or "risk reward" in reason_lower:
            return "target_rr"
        elif "confidence" in reason_lower:
            return "min_confidence_threshold"
        elif "mtf" in reason_lower:
            return "mtf_strength_threshold"
        elif "session" in reason_lower:
            return "session_filter_enabled"

        return None

    def _build_override_prompt(
        self,
        context: OverrideContext,
        signal_data: Dict[str, Any]
    ) -> str:
        """Build prompt for AI override evaluation."""

        # Get adjustable settings info
        setting_to_adjust = self._identify_setting_to_adjust(context.skip_reason)
        setting_info = ""
        if setting_to_adjust:
            bounds = TunableSettings.get_bounds(setting_to_adjust)
            if bounds:
                setting_info = f"""
SETTING TO ADJUST: {setting_to_adjust}
- Current logic rejected because: {context.skip_reason}
- Adjustable range: {bounds.min_value} to {bounds.max_value}
- Default value: {bounds.default_value}
"""

        prompt = f"""You are an AI trading override evaluator. A signal was REJECTED by technical filters.
Your job is to decide if this rejection should be OVERRIDDEN.

REJECTED SIGNAL:
- Instrument: {context.instrument}
- Direction: {context.direction}
- Confidence Score: {context.confidence}%

REJECTION REASON: {context.skip_reason}

MARKET DATA:
- Price: {signal_data.get('price', 'N/A')}
- Spread: {context.spread_pips:.1f} pips
- ATR: {context.atr_pips:.1f} pips
- RSI: {signal_data.get('rsi', 'N/A')}
- MACD: {signal_data.get('macd_trend', 'N/A')}
- M5 Trend: {signal_data.get('m5_trend', 'N/A')}
- H1 Trend: {signal_data.get('h1_trend', 'N/A')} ({signal_data.get('h1_strength', 'N/A')}%)

CONFIDENCE BREAKDOWN:
- Technical: {signal_data.get('tech_score', 'N/A')}%
- Sentiment: {signal_data.get('sentiment_score', 'N/A')}
- Adversarial: {signal_data.get('adv_score', 'N/A')}%
{setting_info}
OVERRIDE RULES:
1. Override ONLY if you believe the trade is likely profitable despite the rejection reason
2. For MTF conflict: Override only if HTF opposition is weak (<75%) and LTF setup is strong
3. For spread: Override only if signal confidence is very high (>80%)
4. For ATR: Override only during killzones or if trend is very clear
5. NEVER suggest adjustments outside the allowed range
6. Your confidence must be >= 65 to recommend override

IMPORTANT: This is a TEMPORARY override for this ONE trade only.
Hard limits (risk %, drawdown) can NEVER be overridden.

Respond with ONLY valid JSON:
{{
  "override_recommended": true/false,
  "confidence": 0-100,
  "reasoning": "1-2 sentence explanation",
  "suggested_adjustment": {{
    "setting": "setting_name",
    "new_value": value_within_bounds
  }}
}}

If you don't recommend override, set suggested_adjustment to null.
"""
        return prompt

    def evaluate_override(
        self,
        context: OverrideContext,
        signal_data: Dict[str, Any],
        skip_reason: str
    ) -> Optional[OverrideResult]:
        """
        Evaluate whether a rejected signal should be overridden.

        Args:
            context: Override context with instrument, direction, etc.
            signal_data: Full signal data for AI analysis
            skip_reason: Reason the signal was rejected

        Returns:
            OverrideResult with AI decision, or None if evaluation failed
        """
        if not self.can_override(skip_reason):
            return None

        # Check if the setting to adjust has too many losses
        setting_to_adjust = self._identify_setting_to_adjust(skip_reason)
        if setting_to_adjust:
            loss_count = self._setting_losses.get(setting_to_adjust, 0)
            max_losses = self.config.learning.get("disable_setting_after_losses", 3)
            if loss_count >= max_losses:
                logger.warning(f"Setting {setting_to_adjust} disabled after {loss_count} consecutive losses")
                return None

        prompt = self._build_override_prompt(context, signal_data)

        try:
            start = time.perf_counter()
            client = Anthropic(api_key=self.api_key)

            # Use faster model for override evaluation
            override_model = os.getenv("OVERRIDE_MODEL", "claude-sonnet-4-20250514")

            message = client.messages.create(
                model=override_model,
                max_tokens=300,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            latency_ms = int((time.perf_counter() - start) * 1000)

            content = message.content[0].text if message and message.content else ""
            logger.info(f"AI Override response ({latency_ms}ms): {content[:150]}")

            # Parse JSON response
            try:
                # Handle potential markdown code blocks
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                parsed = json.loads(content.strip())
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse AI override response: {content[:100]}")
                return None

            usage = getattr(message, "usage", None)

            # Extract suggested adjustment
            adjustment = None
            suggested = parsed.get("suggested_adjustment")
            if suggested and isinstance(suggested, dict):
                setting_name = suggested.get("setting")
                new_value = suggested.get("new_value")

                if setting_name and new_value is not None:
                    # Validate adjustment
                    is_valid, error = TunableSettings.validate_adjustment(setting_name, new_value)
                    if is_valid:
                        # Get current value from context or defaults
                        bounds = TunableSettings.get_bounds(setting_name)
                        original_value = bounds.default_value if bounds else new_value

                        adjustment = OverrideAdjustment(
                            setting_name=setting_name,
                            original_value=original_value,
                            new_value=TunableSettings.get_safe_value(setting_name, new_value),
                            reason=parsed.get("reasoning", "AI override")
                        )
                    else:
                        logger.warning(f"Invalid adjustment rejected: {error}")

            # Build result
            ai_confidence = int(parsed.get("confidence", 0))
            override_recommended = (
                parsed.get("override_recommended", False) and
                ai_confidence >= self.config.min_ai_confidence
            )

            result = OverrideResult(
                override_recommended=override_recommended,
                ai_confidence=ai_confidence,
                reasoning=parsed.get("reasoning", "No reasoning provided"),
                suggested_adjustment=adjustment if override_recommended else None,
                model=override_model,
                latency_ms=latency_ms,
                input_tokens=getattr(usage, "input_tokens", None) if usage else None,
                output_tokens=getattr(usage, "output_tokens", None) if usage else None,
            )

            # Log to database
            self._log_override_decision(context, result, skip_reason)

            # Increment daily counter if override recommended
            if override_recommended:
                self._daily_override_count += 1

            return result

        except Exception as e:
            logger.error(f"AI override evaluation failed: {e}")
            return None

    def _log_override_decision(
        self,
        context: OverrideContext,
        result: OverrideResult,
        skip_reason: str
    ):
        """Log override decision to database."""
        try:
            db.log_override({
                "instrument": context.instrument,
                "direction": context.direction,
                "original_skip_reason": skip_reason,
                "original_confidence": context.confidence,
                "override_recommended": result.override_recommended,
                "ai_confidence": result.ai_confidence,
                "ai_reasoning": result.reasoning,
                "suggested_adjustment": json.dumps(result.suggested_adjustment.to_dict()) if result.suggested_adjustment else None,
                "adjustment_applied": result.suggested_adjustment.setting_name if result.suggested_adjustment else None,
                "adjustment_value": str(result.suggested_adjustment.new_value) if result.suggested_adjustment else None,
            })
        except Exception as e:
            logger.warning(f"Failed to log override decision: {e}")

        # Also log to activity log
        db.log_activity({
            "activity_type": "AI_OVERRIDE_EVAL",
            "instrument": context.instrument,
            "direction": context.direction,
            "confidence": result.ai_confidence,
            "decision": "OVERRIDE_APPROVED" if result.override_recommended else "OVERRIDE_REJECTED",
            "reasoning": result.reasoning,
            "details": {
                "skip_reason": skip_reason,
                "original_confidence": context.confidence,
                "adjustment": result.suggested_adjustment.to_dict() if result.suggested_adjustment else None,
                "latency_ms": result.latency_ms,
            }
        })

    def record_trade_outcome(
        self,
        instrument: str,
        direction: str,
        adjustment_setting: str,
        outcome: str,  # WIN, LOSS, BREAKEVEN
        pnl: float
    ):
        """
        Record the outcome of an override trade for learning.

        Args:
            instrument: Traded instrument
            direction: Trade direction
            adjustment_setting: The setting that was adjusted
            outcome: Trade outcome (WIN/LOSS/BREAKEVEN)
            pnl: Profit/loss amount
        """
        # Update database
        try:
            db.update_override_result(
                instrument=instrument,
                direction=direction,
                trade_outcome=outcome,
                pnl=pnl
            )
        except Exception as e:
            logger.warning(f"Failed to update override result: {e}")

        # Update loss tracking for learning
        if outcome == "LOSS":
            self._setting_losses[adjustment_setting] = self._setting_losses.get(adjustment_setting, 0) + 1
            self._last_loss_time = datetime.now()
            logger.info(f"Override loss recorded for {adjustment_setting}: {self._setting_losses[adjustment_setting]} consecutive")
        elif outcome == "WIN":
            # Reset loss counter on win
            self._setting_losses[adjustment_setting] = 0

    def get_override_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get override statistics."""
        return {
            "daily_override_count": self._daily_override_count,
            "daily_limit": self.config.max_overrides_per_day,
            "setting_losses": dict(self._setting_losses),
            "cooldown_active": self._last_loss_time is not None and
                             datetime.now() < self._last_loss_time + timedelta(minutes=self.config.cooldown_after_loss_minutes),
        }


# Singleton instance (initialized lazily)
_override_evaluator: Optional[AIOverrideEvaluator] = None


def get_override_evaluator(config: Optional[AIOverrideConfig] = None) -> AIOverrideEvaluator:
    """Get or create the override evaluator singleton."""
    global _override_evaluator
    if _override_evaluator is None:
        if config is None:
            config = AIOverrideConfig()
        _override_evaluator = AIOverrideEvaluator(config)
    return _override_evaluator
