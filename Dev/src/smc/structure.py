"""
Market Structure Detection - CHoCH, BOS, Swing Points.

Core SMC concept: identify market structure shifts that signal
institutional order flow direction changes.

- SwingPoint: local high/low pivot points
- CHoCH (Change of Character): trend reversal signal
- BOS (Break of Structure): trend continuation signal
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class SwingPoint:
    """A swing high or swing low pivot point."""
    index: int
    price: float
    type: str  # "HIGH" or "LOW"
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "price": self.price,
            "type": self.type,
            "timestamp": self.timestamp,
        }


@dataclass
class StructureShift:
    """A market structure shift (CHoCH or BOS)."""
    type: str  # "CHOCH" or "BOS"
    direction: str  # "BULLISH" or "BEARISH"
    break_level: float  # The price level that was broken
    swing_point: SwingPoint  # The swing point that was violated
    confirmation_candle_idx: int  # Index of candle that confirmed the break
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "direction": self.direction,
            "break_level": self.break_level,
            "swing_point": self.swing_point.to_dict(),
            "confirmation_candle_idx": self.confirmation_candle_idx,
            "timestamp": self.timestamp,
        }


def detect_swing_points(
    candles: List[Dict[str, Any]],
    left_bars: int = 5,
    right_bars: int = 2
) -> List[SwingPoint]:
    """
    Detect swing highs and swing lows using pivot logic.

    A swing high requires `left_bars` lower highs to the left
    and `right_bars` lower highs to the right.

    Args:
        candles: OHLC candle data
        left_bars: Number of bars to look left (default 5)
        right_bars: Number of bars to look right (default 2)

    Returns:
        List of SwingPoint sorted by index
    """
    if len(candles) < left_bars + right_bars + 1:
        return []

    swing_points = []

    for i in range(left_bars, len(candles) - right_bars):
        high = candles[i]["high"]
        low = candles[i]["low"]
        timestamp = candles[i].get("time", "")

        # Check swing high
        is_swing_high = True
        for j in range(1, left_bars + 1):
            if candles[i - j]["high"] >= high:
                is_swing_high = False
                break
        if is_swing_high:
            for j in range(1, right_bars + 1):
                if candles[i + j]["high"] >= high:
                    is_swing_high = False
                    break

        if is_swing_high:
            swing_points.append(SwingPoint(
                index=i, price=high, type="HIGH", timestamp=timestamp
            ))

        # Check swing low
        is_swing_low = True
        for j in range(1, left_bars + 1):
            if candles[i - j]["low"] <= low:
                is_swing_low = False
                break
        if is_swing_low:
            for j in range(1, right_bars + 1):
                if candles[i + j]["low"] <= low:
                    is_swing_low = False
                    break

        if is_swing_low:
            swing_points.append(SwingPoint(
                index=i, price=low, type="LOW", timestamp=timestamp
            ))

    return sorted(swing_points, key=lambda sp: sp.index)


def classify_structure(swing_points: List[SwingPoint]) -> str:
    """
    Classify market structure from swing points.

    Returns:
        "HH_HL" (bullish), "LH_LL" (bearish), or "RANGING"
    """
    highs = [sp for sp in swing_points if sp.type == "HIGH"]
    lows = [sp for sp in swing_points if sp.type == "LOW"]

    if len(highs) < 2 or len(lows) < 2:
        return "RANGING"

    # Check last 2 swing highs and lows
    last_highs = highs[-2:]
    last_lows = lows[-2:]

    higher_highs = last_highs[1].price > last_highs[0].price
    higher_lows = last_lows[1].price > last_lows[0].price
    lower_highs = last_highs[1].price < last_highs[0].price
    lower_lows = last_lows[1].price < last_lows[0].price

    if higher_highs and higher_lows:
        return "HH_HL"
    elif lower_highs and lower_lows:
        return "LH_LL"
    else:
        return "RANGING"


def detect_choch(
    candles: List[Dict[str, Any]],
    swing_points: List[SwingPoint]
) -> Optional[StructureShift]:
    """
    Detect Change of Character (CHoCH).

    CHoCH signals a potential trend reversal:
    - In uptrend (HH/HL): CHoCH when price closes below last HL
    - In downtrend (LH/LL): CHoCH when price closes above last LH

    Args:
        candles: OHLC candle data
        swing_points: Previously detected swing points

    Returns:
        StructureShift or None
    """
    structure = classify_structure(swing_points)

    highs = [sp for sp in swing_points if sp.type == "HIGH"]
    lows = [sp for sp in swing_points if sp.type == "LOW"]

    if structure == "HH_HL" and len(lows) >= 1:
        # Bullish structure -> look for bearish CHoCH
        # CHoCH = price closes below the last Higher Low
        last_hl = lows[-1]
        # Search candles AFTER the swing low for a close below it
        for i in range(last_hl.index + 1, len(candles)):
            if candles[i]["close"] < last_hl.price:
                return StructureShift(
                    type="CHOCH",
                    direction="BEARISH",
                    break_level=last_hl.price,
                    swing_point=last_hl,
                    confirmation_candle_idx=i,
                    timestamp=candles[i].get("time", ""),
                )
                break

    elif structure == "LH_LL" and len(highs) >= 1:
        # Bearish structure -> look for bullish CHoCH
        # CHoCH = price closes above the last Lower High
        last_lh = highs[-1]
        for i in range(last_lh.index + 1, len(candles)):
            if candles[i]["close"] > last_lh.price:
                return StructureShift(
                    type="CHOCH",
                    direction="BULLISH",
                    break_level=last_lh.price,
                    swing_point=last_lh,
                    confirmation_candle_idx=i,
                    timestamp=candles[i].get("time", ""),
                )
                break

    return None


def detect_bos(
    candles: List[Dict[str, Any]],
    swing_points: List[SwingPoint]
) -> Optional[StructureShift]:
    """
    Detect Break of Structure (BOS).

    BOS signals trend continuation:
    - In uptrend (HH/HL): BOS when price closes above last HH
    - In downtrend (LH/LL): BOS when price closes below last LL

    Args:
        candles: OHLC candle data
        swing_points: Previously detected swing points

    Returns:
        StructureShift or None
    """
    structure = classify_structure(swing_points)

    highs = [sp for sp in swing_points if sp.type == "HIGH"]
    lows = [sp for sp in swing_points if sp.type == "LOW"]

    if structure == "HH_HL" and len(highs) >= 1:
        # Bullish structure -> BOS = close above last HH
        last_hh = highs[-1]
        for i in range(last_hh.index + 1, len(candles)):
            if candles[i]["close"] > last_hh.price:
                return StructureShift(
                    type="BOS",
                    direction="BULLISH",
                    break_level=last_hh.price,
                    swing_point=last_hh,
                    confirmation_candle_idx=i,
                    timestamp=candles[i].get("time", ""),
                )
                break

    elif structure == "LH_LL" and len(lows) >= 1:
        # Bearish structure -> BOS = close below last LL
        last_ll = lows[-1]
        for i in range(last_ll.index + 1, len(candles)):
            if candles[i]["close"] < last_ll.price:
                return StructureShift(
                    type="BOS",
                    direction="BEARISH",
                    break_level=last_ll.price,
                    swing_point=last_ll,
                    confirmation_candle_idx=i,
                    timestamp=candles[i].get("time", ""),
                )
                break

    return None
