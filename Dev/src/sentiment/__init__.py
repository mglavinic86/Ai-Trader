"""
External Sentiment Integration (Phase 2 Enhancement).

Provides aggregated sentiment from multiple sources:
- News sentiment (Claude-powered analysis)
- VIX correlation (risk-on/risk-off)
- Economic calendar impact

Usage:
    from src.sentiment import SentimentAggregator

    aggregator = SentimentAggregator()
    result = aggregator.get_combined_sentiment("EUR_USD")
"""

from src.sentiment.aggregator import SentimentAggregator, EnhancedSentimentResult
from src.sentiment.base_provider import BaseSentimentProvider

__all__ = [
    "SentimentAggregator",
    "EnhancedSentimentResult",
    "BaseSentimentProvider",
]
