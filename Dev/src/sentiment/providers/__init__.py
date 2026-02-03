"""
Sentiment Providers.

Available providers:
- NewsProvider: Claude-powered news analysis
- VIXProvider: VIX correlation for risk sentiment
- CalendarProvider: Economic calendar impact
"""

from src.sentiment.providers.news_provider import NewsProvider
from src.sentiment.providers.vix_provider import VIXProvider
from src.sentiment.providers.calendar_provider import CalendarProvider

__all__ = [
    "NewsProvider",
    "VIXProvider",
    "CalendarProvider",
]
