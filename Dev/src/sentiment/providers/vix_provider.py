"""
VIX Correlation Provider.

Uses VIX (volatility index) to determine market risk sentiment.
- VIX > 30: Risk-off (avoid long risk currencies)
- VIX < 15: Risk-on (favor carry trades)
- VIX spike: Avoid trading
"""

from datetime import datetime, timedelta
from typing import Optional

from src.sentiment.base_provider import BaseSentimentProvider, ProviderSentiment
from src.utils.logger import logger


# Cache for VIX data
_vix_cache: dict = {}
_cache_ttl = 300  # 5 minutes - VIX updates frequently


# Currency risk classification
# Risk currencies: AUD, NZD, CAD (commodity/carry)
# Safe havens: USD, JPY, CHF
RISK_CURRENCIES = {"AUD", "NZD", "CAD", "GBP"}
SAFE_HAVEN_CURRENCIES = {"USD", "JPY", "CHF"}


class VIXProvider(BaseSentimentProvider):
    """
    VIX-based sentiment provider.

    Determines risk-on/risk-off sentiment based on VIX levels.
    """

    def __init__(self):
        self._weight = 0.15
        self._last_vix = None
        self._last_vix_time = None

    def get_name(self) -> str:
        return "vix"

    def get_weight(self) -> float:
        return self._weight

    def get_cache_ttl_seconds(self) -> int:
        return _cache_ttl

    def get_sentiment(self, instrument: str) -> ProviderSentiment:
        """
        Get VIX-based sentiment for an instrument.

        High VIX = risk-off = bearish for risk currencies
        Low VIX = risk-on = bullish for risk currencies

        Args:
            instrument: Currency pair

        Returns:
            ProviderSentiment based on VIX correlation
        """
        try:
            vix = self._get_vix()

            if vix is None:
                return self._create_error_result(instrument, "VIX data unavailable")

            # Determine currency types
            base, quote = self._get_currencies(instrument)
            is_risk_currency = base in RISK_CURRENCIES or quote in RISK_CURRENCIES
            is_safe_haven = base in SAFE_HAVEN_CURRENCIES or quote in SAFE_HAVEN_CURRENCIES

            # Calculate sentiment based on VIX
            sentiment_score, confidence, reasoning = self._calculate_vix_sentiment(
                vix, base, quote, is_risk_currency, is_safe_haven
            )

            return ProviderSentiment(
                score=sentiment_score,
                confidence=confidence,
                provider=self.get_name(),
                instrument=instrument,
                reasoning=reasoning,
                raw_data={
                    "vix": vix,
                    "is_risk_currency": is_risk_currency,
                    "is_safe_haven": is_safe_haven,
                }
            )

        except Exception as e:
            logger.error(f"VIX provider error: {e}")
            return self._create_error_result(instrument, str(e))

    def _get_vix(self) -> Optional[float]:
        """
        Get current VIX value.

        In production would fetch from:
        - Yahoo Finance API
        - Alpha Vantage
        - CBOE

        Returns:
            VIX value or None
        """
        # Check cache
        if self._last_vix and self._last_vix_time:
            if datetime.now() - self._last_vix_time < timedelta(seconds=_cache_ttl):
                return self._last_vix

        try:
            # Placeholder - in production would fetch real VIX
            # import yfinance as yf
            # vix = yf.Ticker("^VIX")
            # data = vix.history(period="1d")
            # current_vix = data['Close'].iloc[-1]

            # For development, use a default value
            # TODO: Implement actual VIX fetching
            current_vix = 18.5  # Moderate volatility placeholder

            self._last_vix = current_vix
            self._last_vix_time = datetime.now()

            return current_vix

        except Exception as e:
            logger.warning(f"Failed to fetch VIX: {e}")
            return self._last_vix  # Return last known value

    def _get_currencies(self, instrument: str) -> tuple[str, str]:
        """Extract currency codes from instrument."""
        if "_" in instrument:
            parts = instrument.split("_")
            return (parts[0], parts[1])
        else:
            return (instrument[:3], instrument[3:])

    def _calculate_vix_sentiment(
        self,
        vix: float,
        base: str,
        quote: str,
        is_risk: bool,
        is_safe: bool
    ) -> tuple[float, float, str]:
        """
        Calculate sentiment based on VIX level and currency type.

        VIX Levels:
        - < 15: Low volatility, risk-on
        - 15-20: Normal
        - 20-30: Elevated, cautious
        - > 30: High volatility, risk-off

        Args:
            vix: Current VIX value
            base: Base currency
            quote: Quote currency
            is_risk: Is this a risk currency pair
            is_safe: Is this a safe haven pair

        Returns:
            (sentiment_score, confidence, reasoning)
        """
        # Neutral for non-classified pairs
        if not is_risk and not is_safe:
            return 0.0, 0.3, f"VIX at {vix:.1f} - neutral for {base}/{quote}"

        # Determine sentiment direction
        base_in_risk = base in RISK_CURRENCIES
        quote_in_risk = quote in RISK_CURRENCIES
        base_in_safe = base in SAFE_HAVEN_CURRENCIES
        quote_in_safe = quote in SAFE_HAVEN_CURRENCIES

        # Risk-on scenario (low VIX)
        if vix < 15:
            if base_in_risk and quote_in_safe:
                return 0.6, 0.7, f"VIX low ({vix:.1f}) - risk-on favors {base}"
            elif base_in_safe and quote_in_risk:
                return -0.6, 0.7, f"VIX low ({vix:.1f}) - risk-on favors {quote}"
            else:
                return 0.3, 0.5, f"VIX low ({vix:.1f}) - mild risk-on"

        # Normal volatility
        elif vix < 20:
            return 0.0, 0.4, f"VIX normal ({vix:.1f}) - neutral"

        # Elevated volatility
        elif vix < 30:
            if base_in_safe and quote_in_risk:
                return 0.4, 0.6, f"VIX elevated ({vix:.1f}) - cautious, favors {base}"
            elif base_in_risk and quote_in_safe:
                return -0.4, 0.6, f"VIX elevated ({vix:.1f}) - cautious, {quote} preferred"
            else:
                return -0.2, 0.5, f"VIX elevated ({vix:.1f}) - risk caution"

        # High volatility (VIX > 30)
        else:
            if base_in_safe and quote_in_risk:
                return 0.7, 0.8, f"VIX high ({vix:.1f}) - risk-off, strong {base}"
            elif base_in_risk and quote_in_safe:
                return -0.7, 0.8, f"VIX high ({vix:.1f}) - risk-off, {quote} safe haven"
            else:
                return -0.5, 0.7, f"VIX high ({vix:.1f}) - avoid risk trades"

    def detect_vix_spike(self) -> tuple[bool, float]:
        """
        Detect if VIX has spiked (sudden increase).

        Useful for avoiding trading during market stress.

        Returns:
            (is_spike, spike_magnitude)
        """
        # Would need historical VIX data to detect spikes
        # For now, just check if VIX is above panic level
        vix = self._get_vix()
        if vix and vix > 35:
            return True, vix - 20  # Spike magnitude
        return False, 0.0
