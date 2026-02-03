"""
Sentiment Aggregator - Combines Multiple Sentiment Sources.

Weights:
- Price Action (existing): 30%
- Claude News Analysis: 35%
- VIX Correlation: 15%
- Economic Calendar: 20%

Usage:
    from src.sentiment.aggregator import SentimentAggregator

    aggregator = SentimentAggregator()
    result = aggregator.get_combined_sentiment("EUR_USD")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from src.sentiment.base_provider import BaseSentimentProvider, ProviderSentiment
from src.sentiment.providers.news_provider import NewsProvider
from src.sentiment.providers.vix_provider import VIXProvider
from src.sentiment.providers.calendar_provider import CalendarProvider
from src.utils.logger import logger


@dataclass
class EnhancedSentimentResult:
    """Combined sentiment from all providers."""
    # Final combined score
    score: float  # -1.0 to +1.0
    confidence: float  # 0.0 to 1.0

    # Component scores
    price_action_score: float = 0.0
    news_score: float = 0.0
    vix_score: float = 0.0
    calendar_score: float = 0.0

    # Metadata
    instrument: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # Reasoning from Claude (if available)
    claude_reasoning: str = ""

    # Component details
    components: dict = field(default_factory=dict)

    # Warnings
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "confidence": self.confidence,
            "price_action_score": self.price_action_score,
            "news_score": self.news_score,
            "vix_score": self.vix_score,
            "calendar_score": self.calendar_score,
            "instrument": self.instrument,
            "timestamp": self.timestamp.isoformat(),
            "claude_reasoning": self.claude_reasoning,
            "warnings": self.warnings,
        }


class SentimentAggregator:
    """
    Aggregates sentiment from multiple providers.

    Default weights:
    - price_action: 0.30
    - news_claude: 0.35
    - vix: 0.15
    - calendar: 0.20
    """

    DEFAULT_WEIGHTS = {
        "price_action": 0.30,
        "news_claude": 0.35,
        "vix": 0.15,
        "calendar": 0.20,
    }

    def __init__(
        self,
        weights: Optional[dict] = None,
        enable_news: bool = True,
        enable_vix: bool = True,
        enable_calendar: bool = True
    ):
        """
        Initialize aggregator with providers.

        Args:
            weights: Custom weights for providers (optional)
            enable_news: Enable news provider
            enable_vix: Enable VIX provider
            enable_calendar: Enable calendar provider
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

        # Initialize providers
        self.providers: List[BaseSentimentProvider] = []

        if enable_news:
            try:
                self.providers.append(NewsProvider())
            except Exception as e:
                logger.warning(f"Could not initialize NewsProvider: {e}")

        if enable_vix:
            try:
                self.providers.append(VIXProvider())
            except Exception as e:
                logger.warning(f"Could not initialize VIXProvider: {e}")

        if enable_calendar:
            try:
                self.providers.append(CalendarProvider())
            except Exception as e:
                logger.warning(f"Could not initialize CalendarProvider: {e}")

        logger.info(f"SentimentAggregator initialized with {len(self.providers)} providers")

    def get_combined_sentiment(
        self,
        instrument: str,
        price_action_sentiment: Optional[float] = None
    ) -> EnhancedSentimentResult:
        """
        Get combined sentiment from all sources.

        Args:
            instrument: Currency pair
            price_action_sentiment: Existing price action sentiment (optional)

        Returns:
            EnhancedSentimentResult with combined analysis
        """
        components = {}
        warnings = []
        weighted_sum = 0.0
        total_weight = 0.0

        # Price action component (from existing analyzer)
        if price_action_sentiment is not None:
            price_weight = self.weights.get("price_action", 0.30)
            weighted_sum += price_action_sentiment * price_weight
            total_weight += price_weight
            components["price_action"] = {
                "score": price_action_sentiment,
                "weight": price_weight,
            }

        # External providers
        claude_reasoning = ""
        news_score = 0.0
        vix_score = 0.0
        calendar_score = 0.0

        for provider in self.providers:
            try:
                result = provider.get_sentiment(instrument)
                provider_name = provider.get_name()
                provider_weight = self.weights.get(provider_name, provider.get_weight())

                if result.is_error:
                    warnings.append(f"{provider_name}: {result.error_message}")
                    continue

                # Apply confidence-adjusted weighting
                adjusted_weight = provider_weight * result.confidence
                weighted_sum += result.score * adjusted_weight
                total_weight += adjusted_weight

                components[provider_name] = {
                    "score": result.score,
                    "confidence": result.confidence,
                    "weight": provider_weight,
                    "adjusted_weight": adjusted_weight,
                    "reasoning": result.reasoning,
                }

                # Store specific scores
                if provider_name == "news_claude":
                    news_score = result.score
                    claude_reasoning = result.reasoning
                elif provider_name == "vix":
                    vix_score = result.score
                elif provider_name == "calendar":
                    calendar_score = result.score

            except Exception as e:
                logger.error(f"Provider {provider.get_name()} failed: {e}")
                warnings.append(f"{provider.get_name()}: Error - {str(e)}")

        # Calculate final score
        if total_weight > 0:
            final_score = weighted_sum / total_weight
        else:
            final_score = price_action_sentiment if price_action_sentiment else 0.0
            warnings.append("No external sentiment available, using price action only")

        # Calculate overall confidence
        # Based on number of sources and their individual confidences
        num_sources = len(components)
        avg_confidence = (
            sum(c.get("confidence", 0.5) for c in components.values()) / num_sources
            if num_sources > 0 else 0.5
        )

        result = EnhancedSentimentResult(
            score=max(-1.0, min(1.0, final_score)),
            confidence=avg_confidence,
            price_action_score=price_action_sentiment or 0.0,
            news_score=news_score,
            vix_score=vix_score,
            calendar_score=calendar_score,
            instrument=instrument,
            claude_reasoning=claude_reasoning,
            components=components,
            warnings=warnings,
        )

        logger.info(
            f"Combined sentiment for {instrument}: "
            f"{result.score:+.2f} (conf: {result.confidence:.0%}) "
            f"[PA={result.price_action_score:+.2f}, "
            f"News={result.news_score:+.2f}, "
            f"VIX={result.vix_score:+.2f}, "
            f"Cal={result.calendar_score:+.2f}]"
        )

        return result

    def get_quick_sentiment(self, instrument: str) -> float:
        """
        Quick sentiment check without full analysis.

        Only uses cached values, no API calls.

        Args:
            instrument: Currency pair

        Returns:
            Sentiment score -1.0 to +1.0
        """
        # Check if we have cached VIX data (fastest)
        from src.sentiment.providers.vix_provider import VIXProvider
        vix_provider = VIXProvider()
        vix_result = vix_provider.get_sentiment(instrument)

        if not vix_result.is_error:
            return vix_result.score

        return 0.0  # Neutral if no data

    def set_weights(self, weights: dict):
        """
        Update aggregation weights.

        Args:
            weights: New weights dict
        """
        self.weights.update(weights)
        logger.info(f"Updated sentiment weights: {self.weights}")

    def get_active_providers(self) -> List[str]:
        """Get list of active provider names."""
        return [p.get_name() for p in self.providers]
