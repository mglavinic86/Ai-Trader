"""
Sentiment Analysis - Price action and momentum-based sentiment.

Phase 2 Enhancement: Optional external sentiment integration
from news, VIX, and economic calendar.

Usage:
    from src.analysis.sentiment import SentimentAnalyzer

    analyzer = SentimentAnalyzer()
    result = analyzer.analyze(candles, technical_analysis)

    # With external sentiment
    result = analyzer.analyze(candles, technical_analysis, instrument="EUR_USD", use_external=True)
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

from src.market.indicators import TechnicalAnalysis
from src.utils.logger import logger


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    # Overall sentiment
    sentiment_score: float  # -1.0 (bearish) to +1.0 (bullish)
    sentiment_label: str  # VERY_BEARISH, BEARISH, NEUTRAL, BULLISH, VERY_BULLISH

    # Components
    price_action_score: float
    momentum_score: float
    volatility_score: float

    # Flags
    is_trending: bool
    trend_direction: str  # UP, DOWN, FLAT

    # External sentiment (Phase 2 Enhancement)
    external_score: float = 0.0
    external_confidence: float = 0.0
    external_reasoning: str = ""
    has_external: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.sentiment_label,
            "price_action_score": self.price_action_score,
            "momentum_score": self.momentum_score,
            "volatility_score": self.volatility_score,
            "is_trending": self.is_trending,
            "trend_direction": self.trend_direction,
            "external_score": self.external_score,
            "external_confidence": self.external_confidence,
            "external_reasoning": self.external_reasoning,
            "has_external": self.has_external,
        }

    def format_summary(self) -> str:
        """Format as readable summary."""
        emoji = "🟢" if self.sentiment_score > 0.3 else "🔴" if self.sentiment_score < -0.3 else "🟡"
        return f"""
🎯 SENTIMENT ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━
Overall: {emoji} {self.sentiment_score:+.2f} ({self.sentiment_label})

Components:
• Price Action: {self.price_action_score:+.2f}
• Momentum:     {self.momentum_score:+.2f}
• Volatility:   {self.volatility_score:+.2f}

Trending: {'Yes' if self.is_trending else 'No'} ({self.trend_direction})
"""


class SentimentAnalyzer:
    """Analyzes market sentiment from price action."""

    def __init__(self, use_external: bool = False):
        """
        Initialize analyzer.

        Args:
            use_external: Whether to include external sentiment by default
        """
        self._use_external = use_external
        self._aggregator = None

    def _get_aggregator(self):
        """Lazy load sentiment aggregator."""
        if self._aggregator is None:
            try:
                from src.sentiment.aggregator import SentimentAggregator
                self._aggregator = SentimentAggregator()
            except Exception as e:
                logger.warning(f"Could not load SentimentAggregator: {e}")
                return None
        return self._aggregator

    def analyze(
        self,
        candles: list[dict],
        technical: Optional[TechnicalAnalysis] = None,
        instrument: str = None,
        use_external: bool = None
    ) -> SentimentResult:
        """
        Analyze sentiment from candle data.

        Args:
            candles: OHLCV candle data
            technical: Optional pre-calculated technical analysis
            instrument: Currency pair (required for external sentiment)
            use_external: Override default external sentiment usage

        Returns:
            SentimentResult
        """
        df = pd.DataFrame(candles)

        # Calculate component scores
        price_action = self._price_action_sentiment(df)
        momentum = self._momentum_sentiment(df, technical)
        volatility = self._volatility_sentiment(df)

        # Combine scores with weights
        # Price action: 50%, Momentum: 35%, Volatility: 15%
        combined = (price_action * 0.50) + (momentum * 0.35) + (volatility * 0.15)

        # External sentiment (Phase 2 Enhancement)
        external_score = 0.0
        external_confidence = 0.0
        external_reasoning = ""
        has_external = False

        should_use_external = use_external if use_external is not None else self._use_external

        if should_use_external and instrument:
            external_score, external_confidence, external_reasoning = self._get_external_sentiment(
                instrument, combined
            )
            if external_confidence > 0:
                has_external = True
                # Blend external with internal (40% external, 60% internal)
                combined = (combined * 0.60) + (external_score * 0.40)

        # Determine label
        label = self._score_to_label(combined)

        # Determine if trending
        is_trending, trend_dir = self._check_trend(df)

        return SentimentResult(
            sentiment_score=round(combined, 2),
            sentiment_label=label,
            price_action_score=round(price_action, 2),
            momentum_score=round(momentum, 2),
            volatility_score=round(volatility, 2),
            is_trending=is_trending,
            trend_direction=trend_dir,
            external_score=round(external_score, 2),
            external_confidence=round(external_confidence, 2),
            external_reasoning=external_reasoning,
            has_external=has_external,
        )

    def _get_external_sentiment(
        self,
        instrument: str,
        price_action_sentiment: float
    ) -> tuple[float, float, str]:
        """
        Get external sentiment from aggregator.

        Args:
            instrument: Currency pair
            price_action_sentiment: Current price action sentiment

        Returns:
            (score, confidence, reasoning)
        """
        aggregator = self._get_aggregator()
        if aggregator is None:
            return 0.0, 0.0, ""

        try:
            result = aggregator.get_combined_sentiment(
                instrument,
                price_action_sentiment=price_action_sentiment
            )
            return result.score, result.confidence, result.claude_reasoning
        except Exception as e:
            logger.warning(f"External sentiment failed for {instrument}: {e}")
            return 0.0, 0.0, ""

    def _price_action_sentiment(self, df: pd.DataFrame) -> float:
        """
        Calculate sentiment from recent price action.

        Returns: -1.0 to +1.0
        """
        if len(df) < 10:
            return 0.0

        # Look at last 10 candles
        recent = df.iloc[-10:]

        # Count bullish vs bearish candles
        bullish = 0
        bearish = 0

        for _, candle in recent.iterrows():
            if candle['close'] > candle['open']:
                bullish += 1
            elif candle['close'] < candle['open']:
                bearish += 1

        # Calculate ratio
        total = bullish + bearish
        if total == 0:
            return 0.0

        ratio = (bullish - bearish) / total

        # Also check recent price change
        start_price = recent['close'].iloc[0]
        end_price = recent['close'].iloc[-1]
        price_change = (end_price - start_price) / start_price

        # Combine (50/50)
        return (ratio + (price_change * 100)) / 2

    def _momentum_sentiment(self, df: pd.DataFrame, technical: Optional[TechnicalAnalysis]) -> float:
        """
        Calculate sentiment from momentum indicators.

        Returns: -1.0 to +1.0
        """
        if technical is None:
            return 0.0

        score = 0.0

        # RSI contribution
        if technical.rsi > 70:
            score -= 0.5  # Overbought = bearish
        elif technical.rsi < 30:
            score += 0.5  # Oversold = bullish
        elif technical.rsi > 50:
            score += (technical.rsi - 50) / 40  # Scale 50-70 to 0-0.5
        else:
            score -= (50 - technical.rsi) / 40  # Scale 30-50 to -0.5-0

        # MACD contribution
        if technical.macd_histogram > 0:
            score += 0.3
        else:
            score -= 0.3

        # EMA trend contribution
        if technical.price_vs_ema20 == "ABOVE":
            score += 0.2
        else:
            score -= 0.2

        return max(-1.0, min(1.0, score))

    def _volatility_sentiment(self, df: pd.DataFrame) -> float:
        """
        Calculate sentiment from volatility.

        Low volatility = neutral, high volatility = caution

        Returns: -1.0 to +1.0
        """
        if len(df) < 14:
            return 0.0

        # Calculate simple volatility (range as % of price)
        recent = df.iloc[-14:]
        avg_range = (recent['high'] - recent['low']).mean()
        avg_price = recent['close'].mean()
        volatility = avg_range / avg_price * 100

        # Low volatility (< 0.5%) = slightly positive (good for trading)
        # Medium volatility (0.5-1%) = neutral
        # High volatility (> 1%) = negative (risky)

        if volatility < 0.5:
            return 0.2
        elif volatility < 1.0:
            return 0.0
        else:
            return -0.3

    def _score_to_label(self, score: float) -> str:
        """Convert score to label."""
        if score >= 0.6:
            return "VERY_BULLISH"
        elif score >= 0.2:
            return "BULLISH"
        elif score > -0.2:
            return "NEUTRAL"
        elif score > -0.6:
            return "BEARISH"
        else:
            return "VERY_BEARISH"

    def _check_trend(self, df: pd.DataFrame) -> tuple[bool, str]:
        """Check if market is trending."""
        if len(df) < 20:
            return False, "FLAT"

        # Simple trend check using price change over 20 candles
        start = df['close'].iloc[-20]
        end = df['close'].iloc[-1]
        change = (end - start) / start * 100

        if change > 0.5:
            return True, "UP"
        elif change < -0.5:
            return True, "DOWN"
        else:
            return False, "FLAT"


def analyze_sentiment(candles: list[dict], technical: Optional[TechnicalAnalysis] = None) -> SentimentResult:
    """
    Convenience function for quick sentiment analysis.

    Args:
        candles: OHLCV candle data
        technical: Optional technical analysis

    Returns:
        SentimentResult
    """
    analyzer = SentimentAnalyzer()
    return analyzer.analyze(candles, technical)
