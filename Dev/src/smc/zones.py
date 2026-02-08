"""
SMC Zones - Fair Value Gaps, Order Blocks, Premium/Discount.

Key zone types:
- FVG (Fair Value Gap): imbalance in price that acts as magnet
- Order Block: last opposing candle before displacement
- Premium/Discount: where we want to buy/sell relative to range
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class FairValueGap:
    """A Fair Value Gap (imbalance) in price."""
    start_price: float  # Gap start (closer to price)
    end_price: float  # Gap end (farther from price)
    direction: str  # "BULLISH" or "BEARISH"
    candle_index: int  # Index of middle candle (the one that created the gap)
    filled: bool = False
    fill_percentage: float = 0.0
    timestamp: str = ""

    @property
    def midpoint(self) -> float:
        return (self.start_price + self.end_price) / 2

    @property
    def size(self) -> float:
        return abs(self.end_price - self.start_price)

    def to_dict(self) -> dict:
        return {
            "start_price": self.start_price,
            "end_price": self.end_price,
            "direction": self.direction,
            "candle_index": self.candle_index,
            "filled": self.filled,
            "fill_percentage": self.fill_percentage,
            "midpoint": self.midpoint,
            "size": self.size,
        }


@dataclass
class OrderBlock:
    """An Order Block - last opposing candle before displacement."""
    high: float
    low: float
    direction: str  # "BULLISH" (demand) or "BEARISH" (supply)
    candle_index: int
    mitigated: bool = False  # Has price returned and filled through it?
    displacement_strength: float = 0.0  # How strong the displacement was
    timestamp: str = ""

    @property
    def midpoint(self) -> float:
        return (self.high + self.low) / 2

    def to_dict(self) -> dict:
        return {
            "high": self.high,
            "low": self.low,
            "direction": self.direction,
            "candle_index": self.candle_index,
            "mitigated": self.mitigated,
            "displacement_strength": self.displacement_strength,
            "midpoint": self.midpoint,
        }


@dataclass
class SupplyDemandZone:
    """A supply or demand zone combining OB/FVG data."""
    high: float
    low: float
    type: str  # "SUPPLY" or "DEMAND"
    source: str  # "OB", "FVG", "OB_FVG" (overlap)
    strength: int = 1  # Higher = more confluence
    fresh: bool = True  # Has price revisited this zone?

    def to_dict(self) -> dict:
        return {
            "high": self.high,
            "low": self.low,
            "type": self.type,
            "source": self.source,
            "strength": self.strength,
            "fresh": self.fresh,
        }


def detect_fvg(
    candles: List[Dict[str, Any]],
    min_gap_ratio: float = 0.0
) -> List[FairValueGap]:
    """
    Detect Fair Value Gaps in candle data.

    Bullish FVG: candle[i-1].high < candle[i+1].low (gap up)
    Bearish FVG: candle[i-1].low > candle[i+1].high (gap down)

    Args:
        candles: OHLC candle data
        min_gap_ratio: Minimum gap size relative to average body (0 = any gap)

    Returns:
        List of FairValueGap
    """
    if len(candles) < 3:
        return []

    fvgs = []
    current_price = candles[-1]["close"]

    # Calculate average body size for filtering
    bodies = [abs(c["close"] - c["open"]) for c in candles[-30:]]
    avg_body = sum(bodies) / len(bodies) if bodies else 0

    for i in range(1, len(candles) - 1):
        prev = candles[i - 1]
        curr = candles[i]
        next_ = candles[i + 1]

        # Bullish FVG: gap between prev high and next low
        if prev["high"] < next_["low"]:
            gap_size = next_["low"] - prev["high"]
            if min_gap_ratio == 0 or (avg_body > 0 and gap_size / avg_body >= min_gap_ratio):
                fvg = FairValueGap(
                    start_price=next_["low"],
                    end_price=prev["high"],
                    direction="BULLISH",
                    candle_index=i,
                    timestamp=curr.get("time", ""),
                )
                # Check if filled by subsequent price action
                _check_fvg_fill(fvg, candles[i + 1:], current_price)
                fvgs.append(fvg)

        # Bearish FVG: gap between prev low and next high
        if prev["low"] > next_["high"]:
            gap_size = prev["low"] - next_["high"]
            if min_gap_ratio == 0 or (avg_body > 0 and gap_size / avg_body >= min_gap_ratio):
                fvg = FairValueGap(
                    start_price=next_["high"],
                    end_price=prev["low"],
                    direction="BEARISH",
                    candle_index=i,
                    timestamp=curr.get("time", ""),
                )
                _check_fvg_fill(fvg, candles[i + 1:], current_price)
                fvgs.append(fvg)

    return fvgs


def _check_fvg_fill(
    fvg: FairValueGap,
    subsequent_candles: List[Dict[str, Any]],
    current_price: float
) -> None:
    """Check if an FVG has been filled by subsequent price action."""
    gap_top = max(fvg.start_price, fvg.end_price)
    gap_bottom = min(fvg.start_price, fvg.end_price)
    gap_size = gap_top - gap_bottom

    if gap_size <= 0:
        fvg.filled = True
        fvg.fill_percentage = 100.0
        return

    max_fill = 0.0

    for candle in subsequent_candles:
        if fvg.direction == "BULLISH":
            # Bullish FVG fills when price comes down into the gap
            if candle["low"] <= gap_top:
                penetration = gap_top - max(candle["low"], gap_bottom)
                fill_pct = (penetration / gap_size) * 100
                max_fill = max(max_fill, fill_pct)
        else:
            # Bearish FVG fills when price comes up into the gap
            if candle["high"] >= gap_bottom:
                penetration = min(candle["high"], gap_top) - gap_bottom
                fill_pct = (penetration / gap_size) * 100
                max_fill = max(max_fill, fill_pct)

    fvg.fill_percentage = min(max_fill, 100.0)
    fvg.filled = fvg.fill_percentage >= 100.0


def detect_order_blocks(
    candles: List[Dict[str, Any]],
    swing_points: List = None,
    min_displacement_ratio: float = 2.0
) -> List[OrderBlock]:
    """
    Detect Order Blocks in candle data.

    Bullish OB: last bearish candle before strong bullish displacement
    Bearish OB: last bullish candle before strong bearish displacement

    Args:
        candles: OHLC candle data
        swing_points: Optional swing points for context
        min_displacement_ratio: Min body size vs average to qualify as displacement

    Returns:
        List of OrderBlock
    """
    if len(candles) < 5:
        return []

    order_blocks = []

    # Calculate average body size
    bodies = [abs(c["close"] - c["open"]) for c in candles[-30:]]
    avg_body = sum(bodies) / len(bodies) if bodies else 0

    if avg_body == 0:
        return []

    current_price = candles[-1]["close"]

    for i in range(1, len(candles) - 1):
        curr = candles[i]
        next_ = candles[i + 1]

        curr_body = abs(curr["close"] - curr["open"])
        next_body = abs(next_["close"] - next_["open"])

        # Bullish OB: current candle is bearish, next is strong bullish displacement
        if (curr["close"] < curr["open"] and  # Bearish candle
                next_["close"] > next_["open"] and  # Bullish candle
                next_body >= avg_body * min_displacement_ratio):  # Strong displacement
            ob = OrderBlock(
                high=curr["high"],
                low=curr["low"],
                direction="BULLISH",
                candle_index=i,
                displacement_strength=next_body / avg_body,
                timestamp=curr.get("time", ""),
            )
            # Check if mitigated (price returned through OB)
            ob.mitigated = _is_ob_mitigated(ob, candles[i + 2:])
            order_blocks.append(ob)

        # Bearish OB: current candle is bullish, next is strong bearish displacement
        if (curr["close"] > curr["open"] and  # Bullish candle
                next_["close"] < next_["open"] and  # Bearish candle
                next_body >= avg_body * min_displacement_ratio):  # Strong displacement
            ob = OrderBlock(
                high=curr["high"],
                low=curr["low"],
                direction="BEARISH",
                candle_index=i,
                displacement_strength=next_body / avg_body,
                timestamp=curr.get("time", ""),
            )
            ob.mitigated = _is_ob_mitigated(ob, candles[i + 2:])
            order_blocks.append(ob)

    return order_blocks


def _is_ob_mitigated(ob: OrderBlock, subsequent_candles: List[Dict]) -> bool:
    """Check if an order block has been mitigated (price went through it)."""
    for candle in subsequent_candles:
        if ob.direction == "BULLISH":
            # Bullish OB mitigated when price goes below OB low
            if candle["close"] < ob.low:
                return True
        else:
            # Bearish OB mitigated when price goes above OB high
            if candle["close"] > ob.high:
                return True
    return False


def calculate_premium_discount(
    swing_high: float,
    swing_low: float,
    current_price: float
) -> Dict[str, Any]:
    """
    Calculate premium/discount zone position.

    Above 50% of range = Premium (sell zone)
    Below 50% = Discount (buy zone)
    45-55% = Equilibrium (no trade zone)

    Args:
        swing_high: Recent swing high
        swing_low: Recent swing low
        current_price: Current market price

    Returns:
        Dict with zone, percentage, equilibrium level
    """
    if swing_high <= swing_low:
        return {"zone": "UNKNOWN", "percentage": 50.0, "equilibrium": 0}

    range_size = swing_high - swing_low
    position = (current_price - swing_low) / range_size * 100

    equilibrium = swing_low + range_size * 0.5

    if position >= 55:
        zone = "PREMIUM"
    elif position <= 45:
        zone = "DISCOUNT"
    else:
        zone = "EQUILIBRIUM"

    return {
        "zone": zone,
        "percentage": round(position, 1),
        "equilibrium": equilibrium,
        "swing_high": swing_high,
        "swing_low": swing_low,
    }
