"""
Adversarial Thinking Engine - Bull vs Bear debate.

Before every trade decision, generate both bull and bear cases
to ensure balanced analysis.

Usage:
    from src.analysis.adversarial import AdversarialEngine

    engine = AdversarialEngine()
    result = engine.analyze(technical, sentiment, instrument)
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from src.market.indicators import TechnicalAnalysis
from src.analysis.sentiment import SentimentResult
from src.utils.logger import logger


@dataclass
class CasePoint:
    """A single point in bull or bear case."""
    argument: str
    weight: float  # 0.0 to 1.0
    category: str  # TECHNICAL, FUNDAMENTAL, SENTIMENT, RISK


@dataclass
class AdversarialResult:
    """Result of adversarial analysis."""
    # Cases
    bull_case: list[CasePoint]
    bear_case: list[CasePoint]

    # Scores
    bull_score: float  # 0-100
    bear_score: float  # 0-100

    # Verdict
    verdict: str  # STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL
    confidence_adjustment: int  # -30 to +30

    # Warnings
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "bull_case": [{"argument": p.argument, "weight": p.weight, "category": p.category} for p in self.bull_case],
            "bear_case": [{"argument": p.argument, "weight": p.weight, "category": p.category} for p in self.bear_case],
            "bull_score": self.bull_score,
            "bear_score": self.bear_score,
            "verdict": self.verdict,
            "confidence_adjustment": self.confidence_adjustment,
            "warnings": self.warnings
        }

    def format_summary(self) -> str:
        """Format as readable summary."""
        bull_points = "\n".join([f"  ✓ {p.argument}" for p in self.bull_case])
        bear_points = "\n".join([f"  ✗ {p.argument}" for p in self.bear_case])

        warnings_str = ""
        if self.warnings:
            warnings_str = "\n⚠️ WARNINGS:\n" + "\n".join([f"  • {w}" for w in self.warnings])

        return f"""
⚔️ ADVERSARIAL ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━

✅ BULL CASE (Score: {self.bull_score:.0f})
{bull_points}

❌ BEAR CASE (Score: {self.bear_score:.0f})
{bear_points}
{warnings_str}

📋 VERDICT: {self.verdict}
   Confidence adjustment: {self.confidence_adjustment:+d}
"""


class AdversarialEngine:
    """
    Generates bull and bear cases for trade decisions.

    This ensures we always consider both sides before trading.
    """

    def __init__(self):
        """Initialize engine."""
        pass

    def analyze(
        self,
        technical: TechnicalAnalysis,
        sentiment: SentimentResult,
        instrument: str,
        direction: str = "LONG",  # LONG or SHORT
        current_price: Optional[float] = None,
        upcoming_events: list[str] = None
    ) -> AdversarialResult:
        """
        Generate bull and bear cases for a potential trade.

        Args:
            technical: Technical analysis result
            sentiment: Sentiment analysis result
            instrument: Currency pair
            direction: Proposed trade direction
            current_price: Current price
            upcoming_events: List of upcoming news events

        Returns:
            AdversarialResult with both cases and verdict
        """
        bull_points = []
        bear_points = []
        warnings = []

        # === TECHNICAL FACTORS ===

        # Trend
        if technical.trend == "BULLISH":
            bull_points.append(CasePoint(
                f"Trend is bullish (EMA20 > EMA50)",
                0.8, "TECHNICAL"
            ))
        elif technical.trend == "BEARISH":
            bear_points.append(CasePoint(
                f"Trend is bearish (EMA20 < EMA50)",
                0.8, "TECHNICAL"
            ))
        else:
            bear_points.append(CasePoint(
                "Market is ranging - no clear trend",
                0.5, "TECHNICAL"
            ))

        # RSI
        if technical.rsi_signal == "OVERBOUGHT":
            bear_points.append(CasePoint(
                f"RSI overbought ({technical.rsi:.1f}) - reversal risk",
                0.7, "TECHNICAL"
            ))
            if direction == "LONG":
                warnings.append("Entering LONG when RSI is overbought")
        elif technical.rsi_signal == "OVERSOLD":
            bull_points.append(CasePoint(
                f"RSI oversold ({technical.rsi:.1f}) - bounce potential",
                0.7, "TECHNICAL"
            ))
            if direction == "SHORT":
                warnings.append("Entering SHORT when RSI is oversold")
        else:
            bull_points.append(CasePoint(
                f"RSI neutral ({technical.rsi:.1f}) - room to move",
                0.4, "TECHNICAL"
            ))

        # MACD
        if technical.macd_trend == "BULLISH":
            bull_points.append(CasePoint(
                "MACD histogram positive - bullish momentum",
                0.6, "TECHNICAL"
            ))
        else:
            bear_points.append(CasePoint(
                "MACD histogram negative - bearish momentum",
                0.6, "TECHNICAL"
            ))

        # Support/Resistance
        if technical.distance_to_support_pips and technical.distance_to_support_pips < 20:
            bull_points.append(CasePoint(
                f"Near support ({technical.distance_to_support_pips:.0f} pips) - good for long",
                0.7, "TECHNICAL"
            ))
        if technical.distance_to_resistance_pips and technical.distance_to_resistance_pips < 30:
            bear_points.append(CasePoint(
                f"Resistance nearby ({technical.distance_to_resistance_pips:.0f} pips) - upside limited",
                0.6, "TECHNICAL"
            ))

        # === SENTIMENT FACTORS ===

        if sentiment.sentiment_score > 0.3:
            bull_points.append(CasePoint(
                f"Sentiment bullish ({sentiment.sentiment_score:+.2f})",
                0.5, "SENTIMENT"
            ))
        elif sentiment.sentiment_score < -0.3:
            bear_points.append(CasePoint(
                f"Sentiment bearish ({sentiment.sentiment_score:+.2f})",
                0.5, "SENTIMENT"
            ))

        if sentiment.is_trending:
            if sentiment.trend_direction == "UP":
                bull_points.append(CasePoint(
                    "Market trending UP",
                    0.5, "SENTIMENT"
                ))
            elif sentiment.trend_direction == "DOWN":
                bear_points.append(CasePoint(
                    "Market trending DOWN",
                    0.5, "SENTIMENT"
                ))

        # === RISK FACTORS ===

        # Volatility (ATR)
        if technical.atr_pips > 50:
            bear_points.append(CasePoint(
                f"High volatility (ATR: {technical.atr_pips:.0f} pips) - wider stops needed",
                0.4, "RISK"
            ))
            warnings.append("High volatility environment")

        # Upcoming events
        if upcoming_events:
            for event in upcoming_events:
                bear_points.append(CasePoint(
                    f"Upcoming event: {event}",
                    0.7, "RISK"
                ))
            warnings.append(f"{len(upcoming_events)} upcoming event(s) - increased risk")

        # === CALCULATE SCORES ===

        bull_score = self._calculate_case_score(bull_points)
        bear_score = self._calculate_case_score(bear_points)

        # Adjust for direction
        if direction == "SHORT":
            # Swap perspective for short trades
            bull_score, bear_score = bear_score, bull_score

        # Determine verdict
        verdict, confidence_adj = self._determine_verdict(bull_score, bear_score)

        # Add warning if bear case is strong
        if bear_score > 60:
            warnings.append("Strong BEAR case - consider reducing position size")

        return AdversarialResult(
            bull_case=bull_points,
            bear_case=bear_points,
            bull_score=bull_score,
            bear_score=bear_score,
            verdict=verdict,
            confidence_adjustment=confidence_adj,
            warnings=warnings
        )

    def _calculate_case_score(self, points: list[CasePoint]) -> float:
        """Calculate overall score for a case (0-100)."""
        if not points:
            return 0.0

        total_weight = sum(p.weight for p in points)
        if total_weight == 0:
            return 0.0

        # Weighted average, scaled to 0-100
        weighted_sum = sum(p.weight * 50 for p in points)  # Each point contributes up to 50
        score = weighted_sum / len(points)

        return min(100, score)

    def _determine_verdict(self, bull_score: float, bear_score: float) -> tuple[str, int]:
        """
        Determine verdict and confidence adjustment.

        Returns:
            (verdict, confidence_adjustment)
        """
        diff = bull_score - bear_score

        if diff > 30:
            return "STRONG_BUY", +15
        elif diff > 10:
            return "BUY", +5
        elif diff > -10:
            return "NEUTRAL", -10
        elif diff > -30:
            return "SELL", -15
        else:
            return "STRONG_SELL", -25


def generate_adversarial_analysis(
    technical: TechnicalAnalysis,
    sentiment: SentimentResult,
    instrument: str,
    direction: str = "LONG"
) -> AdversarialResult:
    """
    Convenience function for quick adversarial analysis.

    Args:
        technical: Technical analysis
        sentiment: Sentiment analysis
        instrument: Currency pair
        direction: Trade direction

    Returns:
        AdversarialResult
    """
    engine = AdversarialEngine()
    return engine.analyze(technical, sentiment, instrument, direction)
