"""
News Providers - Fetch economic calendar data from multiple sources.

Supported providers:
1. Finnhub (free API, 60 calls/min)
2. Forex Factory (scraping, no API key needed)
3. Investing.com (via open-source scraper)

Usage:
    from src.analysis.news_providers import NewsProviderManager

    manager = NewsProviderManager()
    events = await manager.fetch_events()
"""

import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from src.utils.logger import logger


_dev_dir = Path(__file__).parent.parent.parent
_settings_dir = _dev_dir / "settings"
_calendar_path = _settings_dir / "news_calendar.json"
_config_path = _settings_dir / "news_providers.json"


class NewsProvider(ABC):
    """Base class for news providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def fetch_events(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Fetch economic events."""
        pass


class FinnhubProvider(NewsProvider):
    """
    Finnhub Economic Calendar API.

    Free tier: 60 API calls/minute
    Docs: https://finnhub.io/docs/api/economic-calendar
    """

    name = "finnhub"
    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def fetch_events(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Fetch economic calendar from Finnhub."""
        if not self.api_key:
            logger.warning("Finnhub API key not configured")
            return []

        now = datetime.now(timezone.utc)
        from_date = now.strftime("%Y-%m-%d")
        to_date = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        url = f"{self.BASE_URL}/calendar/economic"
        params = {
            "from": from_date,
            "to": to_date,
            "token": self.api_key
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status != 200:
                        logger.error(f"Finnhub API error: {resp.status}")
                        return []

                    data = await resp.json()
                    events = []

                    for item in data.get("economicCalendar", []):
                        # Map Finnhub impact to our format
                        impact = self._map_impact(item.get("impact", 0))

                        # Extract currency from country
                        currency = self._country_to_currency(item.get("country", ""))

                        if currency:  # Only include forex-relevant events
                            events.append({
                                "time": item.get("time", ""),
                                "currency": currency,
                                "name": item.get("event", "Unknown"),
                                "impact": impact,
                                "actual": item.get("actual"),
                                "forecast": item.get("estimate"),
                                "previous": item.get("prev"),
                                "source": "finnhub"
                            })

                    logger.info(f"Finnhub: fetched {len(events)} events")
                    return events

        except asyncio.TimeoutError:
            logger.error("Finnhub API timeout")
            return []
        except Exception as e:
            logger.error(f"Finnhub API error: {e}")
            return []

    def _map_impact(self, impact_num: int) -> str:
        """Map Finnhub impact number to HIGH/MEDIUM/LOW."""
        if impact_num >= 3:
            return "HIGH"
        elif impact_num >= 2:
            return "MEDIUM"
        return "LOW"

    def _country_to_currency(self, country: str) -> Optional[str]:
        """Map country to forex currency code."""
        mapping = {
            "US": "USD",
            "EU": "EUR",
            "GB": "GBP",
            "JP": "JPY",
            "AU": "AUD",
            "NZ": "NZD",
            "CA": "CAD",
            "CH": "CHF",
            "CN": "CNY",
            "DE": "EUR",
            "FR": "EUR",
            "IT": "EUR",
            "ES": "EUR",
        }
        return mapping.get(country.upper())


class ForexFactoryProvider(NewsProvider):
    """
    Forex Factory Calendar via JBlanked API.

    Free API with rate limit of 1 request/second.
    Docs: https://www.jblanked.com/news/api/docs/calendar/
    """

    name = "forexfactory"
    # JBlanked API - free access to FF data
    WEEK_URL = "https://www.jblanked.com/news/api/forex-factory/calendar/week/"
    RANGE_URL = "https://www.jblanked.com/news/api/forex-factory/calendar/range/"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key  # Optional for authenticated requests

    async def fetch_events(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Fetch calendar from Forex Factory via JBlanked API."""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Api-Key {self.api_key}"

            async with aiohttp.ClientSession() as session:
                # Try weekly endpoint first (no auth required)
                async with session.get(
                    self.WEEK_URL,
                    headers=headers,
                    timeout=15
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"JBlanked API status: {resp.status}")
                        # Try alternate endpoint
                        return await self._fetch_alternate()

                    data = await resp.json()
                    events = []
                    now = datetime.now(timezone.utc)
                    cutoff = now + timedelta(days=days_ahead)

                    # Handle both list and dict response formats
                    event_list = data if isinstance(data, list) else data.get("data", data.get("events", []))

                    for item in event_list:
                        try:
                            # Parse datetime - JBlanked format
                            date_str = item.get("date", "") or item.get("datetime", "")
                            if not date_str:
                                continue

                            # Try various datetime formats
                            event_time = None
                            for fmt in [
                                "%Y-%m-%dT%H:%M:%S",
                                "%Y-%m-%d %H:%M:%S",
                                "%Y-%m-%d %I:%M%p",
                                "%Y-%m-%d"
                            ]:
                                try:
                                    event_time = datetime.strptime(date_str[:len(fmt)+5], fmt)
                                    break
                                except ValueError:
                                    continue

                            if not event_time:
                                continue

                            event_time = event_time.replace(tzinfo=timezone.utc)

                            # Filter by date range
                            if event_time < now or event_time > cutoff:
                                continue

                            # Map impact
                            impact_raw = str(item.get("impact", "")).upper()
                            if "HIGH" in impact_raw or impact_raw == "3":
                                impact = "HIGH"
                            elif "MEDIUM" in impact_raw or "MED" in impact_raw or impact_raw == "2":
                                impact = "MEDIUM"
                            else:
                                impact = "LOW"

                            # Get currency
                            currency = (
                                item.get("currency", "") or
                                item.get("country", "") or
                                ""
                            ).upper()

                            if not currency:
                                continue

                            events.append({
                                "time": event_time.isoformat(),
                                "currency": currency,
                                "name": item.get("title", item.get("event", item.get("name", "Unknown"))),
                                "impact": impact,
                                "actual": item.get("actual"),
                                "forecast": item.get("forecast"),
                                "previous": item.get("previous"),
                                "source": "forexfactory"
                            })

                        except Exception as e:
                            logger.debug(f"Failed to parse FF event: {e}")
                            continue

                    logger.info(f"ForexFactory: fetched {len(events)} events")
                    return events

        except asyncio.TimeoutError:
            logger.error("ForexFactory fetch timeout")
            return await self._fetch_alternate()
        except Exception as e:
            logger.error(f"ForexFactory fetch error: {e}")
            return await self._fetch_alternate()

    async def _fetch_alternate(self) -> List[Dict[str, Any]]:
        """Try alternate free endpoints."""
        alternate_urls = [
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
        ]

        for url in alternate_urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status != 200:
                            continue

                        data = await resp.json()
                        events = []
                        now = datetime.now(timezone.utc)

                        for item in data:
                            try:
                                date_str = item.get("date", "")
                                time_str = item.get("time", "")
                                if not date_str:
                                    continue

                                if time_str and time_str not in ["All Day", "Tentative"]:
                                    dt_str = f"{date_str} {time_str}"
                                    try:
                                        event_time = datetime.strptime(dt_str, "%Y-%m-%d %I:%M%p")
                                    except ValueError:
                                        event_time = datetime.strptime(date_str, "%Y-%m-%d")
                                else:
                                    event_time = datetime.strptime(date_str, "%Y-%m-%d")

                                event_time = event_time.replace(tzinfo=timezone.utc)

                                if event_time < now:
                                    continue

                                impact = item.get("impact", "Low")
                                if impact in ["High", "high"]:
                                    impact = "HIGH"
                                elif impact in ["Medium", "medium"]:
                                    impact = "MEDIUM"
                                else:
                                    impact = "LOW"

                                events.append({
                                    "time": event_time.isoformat(),
                                    "currency": item.get("country", "").upper(),
                                    "name": item.get("title", "Unknown"),
                                    "impact": impact,
                                    "actual": item.get("actual"),
                                    "forecast": item.get("forecast"),
                                    "previous": item.get("previous"),
                                    "source": "forexfactory_alt"
                                })

                            except Exception:
                                continue

                        if events:
                            logger.info(f"ForexFactory (alt): fetched {len(events)} events")
                            return events

            except Exception:
                continue

        return []


class FMPProvider(NewsProvider):
    """
    Financial Modeling Prep Economic Calendar.

    Free tier: 250 API calls/day
    Get API key: https://site.financialmodelingprep.com/developer
    """

    name = "fmp"
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def fetch_events(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Fetch economic calendar from FMP."""
        if not self.api_key:
            logger.warning("FMP API key not configured")
            return []

        now = datetime.now(timezone.utc)
        from_date = now.strftime("%Y-%m-%d")
        to_date = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        url = f"{self.BASE_URL}/economic_calendar"
        params = {
            "from": from_date,
            "to": to_date,
            "apikey": self.api_key
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as resp:
                    if resp.status == 401:
                        logger.error("FMP API: Invalid or missing API key")
                        return []
                    if resp.status != 200:
                        logger.error(f"FMP API error: {resp.status}")
                        return []

                    data = await resp.json()
                    events = []

                    for item in data:
                        try:
                            # Parse datetime
                            date_str = item.get("date", "")
                            if not date_str:
                                continue

                            event_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

                            # Map impact based on event type
                            event_name = item.get("event", "").lower()
                            impact = self._determine_impact(event_name, item.get("country", ""))

                            # Get currency from country
                            currency = self._country_to_currency(item.get("country", ""))
                            if not currency:
                                continue

                            events.append({
                                "time": event_time.isoformat(),
                                "currency": currency,
                                "name": item.get("event", "Unknown"),
                                "impact": impact,
                                "actual": item.get("actual"),
                                "forecast": item.get("estimate"),
                                "previous": item.get("previous"),
                                "source": "fmp"
                            })

                        except Exception as e:
                            logger.debug(f"Failed to parse FMP event: {e}")
                            continue

                    logger.info(f"FMP: fetched {len(events)} events")
                    return events

        except Exception as e:
            logger.error(f"FMP API error: {e}")
            return []

    def _determine_impact(self, event_name: str, country: str) -> str:
        """Determine impact level from event name."""
        high_impact_keywords = [
            "nonfarm", "non-farm", "payroll", "fomc", "fed", "interest rate",
            "gdp", "cpi", "inflation", "unemployment", "ecb", "boe", "boj",
            "retail sales", "pmi", "manufacturing"
        ]
        medium_impact_keywords = [
            "trade balance", "housing", "employment", "claims", "consumer",
            "industrial", "durable", "confidence"
        ]

        event_lower = event_name.lower()
        for keyword in high_impact_keywords:
            if keyword in event_lower:
                return "HIGH"
        for keyword in medium_impact_keywords:
            if keyword in event_lower:
                return "MEDIUM"
        return "LOW"

    def _country_to_currency(self, country: str) -> Optional[str]:
        """Map country to forex currency code."""
        mapping = {
            "US": "USD", "United States": "USD",
            "EU": "EUR", "Euro Area": "EUR", "Germany": "EUR", "France": "EUR",
            "GB": "GBP", "United Kingdom": "GBP", "UK": "GBP",
            "JP": "JPY", "Japan": "JPY",
            "AU": "AUD", "Australia": "AUD",
            "NZ": "NZD", "New Zealand": "NZD",
            "CA": "CAD", "Canada": "CAD",
            "CH": "CHF", "Switzerland": "CHF",
        }
        return mapping.get(country)


class RecurringEventsProvider(NewsProvider):
    """
    Static provider for known recurring high-impact events.

    No API key needed. Generates events based on known schedules.
    Useful as fallback when API providers are unavailable.
    """

    name = "recurring"

    # Known high-impact recurring events
    RECURRING_EVENTS = [
        # US Events
        {"name": "Non-Farm Payrolls", "currency": "USD", "impact": "HIGH",
         "schedule": "first_friday", "time": "13:30"},
        {"name": "FOMC Interest Rate Decision", "currency": "USD", "impact": "HIGH",
         "schedule": "fomc"},
        {"name": "US CPI", "currency": "USD", "impact": "HIGH",
         "schedule": "monthly_mid", "time": "13:30"},
        {"name": "US Retail Sales", "currency": "USD", "impact": "HIGH",
         "schedule": "monthly_mid", "time": "13:30"},

        # EUR Events
        {"name": "ECB Interest Rate Decision", "currency": "EUR", "impact": "HIGH",
         "schedule": "ecb"},
        {"name": "German ZEW Economic Sentiment", "currency": "EUR", "impact": "MEDIUM",
         "schedule": "monthly_mid", "time": "10:00"},

        # GBP Events
        {"name": "BoE Interest Rate Decision", "currency": "GBP", "impact": "HIGH",
         "schedule": "boe"},
        {"name": "UK CPI", "currency": "GBP", "impact": "HIGH",
         "schedule": "monthly_mid", "time": "07:00"},

        # JPY Events
        {"name": "BoJ Interest Rate Decision", "currency": "JPY", "impact": "HIGH",
         "schedule": "boj"},
    ]

    async def fetch_events(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Generate events based on known schedules."""
        events = []
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=days_ahead)

        for event_template in self.RECURRING_EVENTS:
            try:
                # Generate next occurrence based on schedule
                next_dates = self._get_next_occurrences(
                    event_template["schedule"],
                    event_template.get("time", "12:00"),
                    now,
                    end_date
                )

                for event_time in next_dates:
                    events.append({
                        "time": event_time.isoformat(),
                        "currency": event_template["currency"],
                        "name": event_template["name"],
                        "impact": event_template["impact"],
                        "actual": None,
                        "forecast": None,
                        "previous": None,
                        "source": "recurring"
                    })

            except Exception as e:
                logger.debug(f"Failed to generate recurring event: {e}")
                continue

        logger.info(f"Recurring: generated {len(events)} events")
        return events

    def _get_next_occurrences(
        self,
        schedule: str,
        time_str: str,
        start: datetime,
        end: datetime
    ) -> List[datetime]:
        """Get next occurrence dates based on schedule type."""
        occurrences = []
        hour, minute = map(int, time_str.split(":"))

        if schedule == "first_friday":
            # First Friday of each month
            current = start.replace(day=1, hour=hour, minute=minute, second=0, microsecond=0)
            while current <= end:
                # Find first Friday
                while current.weekday() != 4:  # Friday
                    current += timedelta(days=1)
                if start <= current <= end:
                    occurrences.append(current)
                # Move to next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1, day=1)
                else:
                    current = current.replace(month=current.month + 1, day=1)

        elif schedule == "monthly_mid":
            # Around 10th-15th of each month
            current = start.replace(day=12, hour=hour, minute=minute, second=0, microsecond=0)
            while current <= end:
                if start <= current <= end:
                    occurrences.append(current)
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

        elif schedule in ["fomc", "ecb", "boe", "boj"]:
            # Central bank meetings - approximately every 6 weeks
            # This is simplified; real schedule should be looked up
            current = start.replace(hour=hour, minute=minute, second=0, microsecond=0)
            while current <= end:
                if start <= current <= end:
                    occurrences.append(current)
                current += timedelta(days=42)  # ~6 weeks

        return occurrences


class MQL5Provider(NewsProvider):
    """
    MQL5 Economic Calendar.

    Free, no API key required.
    Source: https://www.mql5.com/en/economic-calendar
    """

    name = "mql5"
    # MQL5 provides calendar data via their widget endpoint
    API_URL = "https://www.mql5.com/en/economic-calendar/content"

    async def fetch_events(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Fetch from MQL5 economic calendar."""
        try:
            now = datetime.now(timezone.utc)
            from_date = now.strftime("%Y-%m-%d")
            to_date = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

            # MQL5 calendar endpoint
            url = f"{self.API_URL}"
            params = {
                "date_from": from_date,
                "date_to": to_date,
                "importance": "2,3",  # Medium and High importance
                "currencies": "USD,EUR,GBP,JPY,AUD,NZD,CAD,CHF"
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=15) as resp:
                    if resp.status != 200:
                        logger.warning(f"MQL5 API status: {resp.status}")
                        return []

                    # MQL5 returns HTML, try to parse JSON from response
                    text = await resp.text()

                    # Try to find JSON in response
                    import re
                    json_match = re.search(r'\[.*\]', text, re.DOTALL)
                    if not json_match:
                        logger.warning("MQL5: No JSON data in response")
                        return []

                    data = json.loads(json_match.group())
                    events = []

                    for item in data:
                        try:
                            # Parse MQL5 format
                            event_time = datetime.fromtimestamp(
                                item.get("release_date", 0),
                                tz=timezone.utc
                            )

                            if event_time < now:
                                continue

                            # Map importance
                            importance = item.get("importance", 1)
                            if importance >= 3:
                                impact = "HIGH"
                            elif importance >= 2:
                                impact = "MEDIUM"
                            else:
                                impact = "LOW"

                            events.append({
                                "time": event_time.isoformat(),
                                "currency": item.get("currency", "").upper(),
                                "name": item.get("name", "Unknown"),
                                "impact": impact,
                                "actual": item.get("actual"),
                                "forecast": item.get("forecast"),
                                "previous": item.get("previous"),
                                "source": "mql5"
                            })

                        except Exception as e:
                            logger.debug(f"Failed to parse MQL5 event: {e}")
                            continue

                    logger.info(f"MQL5: fetched {len(events)} events")
                    return events

        except Exception as e:
            logger.error(f"MQL5 fetch error: {e}")
            return []


class InvestingComProvider(NewsProvider):
    """
    Investing.com Calendar via open-source scraper.

    Uses: https://github.com/andrevlima/economic-calendar-api
    Fallback option if others fail.
    """

    name = "investingcom"
    # Public API endpoint (community maintained)
    API_URL = "https://economic-calendar-api.vercel.app/api/calendar"

    async def fetch_events(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Fetch from Investing.com scraper API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, timeout=15) as resp:
                    if resp.status != 200:
                        logger.error(f"Investing.com API error: {resp.status}")
                        return []

                    data = await resp.json()
                    events = []
                    now = datetime.now(timezone.utc)
                    cutoff = now + timedelta(days=days_ahead)

                    for item in data:
                        try:
                            # Parse datetime
                            dt_str = item.get("date", "")
                            if not dt_str:
                                continue

                            event_time = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

                            if event_time < now or event_time > cutoff:
                                continue

                            # Map impact
                            impact_str = item.get("impact", "").lower()
                            if "high" in impact_str or impact_str == "3":
                                impact = "HIGH"
                            elif "medium" in impact_str or impact_str == "2":
                                impact = "MEDIUM"
                            else:
                                impact = "LOW"

                            events.append({
                                "time": event_time.isoformat(),
                                "currency": item.get("currency", "").upper(),
                                "name": item.get("event", "Unknown"),
                                "impact": impact,
                                "actual": item.get("actual"),
                                "forecast": item.get("forecast"),
                                "previous": item.get("previous"),
                                "source": "investingcom"
                            })

                        except Exception as e:
                            logger.debug(f"Failed to parse Investing.com event: {e}")
                            continue

                    logger.info(f"Investing.com: fetched {len(events)} events")
                    return events

        except Exception as e:
            logger.error(f"Investing.com API error: {e}")
            return []


class NewsProviderManager:
    """
    Manages multiple news providers with fallback support.

    Features:
    - Multiple provider support with priority
    - Automatic fallback if primary fails
    - Caching to reduce API calls
    - Auto-save to news_calendar.json
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or _config_path
        self.config = self._load_config()
        self.providers: List[NewsProvider] = []
        self._setup_providers()

        self._cache: List[Dict[str, Any]] = []
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_minutes = 30

    def _load_config(self) -> Dict[str, Any]:
        """Load provider configuration."""
        default_config = {
            "providers": {
                "finnhub": {
                    "enabled": True,
                    "api_key": "",
                    "priority": 1
                },
                "forexfactory": {
                    "enabled": True,
                    "priority": 2
                },
                "investingcom": {
                    "enabled": False,
                    "priority": 3
                }
            },
            "refresh_interval_minutes": 60,
            "days_ahead": 7
        }

        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in loaded:
                            loaded[key] = value
                    return loaded
            except Exception as e:
                logger.error(f"Failed to load news config: {e}")

        # Save default config
        self._save_config(default_config)
        return default_config

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save provider configuration."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save news config: {e}")

    def _setup_providers(self) -> None:
        """Initialize enabled providers sorted by priority."""
        providers_config = self.config.get("providers", {})
        provider_list = []

        for name, cfg in providers_config.items():
            if not cfg.get("enabled", False):
                continue

            priority = cfg.get("priority", 99)

            if name == "finnhub":
                api_key = cfg.get("api_key", "")
                if api_key:
                    provider_list.append((priority, FinnhubProvider(api_key)))
                else:
                    logger.warning("Finnhub enabled but no API key configured")

            elif name == "forexfactory":
                provider_list.append((priority, ForexFactoryProvider()))

            elif name == "investingcom":
                provider_list.append((priority, InvestingComProvider()))

            elif name == "mql5":
                provider_list.append((priority, MQL5Provider()))

            elif name == "fmp":
                api_key = cfg.get("api_key", "")
                if api_key:
                    provider_list.append((priority, FMPProvider(api_key)))
                else:
                    logger.warning("FMP enabled but no API key configured")

            elif name == "recurring":
                provider_list.append((priority, RecurringEventsProvider()))

        # Sort by priority
        provider_list.sort(key=lambda x: x[0])
        self.providers = [p for _, p in provider_list]

        logger.info(f"News providers configured: {[p.name for p in self.providers]}")

    async def fetch_events(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch events from providers with fallback support.

        Args:
            force_refresh: Bypass cache and fetch fresh data

        Returns:
            List of economic events
        """
        # Check cache
        if not force_refresh and self._is_cache_valid():
            logger.debug("Using cached news events")
            return self._cache

        days_ahead = self.config.get("days_ahead", 7)
        events = []

        # Try each provider in priority order
        for provider in self.providers:
            try:
                logger.info(f"Fetching news from {provider.name}...")
                events = await provider.fetch_events(days_ahead)

                if events:
                    # Success - update cache and save
                    self._cache = events
                    self._cache_time = datetime.now(timezone.utc)
                    await self._save_to_calendar(events, provider.name)
                    return events

            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                continue

        # All providers failed - return cached or empty
        if self._cache:
            logger.warning("All providers failed, using stale cache")
            return self._cache

        logger.error("All news providers failed and no cache available")
        return []

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache or not self._cache_time:
            return False

        elapsed = (datetime.now(timezone.utc) - self._cache_time).total_seconds() / 60
        return elapsed < self._cache_ttl_minutes

    async def _save_to_calendar(self, events: List[Dict[str, Any]], source: str) -> None:
        """Save events to news_calendar.json for NewsFilter."""
        try:
            calendar_data = {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "events": events,
                "notes": f"Auto-updated from {source} API"
            }

            _calendar_path.parent.mkdir(parents=True, exist_ok=True)
            with open(_calendar_path, "w", encoding="utf-8") as f:
                json.dump(calendar_data, f, indent=2)

            logger.info(f"Saved {len(events)} events to news_calendar.json")

        except Exception as e:
            logger.error(f"Failed to save calendar: {e}")

    def set_api_key(self, provider: str, api_key: str) -> None:
        """Set API key for a provider."""
        if provider in self.config.get("providers", {}):
            self.config["providers"][provider]["api_key"] = api_key
            self._save_config(self.config)
            self._setup_providers()
            logger.info(f"API key set for {provider}")

    def enable_provider(self, provider: str, enabled: bool = True) -> None:
        """Enable or disable a provider."""
        if provider in self.config.get("providers", {}):
            self.config["providers"][provider]["enabled"] = enabled
            self._save_config(self.config)
            self._setup_providers()
            logger.info(f"Provider {provider} {'enabled' if enabled else 'disabled'}")


# Convenience functions
_manager: Optional[NewsProviderManager] = None


def get_news_manager() -> NewsProviderManager:
    """Get or create the news provider manager singleton."""
    global _manager
    if _manager is None:
        _manager = NewsProviderManager()
    return _manager


async def refresh_news_calendar(force: bool = False) -> List[Dict[str, Any]]:
    """Refresh the news calendar from configured providers."""
    manager = get_news_manager()
    return await manager.fetch_events(force_refresh=force)


def set_finnhub_api_key(api_key: str) -> None:
    """Set the Finnhub API key."""
    manager = get_news_manager()
    manager.set_api_key("finnhub", api_key)
