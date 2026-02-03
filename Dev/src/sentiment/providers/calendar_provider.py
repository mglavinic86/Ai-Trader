"""
Economic Calendar Sentiment Provider.

Provides sentiment based on economic event outcomes.
- Beat expectations: Bullish for currency
- Miss expectations: Bearish for currency
- High-impact upcoming: Reduce confidence

Integrates with existing news_filter.py for event data.
"""

from datetime import datetime, timedelta
from typing import Optional

from src.sentiment.base_provider import BaseSentimentProvider, ProviderSentiment
from src.utils.logger import logger


# Cache for calendar sentiment
_calendar_cache: dict = {}
_cache_ttl = 600  # 10 minutes


# Impact mapping for economic events
EVENT_IMPACT = {
    # Central bank decisions
    "interest_rate": 1.0,
    "rate_decision": 1.0,
    "monetary_policy": 0.9,
    "fed": 0.95,
    "ecb": 0.95,
    "boe": 0.9,
    "boj": 0.85,

    # Employment
    "nfp": 0.95,
    "non-farm": 0.95,
    "employment": 0.8,
    "unemployment": 0.8,
    "jobs": 0.7,

    # Inflation
    "cpi": 0.9,
    "inflation": 0.85,
    "ppi": 0.7,

    # GDP and growth
    "gdp": 0.85,
    "growth": 0.75,

    # Trade
    "trade_balance": 0.6,
    "current_account": 0.6,

    # PMI and surveys
    "pmi": 0.7,
    "ism": 0.75,
    "confidence": 0.6,
    "sentiment": 0.5,
}

# Currency to country mapping
CURRENCY_COUNTRY = {
    "USD": ["US", "United States", "Fed"],
    "EUR": ["EU", "Eurozone", "ECB", "Germany", "France"],
    "GBP": ["UK", "Britain", "BOE"],
    "JPY": ["Japan", "BOJ"],
    "AUD": ["Australia", "RBA"],
    "NZD": ["New Zealand", "RBNZ"],
    "CAD": ["Canada", "BOC"],
    "CHF": ["Switzerland", "SNB"],
}


class CalendarProvider(BaseSentimentProvider):
    """
    Economic calendar sentiment provider.

    Analyzes recent economic releases and upcoming events
    to determine currency sentiment.
    """

    def __init__(self):
        self._weight = 0.20
        self._news_filter = None

    def get_name(self) -> str:
        return "calendar"

    def get_weight(self) -> float:
        return self._weight

    def get_cache_ttl_seconds(self) -> int:
        return _cache_ttl

    def _get_news_filter(self):
        """Lazy load news filter."""
        if self._news_filter is None:
            try:
                from src.analysis.news_filter import news_filter
                self._news_filter = news_filter
            except Exception as e:
                logger.warning(f"Could not load news_filter: {e}")
        return self._news_filter

    def get_sentiment(self, instrument: str) -> ProviderSentiment:
        """
        Get calendar-based sentiment for an instrument.

        Analyzes recent releases and upcoming events.

        Args:
            instrument: Currency pair

        Returns:
            ProviderSentiment based on economic calendar
        """
        # Check cache
        cache_key = f"calendar_{instrument}"
        if cache_key in _calendar_cache:
            cached, timestamp = _calendar_cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=_cache_ttl):
                return cached

        try:
            base, quote = self._get_currencies(instrument)

            # Get sentiment for both currencies
            base_sentiment, base_conf, base_reason = self._get_currency_sentiment(base)
            quote_sentiment, quote_conf, quote_reason = self._get_currency_sentiment(quote)

            # Net sentiment: if base is bullish and quote bearish = more bullish
            net_sentiment = base_sentiment - quote_sentiment
            net_confidence = (base_conf + quote_conf) / 2

            # Reduce confidence if high-impact event upcoming
            upcoming_impact = self._check_upcoming_events(base, quote)
            if upcoming_impact > 0.5:
                net_confidence *= 0.7  # Reduce confidence before big events
                upcoming_reason = "High-impact event upcoming"
            else:
                upcoming_reason = ""

            reasoning = f"Base({base}): {base_reason}. Quote({quote}): {quote_reason}"
            if upcoming_reason:
                reasoning += f". {upcoming_reason}"

            result = ProviderSentiment(
                score=max(-1.0, min(1.0, net_sentiment)),
                confidence=net_confidence,
                provider=self.get_name(),
                instrument=instrument,
                reasoning=reasoning,
                raw_data={
                    "base_sentiment": base_sentiment,
                    "quote_sentiment": quote_sentiment,
                    "base_confidence": base_conf,
                    "quote_confidence": quote_conf,
                    "upcoming_impact": upcoming_impact,
                }
            )

            # Cache result
            _calendar_cache[cache_key] = (result, datetime.now())
            return result

        except Exception as e:
            logger.error(f"Calendar provider error: {e}")
            return self._create_error_result(instrument, str(e))

    def _get_currencies(self, instrument: str) -> tuple[str, str]:
        """Extract currency codes from instrument."""
        if "_" in instrument:
            parts = instrument.split("_")
            return (parts[0], parts[1])
        else:
            return (instrument[:3], instrument[3:])

    def _get_currency_sentiment(self, currency: str) -> tuple[float, float, str]:
        """
        Get sentiment for a single currency based on recent events.

        Args:
            currency: Currency code (e.g., "USD")

        Returns:
            (sentiment, confidence, reason)
        """
        # Placeholder implementation
        # In production would:
        # 1. Fetch recent events for this currency
        # 2. Check actual vs forecast
        # 3. Calculate sentiment based on surprises

        # For now, return neutral
        # TODO: Integrate with ForexFactory scraper or paid API
        return 0.0, 0.3, "No recent events"

    def _check_upcoming_events(self, base: str, quote: str) -> float:
        """
        Check for upcoming high-impact events.

        Args:
            base: Base currency
            quote: Quote currency

        Returns:
            Impact score 0.0 to 1.0
        """
        nf = self._get_news_filter()
        if nf is None:
            return 0.0

        try:
            # Check if news filter indicates avoidance
            instrument = f"{base}_{quote}"
            should_avoid, reason = nf.should_avoid_trade(instrument)

            if should_avoid:
                return 0.8  # High impact upcoming
            return 0.0

        except Exception as e:
            logger.warning(f"Error checking upcoming events: {e}")
            return 0.0

    def analyze_release_impact(
        self,
        currency: str,
        event_type: str,
        actual: float,
        forecast: float,
        previous: float
    ) -> tuple[float, float, str]:
        """
        Analyze the impact of an economic release.

        Args:
            currency: Currency affected
            event_type: Type of event (e.g., "CPI", "NFP")
            actual: Actual released value
            forecast: Market forecast
            previous: Previous value

        Returns:
            (sentiment, impact, reasoning)
        """
        # Calculate surprise
        if forecast != 0:
            surprise_pct = (actual - forecast) / abs(forecast) * 100
        else:
            surprise_pct = 0

        # Get event weight
        event_lower = event_type.lower()
        impact = 0.5  # Default impact
        for key, weight in EVENT_IMPACT.items():
            if key in event_lower:
                impact = weight
                break

        # Calculate sentiment
        # Positive surprise = bullish, negative = bearish
        if surprise_pct > 0:
            sentiment = min(1.0, surprise_pct / 10 * impact)
            reasoning = f"{event_type} beat by {surprise_pct:.1f}% - bullish {currency}"
        elif surprise_pct < 0:
            sentiment = max(-1.0, surprise_pct / 10 * impact)
            reasoning = f"{event_type} missed by {abs(surprise_pct):.1f}% - bearish {currency}"
        else:
            sentiment = 0.0
            reasoning = f"{event_type} in-line with expectations"

        return sentiment, impact, reasoning


def clear_calendar_cache():
    """Clear the calendar cache."""
    global _calendar_cache
    _calendar_cache = {}
    logger.info("Calendar cache cleared")
