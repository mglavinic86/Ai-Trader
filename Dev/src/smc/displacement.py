"""
Displacement Detection - Institutional momentum moves.

Displacement is a strong, impulsive candle that shows institutional
order flow. Characterized by:
- Large body relative to average
- Small wicks (minimal opposition)
- Creates FVGs in its wake
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class Displacement:
    """A detected displacement (institutional impulse move)."""
    direction: str  # "BULLISH" or "BEARISH"
    candle_index: int
    body_size: float
    avg_body_ratio: float  # How many times larger than average
    confirmed: bool = True  # Met all criteria
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "candle_index": self.candle_index,
            "body_size": self.body_size,
            "avg_body_ratio": round(self.avg_body_ratio, 2),
            "confirmed": self.confirmed,
        }


def detect_displacement(
    candles: List[Dict[str, Any]],
    min_ratio: float = 2.0,
    max_wick_pct: float = 0.30,
    lookback: int = 20
) -> List[Displacement]:
    """
    Detect displacement candles (institutional impulse moves).

    Criteria:
    1. Body size > min_ratio * average body (last `lookback` candles)
    2. Wick < max_wick_pct of total range (minimal opposition)

    Args:
        candles: OHLC candle data
        min_ratio: Minimum body-to-average ratio (default 2.0x)
        max_wick_pct: Maximum wick percentage of total range (default 30%)
        lookback: Number of candles for average calculation

    Returns:
        List of Displacement events
    """
    if len(candles) < lookback + 1:
        return []

    displacements = []

    for i in range(lookback, len(candles)):
        candle = candles[i]

        # Calculate body and range
        body = abs(candle["close"] - candle["open"])
        total_range = candle["high"] - candle["low"]

        if total_range == 0:
            continue

        # Calculate average body over lookback period
        avg_body = sum(
            abs(candles[j]["close"] - candles[j]["open"])
            for j in range(i - lookback, i)
        ) / lookback

        if avg_body == 0:
            continue

        ratio = body / avg_body

        # Check body size criteria
        if ratio < min_ratio:
            continue

        # Check wick criteria
        if candle["close"] > candle["open"]:
            # Bullish candle
            upper_wick = candle["high"] - candle["close"]
            lower_wick = candle["open"] - candle["low"]
            direction = "BULLISH"
        else:
            # Bearish candle
            upper_wick = candle["high"] - candle["open"]
            lower_wick = candle["close"] - candle["low"]
            direction = "BEARISH"

        total_wick = upper_wick + lower_wick
        wick_pct = total_wick / total_range

        if wick_pct > max_wick_pct:
            continue

        displacements.append(Displacement(
            direction=direction,
            candle_index=i,
            body_size=body,
            avg_body_ratio=ratio,
            confirmed=True,
            timestamp=candle.get("time", ""),
        ))

    return displacements
