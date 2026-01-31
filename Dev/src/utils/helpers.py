"""
Common utility functions.

Usage:
    from src.utils.helpers import format_price, pip_value, generate_trade_id
"""

from datetime import datetime
from typing import Optional
import uuid


def format_price(price: float, instrument: str) -> str:
    """
    Format price with correct decimal places.

    Args:
        price: Price value
        instrument: Currency pair (e.g., "EUR_USD")

    Returns:
        Formatted price string
    """
    decimals = 3 if "JPY" in instrument else 5
    return f"{price:.{decimals}f}"


def pip_value(instrument: str) -> float:
    """
    Get pip value for instrument.

    Args:
        instrument: Currency pair

    Returns:
        Pip value (0.0001 for most, 0.01 for JPY pairs)
    """
    return 0.01 if "JPY" in instrument else 0.0001


def get_pip_divisor(instrument: str, symbol_info=None) -> float:
    """
    Get pip divisor for spread calculation.
    Uses MT5 symbol info if available, falls back to instrument-based logic.

    Args:
        instrument: Currency pair (e.g., "EUR_USD")
        symbol_info: Optional MT5 symbol info object with digits attribute

    Returns:
        Pip divisor (e.g., 0.0001 for EUR/USD, 0.01 for JPY pairs)
    """
    if symbol_info and hasattr(symbol_info, 'digits'):
        # MT5: digits 5 = 0.0001, digits 3 = 0.01, digits 2 = 0.1
        return 10 ** -(symbol_info.digits - 1)

    instrument_upper = instrument.upper()
    if "XAU" in instrument_upper or "XAG" in instrument_upper:
        return 0.1  # Metals
    elif "BTC" in instrument_upper or "ETH" in instrument_upper:
        return 1.0  # Crypto
    elif "JPY" in instrument_upper:
        return 0.01  # JPY pairs
    else:
        return 0.0001  # Standard forex


def price_to_pips(price_diff: float, instrument: str) -> float:
    """
    Convert price difference to pips.

    Args:
        price_diff: Price difference
        instrument: Currency pair

    Returns:
        Difference in pips
    """
    return abs(price_diff) / pip_value(instrument)


def pips_to_price(pips: float, instrument: str) -> float:
    """
    Convert pips to price difference.

    Args:
        pips: Number of pips
        instrument: Currency pair

    Returns:
        Price difference
    """
    return pips * pip_value(instrument)


def generate_trade_id(prefix: str = "") -> str:
    """
    Generate unique trade ID.

    Format: [prefix-]YYYY-MM-DD-XXXX

    Args:
        prefix: Optional prefix

    Returns:
        Unique trade ID
    """
    date_part = datetime.now().strftime("%Y-%m-%d")
    unique_part = str(uuid.uuid4())[:4].upper()

    if prefix:
        return f"{prefix}-{date_part}-{unique_part}"
    return f"{date_part}-{unique_part}"


def calculate_position_size(
    equity: float,
    risk_percent: float,
    entry_price: float,
    stop_loss: float,
    instrument: str
) -> int:
    """
    Calculate position size based on risk.

    Args:
        equity: Account equity
        risk_percent: Risk as decimal (0.01 = 1%)
        entry_price: Entry price
        stop_loss: Stop loss price
        instrument: Currency pair

    Returns:
        Position size in units
    """
    risk_amount = equity * risk_percent
    pip_distance = price_to_pips(entry_price - stop_loss, instrument)

    if pip_distance == 0:
        return 0

    # Approximate pip value per unit (simplified)
    pip_val = pip_value(instrument)

    units = int(risk_amount / (pip_distance * pip_val))
    return units


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2h 15m", "45m 30s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"

    minutes = int(seconds / 60)
    if minutes < 60:
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"

    hours = int(minutes / 60)
    mins = int(minutes % 60)

    if hours < 24:
        return f"{hours}h {mins}m"

    days = int(hours / 24)
    hrs = int(hours % 24)
    return f"{days}d {hrs}h"


def validate_instrument(instrument: str) -> tuple[bool, str]:
    """
    Validate instrument format.

    Args:
        instrument: Currency pair

    Returns:
        (is_valid, error_message)
    """
    if not instrument:
        return False, "Instrument cannot be empty"

    if "_" not in instrument:
        return False, f"Invalid format. Use XXX_YYY (e.g., EUR_USD)"

    parts = instrument.split("_")
    if len(parts) != 2:
        return False, f"Invalid format. Use XXX_YYY (e.g., EUR_USD)"

    if len(parts[0]) != 3 or len(parts[1]) != 3:
        return False, f"Currency codes must be 3 characters (e.g., EUR, USD)"

    return True, "OK"


def risk_tier_for_confidence(confidence: int) -> tuple[float, str]:
    """
    Get risk tier for confidence score.

    Args:
        confidence: Score 0-100

    Returns:
        (risk_percent, tier_name)
    """
    if confidence >= 90:
        return 0.03, "TIER 3 (High Confidence)"
    elif confidence >= 70:
        return 0.02, "TIER 2 (Good Confidence)"
    elif confidence >= 50:
        return 0.01, "TIER 1 (Moderate Confidence)"
    else:
        return 0.0, "NO TRADE (Low Confidence)"
