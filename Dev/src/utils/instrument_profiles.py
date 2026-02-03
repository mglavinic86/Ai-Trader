"""
Instrument Profiles - Risk/session/spread presets per instrument.

Profiles live in settings/instrument_profiles.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


_dev_dir = Path(__file__).parent.parent.parent
_profiles_path = _dev_dir / "settings" / "instrument_profiles.json"


def _load_profiles() -> dict:
    if _profiles_path.exists():
        with open(_profiles_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_profile(instrument: str) -> dict:
    profiles = _load_profiles()
    default = profiles.get("default", {})
    specific = profiles.get(instrument, {})
    merged = {**default, **specific}
    merged["instrument"] = instrument
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
