"""
Instrument Profiles - Risk/session/spread presets per instrument.

Profiles live in settings/instrument_profiles.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


_dev_dir = Path(__file__).parent.parent.parent
_profiles_path = _dev_dir / "settings" / "instrument_profiles.json"


# Canonical aliases used across scanner/executor to avoid silent profile fallback.
ALIAS_MAP = {
    "EURUSD": "EUR_USD",
    "GBPUSD": "GBP_USD",
    "XAUUSD": "XAU_USD",
    "BTCUSD": "BTC_USD",
    "USDJPY": "USD_JPY",
    "USDCHF": "USD_CHF",
    "USDCAD": "USD_CAD",
    "AUDUSD": "AUD_USD",
    "EURGBP": "EUR_GBP",
    "EURJPY": "EUR_JPY",
    "NZDUSD": "NZD_USD",
    "GBPJPY": "GBP_JPY",
    "EUR/USD": "EUR_USD",
    "GBP/USD": "GBP_USD",
    "XAU/USD": "XAU_USD",
    "BTC/USD": "BTC_USD",
}


def _load_profiles() -> dict:
    if _profiles_path.exists():
        with open(_profiles_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_profiles() -> dict:
    """Public loader for instrument profile settings."""
    return _load_profiles()


def save_profiles(profiles: dict) -> None:
    """Persist instrument profile settings."""
    _profiles_path.parent.mkdir(parents=True, exist_ok=True)
    with open(_profiles_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)


def normalize_sessions(sessions: list[str]) -> list[str]:
    """Validate and normalize session windows as HH-HH (UTC)."""
    normalized: list[str] = []
    for raw in sessions:
        text = str(raw or "").strip()
        if not text:
            continue
        if not re.fullmatch(r"\d{1,2}-\d{1,2}", text):
            raise ValueError(f"Invalid session '{text}'. Expected HH-HH.")
        start_text, end_text = text.split("-")
        start = int(start_text)
        end = int(end_text)
        if not (0 <= start <= 24 and 0 <= end <= 24):
            raise ValueError(f"Invalid session '{text}'. Hours must be between 0 and 24.")
        if start == end and start != 0:
            raise ValueError(f"Invalid session '{text}'. Start and end cannot be equal.")
        normalized.append(f"{start:02d}-{end:02d}")
    # Deduplicate while keeping order.
    return list(dict.fromkeys(normalized))


def set_instrument_sessions(instrument: str, sessions: list[str]) -> list[str]:
    """
    Update allowed trading sessions for a specific instrument profile.
    Returns normalized sessions that were saved.
    """
    canonical = normalize_instrument_symbol(instrument)
    normalized = normalize_sessions(sessions)
    profiles = _load_profiles()
    existing = profiles.get(canonical, {})
    profiles[canonical] = {**existing, "sessions": normalized}
    save_profiles(profiles)
    return normalized


def normalize_instrument_symbol(instrument: str) -> str:
    """Normalize instrument symbol using strict alias map."""
    if not instrument:
        return instrument
    key = instrument.strip().upper()
    return ALIAS_MAP.get(key, key)


def get_profile(instrument: str) -> dict:
    profiles = _load_profiles()
    canonical = normalize_instrument_symbol(instrument)
    default = profiles.get("default", {})
    specific = profiles.get(canonical, profiles.get(instrument, {}))
    merged = {**default, **specific}
    merged["instrument"] = canonical
    return merged


def get_profile_strict(instrument: str) -> dict:
    """
    Get profile with fail-fast behavior.

    Raises:
        KeyError if profile is not explicitly defined (no default fallback).
    """
    profiles = _load_profiles()
    canonical = normalize_instrument_symbol(instrument)
    specific = profiles.get(canonical)
    if specific is None:
        raise KeyError(f"No strict profile for instrument '{instrument}' (canonical '{canonical}')")
    merged = {**profiles.get("default", {}), **specific}
    merged["instrument"] = canonical
    return merged


def _parse_session(session_str: str) -> Optional[tuple[int, int]]:
    try:
        start, end = session_str.split("-")
        return int(start), int(end)
    except Exception:
        return None


def is_in_session(profile: dict, now_utc: Optional[datetime] = None) -> bool:
    """Check if current UTC time is within allowed sessions."""
    sessions = profile.get("sessions", [])
    allow_weekends = profile.get("allow_weekends", False)

    if not sessions:
        return True

    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    if not allow_weekends and now_utc.weekday() >= 5:
        return False

    hour = now_utc.hour
    for s in sessions:
        parsed = _parse_session(s)
        if not parsed:
            continue
        start, end = parsed
        if start <= end:
            if start <= hour < end:
                return True
        else:
            # Overnight window, e.g. 21-6
            if hour >= start or hour < end:
                return True

    return False
