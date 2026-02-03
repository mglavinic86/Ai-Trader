"""
News Calendar Filter - Avoid trading during high-impact news events.

Filters trading signals based on upcoming economic events that could
cause significant volatility.

Usage:
    from src.analysis.news_filter import NewsFilter, news_filter

    should_avoid, reason = news_filter.should_avoid_trade("EUR_USD")

    # Auto-refresh from API providers
    await news_filter.refresh_from_api()
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from src.utils.logger import logger


_dev_dir = Path(__file__).parent.parent.parent
_calendar_path = _dev_dir / "settings" / "news_calendar.json"


class NewsFilter:
    """
    Filters trades based on upcoming economic news events.

    Events are loaded from settings/news_calendar.json and can be:
    - HIGH: Major events (NFP, FOMC, ECB) - avoid 30 min before/after
    - MEDIUM: Moderate events (GDP, CPI) - avoid 15 min before/after
    - LOW: Minor events - no avoidance

    The calendar file should be updated regularly (manually or via API).
    """

    def __init__(self, calendar_path: Optional[Path] = None):
        """
        Initialize news filter.

        Args:
            calendar_path: Path to news calendar JSON (uses default if None)
        """
        self.calendar_path = calendar_path or _calendar_path
        self._events: List[Dict[str, Any]] = []
        self._last_load: Optional[datetime] = None
        self._load_interval_minutes = 5  # Reload every 5 minutes

        # Default avoid windows (minutes before/after event)
        self.avoid_windows = {
            "HIGH": 30,
            "MEDIUM": 15,
            "LOW": 0
        }

    def _load_calendar(self) -> None:
        """Load news calendar from file."""
        if not self.calendar_path.exists():
            self._events = []
            logger.debug("News calendar not found, trading without news filter")
            return

        try:
            with open(self.calendar_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._events = data.get("events", [])
            self._last_load = datetime.now(timezone.utc)
            logger.info(f"Loaded {len(self._events)} news events from calendar")

        except Exception as e:
            logger.error(f"Failed to load news calendar: {e}")
            self._events = []

    def _should_reload(self) -> bool:
        """Check if calendar should be reloaded."""
        if self._last_load is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self._last_load).total_seconds() / 60
        return elapsed >= self._load_interval_minutes

    def _get_affected_currencies(self, instrument: str) -> List[str]:
        """Get currencies that could affect this instrument."""
        # Extract base and quote currencies
        currencies = []

        # Handle different instrument formats
        # EUR_USD, EURUSD, EUR/USD
        clean = instrument.replace("_", "").replace("/", "").upper()

        if len(clean) >= 6:
            currencies.append(clean[:3])  # Base
            currencies.append(clean[3:6])  # Quote

        # Special cases
        if "XAU" in instrument or "GOLD" in instrument:
            currencies.append("USD")  # Gold is priced in USD
        if "BTC" in instrument:
            currencies.append("USD")

        return currencies

    def should_avoid_trade(
        self,
        instrument: str,
        now: Optional[datetime] = None
    ) -> tuple[bool, str]:
        """
        Check if trading should be avoided due to upcoming news.

        Args:
            instrument: Instrument to check
            now: Current time (uses UTC now if None)

        Returns:
            (should_avoid, reason)
        """
        # Reload calendar if needed
        if self._should_reload():
            self._load_calendar()

        if not self._events:
            return False, ""

        if now is None:
            now = datetime.now(timezone.utc)

        # Get affected currencies
        affected = self._get_affected_currencies(instrument)
        if not affected:
            return False, ""

        # Check each event
        for event in self._events:
            try:
                event_time = datetime.fromisoformat(event["time"].replace("Z", "+00:00"))
                impact = event.get("impact", "LOW").upper()
                currency = event.get("currency", "").upper()

                # Skip if currency not affected
                if currency not in affected:
                    continue

                # Get avoid window
                avoid_minutes = self.avoid_windows.get(impact, 0)
                if avoid_minutes == 0:
                    continue

                # Check if within avoid window
                window_start = event_time - timedelta(minutes=avoid_minutes)
                window_end = event_time + timedelta(minutes=avoid_minutes)

                if window_start <= now <= window_end:
                    event_name = event.get("name", "Unknown event")
                    minutes_to = int((event_time - now).total_seconds() / 60)
                    if minutes_to > 0:
                        reason = f"{impact} impact: {event_name} ({currency}) in {minutes_to} min"
                    else:
                        reason = f"{impact} impact: {event_name} ({currency}) just released"
                    return True, reason

            except Exception as e:
                logger.warning(f"Failed to parse event: {e}")
                continue

        return False, ""

    def get_upcoming_events(
        self,
        instrument: str,
        hours_ahead: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming events that could affect the instrument.

        Args:
            instrument: Instrument to check
            hours_ahead: How many hours ahead to look

        Returns:
            List of upcoming events
        """
        if self._should_reload():
            self._load_calendar()

        if not self._events:
            return []

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=hours_ahead)
        affected = self._get_affected_currencies(instrument)

        upcoming = []
        for event in self._events:
            try:
                event_time = datetime.fromisoformat(event["time"].replace("Z", "+00:00"))
                currency = event.get("currency", "").upper()

                if currency in affected and now <= event_time <= cutoff:
                    upcoming.append({
                        **event,
                        "time_parsed": event_time,
                        "minutes_until": int((event_time - now).total_seconds() / 60)
                    })

            except Exception:
                continue

        # Sort by time
        upcoming.sort(key=lambda x: x["time_parsed"])
        return upcoming


    async def refresh_from_api(self, force: bool = False) -> bool:
        """
        Refresh calendar from configured API providers.

        Args:
            force: Force refresh even if cache is valid

        Returns:
            True if refresh successful
        """
        try:
            from src.analysis.news_providers import refresh_news_calendar
            events = await refresh_news_calendar(force=force)

            if events:
                self._events = events
                self._last_load = datetime.now(timezone.utc)
                logger.info(f"Refreshed news calendar from API: {len(events)} events")
                return True

            return False

        except ImportError:
            logger.warning("news_providers module not available")
            return False
        except Exception as e:
            logger.error(f"Failed to refresh from API: {e}")
            return False

    def get_calendar_status(self) -> Dict[str, Any]:
        """Get current calendar status for UI display."""
        if self._should_reload():
            self._load_calendar()

        # Count events by impact
        high_count = sum(1 for e in self._events if e.get("impact", "").upper() == "HIGH")
        medium_count = sum(1 for e in self._events if e.get("impact", "").upper() == "MEDIUM")

        # Get source from calendar file
        source = "unknown"
        try:
            if self.calendar_path.exists():
                with open(self.calendar_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    source = data.get("source", "unknown")
                    last_updated = data.get("last_updated", "")
        except Exception:
            last_updated = ""

        return {
            "total_events": len(self._events),
            "high_impact": high_count,
            "medium_impact": medium_count,
            "source": source,
            "last_updated": last_updated,
            "last_load": self._last_load.isoformat() if self._last_load else None
        }


# Singleton instance
news_filter = NewsFilter()


async def auto_refresh_news(interval_minutes: int = 60) -> None:
    """
    Background task to auto-refresh news calendar.

    Args:
        interval_minutes: How often to refresh (default 60 min)
    """
    while True:
        try:
            await news_filter.refresh_from_api()
        except Exception as e:
            logger.error(f"Auto-refresh failed: {e}")

        await asyncio.sleep(interval_minutes * 60)
