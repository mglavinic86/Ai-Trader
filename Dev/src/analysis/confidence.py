"""
Confidence Calculator - Combines all analysis into final confidence score.

Usage:
    from src.analysis.confidence import ConfidenceCalculator

    calc = ConfidenceCalculator()
    result = calc.calculate(technical, sentiment, adversarial, rag_warnings)
"""

from dataclasses import dataclass, field
from typing import Optional

from src.market.indicators import TechnicalAnalysis
from src.analysis.sentiment import SentimentResult
from src.analysis.adversarial import AdversarialResult
from src.utils.config import config
from src.utils.logger import logger


@dataclass
class ConfidenceResult:
    """Result of confidence calculation."""
    # Final score
    confidence_score: int  # 0-100

    # Component scores
    technical_score: int
    sentiment_score: int
    adversarial_adjustment: int
    rag_penalty: int

    # Risk tier
    risk_tier: str
    risk_percent: float
    can_trade: bool

    # Breakdown
    breakdown: dict = field(default_factory=dict)

    # Analysis summary (for display)
    bull_case: str = ""
    bear_case: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "confidence_score": self.confidence_score,
            "technical_score": self.technical_score,
            "sentiment_score": self.sentiment_score,
            "adversarial_adjustment": self.adversarial_adjustment,
            "rag_penalty": self.rag_penalty,
            "risk_tier": self.risk_tier,
            "risk_percent": self.risk_percent,
            "can_trade": self.can_trade,
            "breakdown": self.breakdown,
            "bull_case": self.bull_case,
            "bear_case": self.bear_case
        }

    def format_summary(self) -> str:
        """Format as readable summary."""
        trade_status = "✅ CAN TRADE" if self.can_trade else "❌ DO NOT TRADE"

        return f"""
📊 CONFIDENCE CALCULATION
━━━━━━━━━━━━━━━━━━━━━━━━

Component Scores:
• Technical:   {self.technical_score:>3}/100
• Sentiment:   {self.sentiment_score:>3}/100
• Adversarial: {self.adversarial_adjustment:>+3}
• RAG Penalty: {self.rag_penalty:>+3}
━━━━━━━━━━━━━━━━━━━━
CONFIDENCE:    {self.confidence_score:>3}/100

Risk Tier: {self.risk_tier}
Max Risk:  {self.risk_percent*100:.0f}%

{trade_status}
"""


class ConfidenceCalculator:
    """
    Calculates final confidence score from all analysis components.

    Weights:
    - Technical: 40%
    - Sentiment: 30%
    - Adversarial: adjustment
    - RAG: penalty
    """

    # Weights
    TECHNICAL_WEIGHT = 0.45
    SENTIMENT_WEIGHT = 0.30
    BASE_SCORE = 0.25  # 25% base to start from

    def __init__(self):
        """Initialize calculator."""
        pass

    def calculate(
        self,
        technical: TechnicalAnalysis,
        sentiment: SentimentResult,
        adversarial: Optional[AdversarialResult] = None,
        rag_warnings: int = 0
    ) -> ConfidenceResult:
        """
        Calculate final confidence score.

        Args:
            technical: Technical analysis result
            sentiment: Sentiment analysis result
            adversarial: Adversarial analysis result (optional)
            rag_warnings: Number of similar past errors found

        Returns:
            ConfidenceResult
        """
        breakdown = {}

        # === TECHNICAL SCORE (0-100) ===
        tech_score = technical.technical_score
        breakdown["technical_raw"] = tech_score

        # === SENTIMENT SCORE (0-100) ===
        # Convert -1 to +1 range to 0-100
        sent_score = int((sentiment.sentiment_score + 1) * 50)
        sent_score = max(0, min(100, sent_score))
        breakdown["sentiment_raw"] = sent_score

        # === BASE CALCULATION ===
        base_confidence = int(
            (tech_score * self.TECHNICAL_WEIGHT) +
            (sent_score * self.SENTIMENT_WEIGHT) +
            (50 * self.BASE_SCORE)  # Base contribution
        )
        breakdown["base_confidence"] = base_confidence

        # === ADVERSARIAL ADJUSTMENT ===
        adv_adjustment = 0
        if adversarial:
            adv_adjustment = adversarial.confidence_adjustment
        breakdown["adversarial_adjustment"] = adv_adjustment

        # === RAG PENALTY ===
        # Each warning reduces confidence by 10, max 30
        rag_penalty = min(rag_warnings * 10, 30) * -1
        breakdown["rag_penalty"] = rag_penalty

        # === FINAL SCORE ===
        final_score = base_confidence + adv_adjustment + rag_penalty
        final_score = max(0, min(100, final_score))

        # === DETERMINE RISK TIER ===
        risk_percent = config.get_risk_percent(final_score)

        if final_score >= 90:
            risk_tier = "TIER 3 (High Confidence)"
        elif final_score >= 70:
            risk_tier = "TIER 2 (Good Confidence)"
        elif final_score >= 50:
            risk_tier = "TIER 1 (Moderate Confidence)"
        else:
            risk_tier = "NO TRADE (Low Confidence)"

        can_trade = final_score >= config.MIN_CONFIDENCE_TO_TRADE

        logger.info(
            f"Confidence calculated: {final_score}% "
            f"(tech={tech_score}, sent={sent_score}, adv={adv_adjustment}, rag={rag_penalty})"
        )

        # Generate bull/bear case summaries
        bull_points = []
        bear_points = []

        # Technical factors
        if tech_score >= 60:
            bull_points.append(f"Strong technical setup ({tech_score}%)")
        elif tech_score <= 40:
            bear_points.append(f"Weak technical setup ({tech_score}%)")

        if technical.trend == "BULLISH":
            bull_points.append(f"Bullish trend")
        elif technical.trend == "BEARISH":
            bear_points.append(f"Bearish trend")

        if technical.rsi < 30:
            bull_points.append(f"RSI oversold ({technical.rsi:.0f})")
        elif technical.rsi > 70:
            bear_points.append(f"RSI overbought ({technical.rsi:.0f})")

        # Sentiment factors
        if sent_score >= 60:
            bull_points.append(f"Positive sentiment ({sent_score}%)")
        elif sent_score <= 40:
            bear_points.append(f"Negative sentiment ({sent_score}%)")

        # External sentiment factors (Phase 2 Enhancement)
        if hasattr(sentiment, 'has_external') and sentiment.has_external:
            if sentiment.external_score > 0.3:
                bull_points.append(f"External bullish ({sentiment.external_score:+.2f})")
                if sentiment.external_reasoning:
                    bull_points.append(f"News: {sentiment.external_reasoning[:50]}...")
            elif sentiment.external_score < -0.3:
                bear_points.append(f"External bearish ({sentiment.external_score:+.2f})")
                if sentiment.external_reasoning:
                    bear_points.append(f"News: {sentiment.external_reasoning[:50]}...")

        # Adversarial factors
        if adv_adjustment > 0:
            bull_points.append(f"Adversarial boost (+{adv_adjustment})")
        elif adv_adjustment < 0:
            bear_points.append(f"Adversarial warning ({adv_adjustment})")

        # RAG factors
        if rag_penalty < 0:
            bear_points.append(f"Similar past errors found ({rag_penalty})")

        bull_case = "; ".join(bull_points) if bull_points else "No strong bullish factors"
        bear_case = "; ".join(bear_points) if bear_points else "No significant bearish factors"

        return ConfidenceResult(
            confidence_score=final_score,
            technical_score=tech_score,
            sentiment_score=sent_score,
            adversarial_adjustment=adv_adjustment,
            rag_penalty=rag_penalty,
            risk_tier=risk_tier,
            risk_percent=risk_percent,
            can_trade=can_trade,
            breakdown=breakdown,
            bull_case=bull_case,
            bear_case=bear_case
        )


def calculate_confidence(
    technical: TechnicalAnalysis,
    sentiment: SentimentResult,
    adversarial: Optional[AdversarialResult] = None,
    rag_warnings: int = 0
) -> ConfidenceResult:
    """
    Convenience function for confidence calculation.

    Args:
        technical: Technical analysis
        sentiment: Sentiment analysis
        adversarial: Adversarial analysis (optional)
        rag_warnings: Number of RAG warnings

    Returns:
        ConfidenceResult
    """
    calc = ConfidenceCalculator()
    return calc.calculate(technical, sentiment, adversarial, rag_warnings)
