"""
Base Sentiment Provider Interface.

All sentiment providers must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ProviderSentiment:
    """Result from a single sentiment provider."""
    # Core sentiment
    score: float  # -1.0 (bearish) to +1.0 (bullish)
    confidence: float  # 0.0 to 1.0

    # Provider metadata
    provider: str
    instrument: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Optional details
    reasoning: str = ""
    raw_data: dict = field(default_factory=dict)

    # Error state
    is_error: bool = False
    error_message: str = ""

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "confidence": self.confidence,
            "provider": self.provider,
            "instrument": self.instrument,
            "timestamp": self.timestamp.isoformat(),
            "reasoning": self.reasoning,
            "is_error": self.is_error,
            "error_message": self.error_message,
        }


class BaseSentimentProvider(ABC):
    """
    Abstract base class for sentiment providers.

    All providers must implement:
    - get_sentiment(instrument) -> ProviderSentiment
    - get_name() -> str
    - get_weight() -> float (0.0-1.0)
    """

    @abstractmethod
    def get_sentiment(self, instrument: str) -> ProviderSentiment:
        """
        Get sentiment for an instrument.

        Args:
            instrument: Currency pair (e.g., "EUR_USD")

        Returns:
            ProviderSentiment result
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name for logging/display."""
        pass

    @abstractmethod
    def get_weight(self) -> float:
        """
        Get the weight of this provider in aggregation.

        Returns:
            Weight between 0.0 and 1.0
        """
        pass

    def is_available(self) -> bool:
        """
        Check if provider is currently available.

        Override in subclasses that need connectivity checks.
        """
        return True

    def get_cache_ttl_seconds(self) -> int:
        """
        Get cache TTL for this provider's results.

        Override for providers with different freshness requirements.
        Default: 30 minutes
        """
        return 1800

    def _create_error_result(
        self,
        instrument: str,
        error_message: str
    ) -> ProviderSentiment:
        """Helper to create error result."""
        return ProviderSentiment(
            score=0.0,
            confidence=0.0,
            provider=self.get_name(),
            instrument=instrument,
            is_error=True,
            error_message=error_message
        )
