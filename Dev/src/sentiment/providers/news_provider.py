"""
News Sentiment Provider - Claude-Powered News Analysis.

Uses Claude to analyze forex news headlines and extract sentiment.
Caches results for 30 minutes.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

from src.sentiment.base_provider import BaseSentimentProvider, ProviderSentiment
from src.utils.logger import logger


# Cache for news sentiment
_news_cache: dict = {}
_cache_ttl = 1800  # 30 minutes


@dataclass
class NewsAnalysis:
    """Structured result from Claude news analysis."""
    sentiment_score: float
    confidence: float
    reasoning: str
    key_events: list = field(default_factory=list)
    priced_in: bool = False
    impact_timeframe: str = "short_term"
    related_pairs: list = field(default_factory=list)
    risk_events_ahead: list = field(default_factory=list)


NEWS_ANALYSIS_PROMPT = """Analyze these forex news headlines for {instrument}:

{headlines}

Provide analysis in JSON format (no markdown, just raw JSON):
{{
  "sentiment_score": <float from -1.0 bearish to +1.0 bullish>,
  "confidence": <float from 0.0 to 1.0>,
  "reasoning": "<brief explanation of sentiment>",
  "key_events": ["<event 1>", "<event 2>"],
  "priced_in": <boolean - is this news already reflected in price?>,
  "impact_timeframe": "<immediate|short_term|medium_term>",
  "related_pairs": ["<other affected pairs>"],
  "risk_events_ahead": ["<upcoming events that could reverse sentiment>"]
}}

Consider:
- Central bank rhetoric (hawkish/dovish)
- Economic data surprises (beat/miss expectations)
- Geopolitical events
- Market positioning (crowded trades)
- Time since headline (fresh vs stale news)
"""


class NewsProvider(BaseSentimentProvider):
    """
    News sentiment provider using Claude for analysis.

    Fetches news headlines and uses Claude to analyze sentiment.
    Caches results for 30 minutes.
    """

    def __init__(self, llm_engine=None):
        """
        Initialize news provider.

        Args:
            llm_engine: Optional LLM engine for analysis.
                       If not provided, will try to import from src.analysis.llm_engine
        """
        self._llm_engine = llm_engine
        self._weight = 0.35  # Highest weight among external sources

    def get_name(self) -> str:
        return "news_claude"

    def get_weight(self) -> float:
        return self._weight

    def get_cache_ttl_seconds(self) -> int:
        return _cache_ttl

    def _get_llm_engine(self):
        """Lazy load LLM engine."""
        if self._llm_engine is None:
            try:
                from src.analysis.llm_engine import LLMEngine
                self._llm_engine = LLMEngine()
            except Exception as e:
                logger.error(f"Failed to load LLM engine: {e}")
                return None
        return self._llm_engine

    def get_sentiment(self, instrument: str) -> ProviderSentiment:
        """
        Get news-based sentiment for an instrument.

        Args:
            instrument: Currency pair (e.g., "EUR_USD")

        Returns:
            ProviderSentiment with Claude analysis
        """
        # Check cache first
        cache_key = f"news_{instrument}"
        if cache_key in _news_cache:
            cached, timestamp = _news_cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=_cache_ttl):
                logger.debug(f"News cache hit for {instrument}")
                return cached

        try:
            # Fetch headlines
            headlines = self._fetch_headlines(instrument)

            if not headlines:
                return self._create_error_result(
                    instrument,
                    "No headlines available"
                )

            # Analyze with Claude
            analysis = self._analyze_with_claude(instrument, headlines)

            if analysis is None:
                return self._create_error_result(
                    instrument,
                    "Claude analysis failed"
                )

            result = ProviderSentiment(
                score=analysis.sentiment_score,
                confidence=analysis.confidence,
                provider=self.get_name(),
                instrument=instrument,
                reasoning=analysis.reasoning,
                raw_data={
                    "key_events": analysis.key_events,
                    "priced_in": analysis.priced_in,
                    "impact_timeframe": analysis.impact_timeframe,
                    "related_pairs": analysis.related_pairs,
                    "risk_events_ahead": analysis.risk_events_ahead,
                }
            )

            # Cache result
            _news_cache[cache_key] = (result, datetime.now())
            logger.info(
                f"News sentiment for {instrument}: "
                f"{analysis.sentiment_score:+.2f} (conf: {analysis.confidence:.0%})"
            )

            return result

        except Exception as e:
            logger.error(f"News provider error for {instrument}: {e}")
            return self._create_error_result(instrument, str(e))

    def _fetch_headlines(self, instrument: str) -> list[str]:
        """
        Fetch news headlines for instrument.

        Currently returns placeholder - in production would fetch from:
        - NewsAPI.org
        - Finviz
        - ForexFactory
        - Reuters/Bloomberg RSS

        Args:
            instrument: Currency pair

        Returns:
            List of headline strings
        """
        # Map instrument to currencies
        currencies = self._get_currencies(instrument)

        # Placeholder headlines for development
        # In production, would fetch from actual news APIs
        placeholder_headlines = [
            f"Market awaits key economic data for {currencies[0]}",
            f"{currencies[1]} steadies after recent volatility",
            "Central bank officials signal cautious approach",
        ]

        # TODO: Implement actual news fetching
        # from newsapi import NewsApiClient
        # newsapi = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))
        # articles = newsapi.get_everything(q=f'{currencies[0]} {currencies[1]} forex')

        return placeholder_headlines

    def _get_currencies(self, instrument: str) -> tuple[str, str]:
        """Extract currency codes from instrument."""
        # Handle both EUR_USD and EURUSD formats
        if "_" in instrument:
            parts = instrument.split("_")
            return (parts[0], parts[1])
        else:
            return (instrument[:3], instrument[3:])

    def _analyze_with_claude(
        self,
        instrument: str,
        headlines: list[str]
    ) -> Optional[NewsAnalysis]:
        """
        Analyze headlines using Claude.

        Args:
            instrument: Currency pair
            headlines: List of news headlines

        Returns:
            NewsAnalysis or None if failed
        """
        llm = self._get_llm_engine()
        if llm is None:
            return None

        try:
            prompt = NEWS_ANALYSIS_PROMPT.format(
                instrument=instrument,
                headlines="\n".join(f"- {h}" for h in headlines)
            )

            # Use the LLM engine to analyze
            response = llm.simple_analyze(prompt, max_tokens=500)

            if not response:
                return None

            # Parse JSON response
            # Try to extract JSON from response
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str)

            return NewsAnalysis(
                sentiment_score=float(data.get("sentiment_score", 0)),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                key_events=data.get("key_events", []),
                priced_in=data.get("priced_in", False),
                impact_timeframe=data.get("impact_timeframe", "short_term"),
                related_pairs=data.get("related_pairs", []),
                risk_events_ahead=data.get("risk_events_ahead", []),
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Claude response: {e}")
            return None
        except Exception as e:
            logger.error(f"Claude analysis error: {e}")
            return None


def clear_news_cache():
    """Clear the news cache."""
    global _news_cache
    _news_cache = {}
    logger.info("News cache cleared")
