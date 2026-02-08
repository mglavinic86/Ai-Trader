"""
Liquidity Analysis - The core SMC concept.

"No sweep = No trade" - Every valid SMC entry requires a liquidity
sweep to confirm institutional order flow.

- LiquidityLevel: price level where stop losses cluster
- LiquidityMap: maps buyside and sellside liquidity
- Session levels: London/NY/Asian session highs and lows
- Sweep detection: identifies when price pierces and reverses from liquidity
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from src.smc.structure import SwingPoint


@dataclass
class LiquidityLevel:
    """A liquidity level where stops cluster."""
    price: float
    type: str  # "BUYSIDE" (above price) or "SELLSIDE" (below price)
    source: str  # "EQUAL_HIGHS", "EQUAL_LOWS", "SWING", "SESSION"
    strength: int = 1  # How many times this level has been tested
    swept: bool = False
    sweep_candle_idx: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "price": self.price,
            "type": self.type,
            "source": self.source,
            "strength": self.strength,
            "swept": self.swept,
        }


@dataclass
class LiquidityMap:
    """Map of all liquidity levels."""
    buyside: List[LiquidityLevel] = field(default_factory=list)
    sellside: List[LiquidityLevel] = field(default_factory=list)
    nearest_buyside: Optional[LiquidityLevel] = None
    nearest_sellside: Optional[LiquidityLevel] = None

    def to_dict(self) -> dict:
        return {
            "buyside_count": len(self.buyside),
            "sellside_count": len(self.sellside),
            "nearest_buyside": self.nearest_buyside.price if self.nearest_buyside else None,
            "nearest_sellside": self.nearest_sellside.price if self.nearest_sellside else None,
            "buyside_levels": [l.to_dict() for l in self.buyside[:5]],
            "sellside_levels": [l.to_dict() for l in self.sellside[:5]],
        }


@dataclass
class LiquiditySweep:
    """A detected liquidity sweep event."""
    level: LiquidityLevel
    sweep_candle_idx: int
    sweep_direction: str  # "BUYSIDE_SWEEP" or "SELLSIDE_SWEEP"
    reversal_confirmed: bool  # Did price reverse after sweep?
    session: str = ""  # Which session the sweep occurred in
    sweep_depth_pips: float = 0.0  # How far past the level price went

    def to_dict(self) -> dict:
        return {
            "level_price": self.level.price,
            "level_type": self.level.type,
            "level_source": self.level.source,
            "sweep_direction": self.sweep_direction,
            "reversal_confirmed": self.reversal_confirmed,
            "session": self.session,
            "sweep_depth_pips": self.sweep_depth_pips,
            "sweep_candle_idx": self.sweep_candle_idx,
        }


def _get_pip_value(instrument: str) -> float:
    """Get pip value for instrument."""
    if "XAU" in instrument:
        return 0.1  # Gold
    if "BTC" in instrument or "ETH" in instrument:
        return 1.0
    if "JPY" in instrument:
        return 0.01
    return 0.0001


def map_liquidity(
    candles: List[Dict[str, Any]],
    swing_points: List[SwingPoint],
    instrument: str = "",
    equal_level_tolerance_pips: float = 3.0
) -> LiquidityMap:
    """
    Build a liquidity map from candle data and swing points.

    Identifies:
    - Equal highs (buyside liquidity)
    - Equal lows (sellside liquidity)
    - Swing highs as buyside targets
    - Swing lows as sellside targets

    Args:
        candles: OHLC candle data
        swing_points: Detected swing points
        instrument: Instrument name for pip value calculation
        equal_level_tolerance_pips: Tolerance for "equal" levels in pips

    Returns:
        LiquidityMap with all identified levels
    """
    pip_value = _get_pip_value(instrument)
    tolerance = equal_level_tolerance_pips * pip_value

    buyside = []
    sellside = []

    current_price = candles[-1]["close"] if candles else 0

    # 1. Swing highs → buyside liquidity
    swing_highs = [sp for sp in swing_points if sp.type == "HIGH"]
    for sp in swing_highs:
        buyside.append(LiquidityLevel(
            price=sp.price,
            type="BUYSIDE",
            source="SWING",
            strength=1,
        ))

    # 2. Swing lows → sellside liquidity
    swing_lows = [sp for sp in swing_points if sp.type == "LOW"]
    for sp in swing_lows:
        sellside.append(LiquidityLevel(
            price=sp.price,
            type="SELLSIDE",
            source="SWING",
            strength=1,
        ))

    # 3. Detect equal highs (buyside liquidity magnet)
    if len(candles) >= 10:
        highs = [(i, c["high"]) for i, c in enumerate(candles)]
        equal_high_groups = _find_equal_levels(highs, tolerance)
        for group in equal_high_groups:
            avg_price = sum(h for _, h in group) / len(group)
            buyside.append(LiquidityLevel(
                price=avg_price,
                type="BUYSIDE",
                source="EQUAL_HIGHS",
                strength=len(group),
            ))

    # 4. Detect equal lows (sellside liquidity magnet)
    if len(candles) >= 10:
        lows = [(i, c["low"]) for i, c in enumerate(candles)]
        equal_low_groups = _find_equal_levels(lows, tolerance)
        for group in equal_low_groups:
            avg_price = sum(l for _, l in group) / len(group)
            sellside.append(LiquidityLevel(
                price=avg_price,
                type="SELLSIDE",
                source="EQUAL_LOWS",
                strength=len(group),
            ))

    # Sort by price
    buyside.sort(key=lambda x: x.price)
    sellside.sort(key=lambda x: x.price, reverse=True)

    # Find nearest levels to current price
    nearest_buy = None
    for level in buyside:
        if level.price > current_price:
            nearest_buy = level
            break

    nearest_sell = None
    for level in sellside:
        if level.price < current_price:
            nearest_sell = level
            break

    return LiquidityMap(
        buyside=buyside,
        sellside=sellside,
        nearest_buyside=nearest_buy,
        nearest_sellside=nearest_sell,
    )


def _find_equal_levels(
    price_points: List[tuple],
    tolerance: float,
    min_count: int = 2
) -> List[List[tuple]]:
    """
    Find groups of price points that are within tolerance of each other.

    Args:
        price_points: List of (index, price) tuples
        tolerance: Maximum price difference to consider "equal"
        min_count: Minimum points to form a group

    Returns:
        List of groups, each group is a list of (index, price) tuples
    """
    if not price_points:
        return []

    groups = []
    used = set()

    sorted_points = sorted(price_points, key=lambda x: x[1])

    for i, (idx_i, price_i) in enumerate(sorted_points):
        if i in used:
            continue

        group = [(idx_i, price_i)]
        used.add(i)

        for j in range(i + 1, len(sorted_points)):
            if j in used:
                continue
            idx_j, price_j = sorted_points[j]
            if abs(price_j - price_i) <= tolerance:
                group.append((idx_j, price_j))
                used.add(j)
            else:
                break  # Sorted, so no more matches possible

        if len(group) >= min_count:
            groups.append(group)

    return groups


def detect_session_levels(
    candles: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Track session high/low for London, NY, and Asian sessions.

    Sessions (UTC):
    - Asian: 00:00-08:00
    - London: 07:00-16:00
    - NY: 12:00-21:00

    Args:
        candles: OHLC candle data with 'time' field

    Returns:
        Dict of session levels:
        {session_name: {high, low, high_idx, low_idx}}
    """
    sessions = {
        "asian": {"start": 0, "end": 8, "high": 0, "low": float("inf"),
                  "high_idx": -1, "low_idx": -1},
        "london": {"start": 7, "end": 16, "high": 0, "low": float("inf"),
                   "high_idx": -1, "low_idx": -1},
        "ny": {"start": 12, "end": 21, "high": 0, "low": float("inf"),
               "high_idx": -1, "low_idx": -1},
    }

    for i, candle in enumerate(candles):
        time_str = candle.get("time", "")
        try:
            if "T" in time_str:
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            else:
                continue
        except (ValueError, TypeError):
            continue

        hour = dt.hour

        for session_name, session in sessions.items():
            if session["start"] <= hour < session["end"]:
                if candle["high"] > session["high"]:
                    session["high"] = candle["high"]
                    session["high_idx"] = i
                if candle["low"] < session["low"]:
                    session["low"] = candle["low"]
                    session["low_idx"] = i

    # Clean up - remove sessions with no data
    result = {}
    for name, data in sessions.items():
        if data["high"] > 0 and data["low"] < float("inf"):
            result[name] = {
                "high": data["high"],
                "low": data["low"],
                "high_idx": data["high_idx"],
                "low_idx": data["low_idx"],
            }

    return result


def detect_sweep(
    candles: List[Dict[str, Any]],
    liquidity_map: LiquidityMap,
    session_levels: Dict[str, Dict],
    sweep_source: str = "london_ny",
    instrument: str = "",
    lookback_bars: int = 20
) -> Optional[LiquiditySweep]:
    """
    Detect a liquidity sweep in recent price action.

    A sweep occurs when:
    1. Price pierces beyond a liquidity level (wick goes past)
    2. Price closes back inside (reversal)
    3. This confirms institutional stop hunting

    Args:
        candles: OHLC candle data
        liquidity_map: Pre-built liquidity map
        session_levels: Session high/low data
        sweep_source: Which session sweep to look for
            - "london": sweep London session high/low
            - "london_ny": sweep London or NY session high/low
            - "any": sweep any session or swing high/low
        instrument: Instrument name
        lookback_bars: How many recent bars to check

    Returns:
        LiquiditySweep if detected, None otherwise
    """
    if len(candles) < 3:
        return None

    pip_value = _get_pip_value(instrument)
    min_sweep_pips = 1.0  # Minimum 1 pip penetration

    # Build list of levels to check based on sweep_source
    levels_to_check = []

    if sweep_source in ("london", "london_ny", "any"):
        if "london" in session_levels:
            sl = session_levels["london"]
            levels_to_check.append(LiquidityLevel(
                price=sl["high"], type="BUYSIDE", source="SESSION", strength=2
            ))
            levels_to_check.append(LiquidityLevel(
                price=sl["low"], type="SELLSIDE", source="SESSION", strength=2
            ))

    if sweep_source in ("london_ny", "any"):
        if "ny" in session_levels:
            sl = session_levels["ny"]
            levels_to_check.append(LiquidityLevel(
                price=sl["high"], type="BUYSIDE", source="SESSION", strength=2
            ))
            levels_to_check.append(LiquidityLevel(
                price=sl["low"], type="SELLSIDE", source="SESSION", strength=2
            ))

    if sweep_source == "any":
        if "asian" in session_levels:
            sl = session_levels["asian"]
            levels_to_check.append(LiquidityLevel(
                price=sl["high"], type="BUYSIDE", source="SESSION", strength=1
            ))
            levels_to_check.append(LiquidityLevel(
                price=sl["low"], type="SELLSIDE", source="SESSION", strength=1
            ))

    # Also check swing-based liquidity levels
    for level in liquidity_map.buyside + liquidity_map.sellside:
        if level.source in ("SWING", "EQUAL_HIGHS", "EQUAL_LOWS"):
            levels_to_check.append(level)

    # Check recent candles for sweeps (most recent first for priority)
    start_idx = max(0, len(candles) - lookback_bars)
    best_sweep = None

    for level in levels_to_check:
        for i in range(len(candles) - 1, start_idx, -1):
            candle = candles[i]

            if level.type == "BUYSIDE":
                # Buyside sweep: wick goes above level, close stays below
                if candle["high"] > level.price and candle["close"] < level.price:
                    sweep_depth = (candle["high"] - level.price) / pip_value
                    if sweep_depth >= min_sweep_pips:
                        # Check if next candle(s) confirm reversal (bearish)
                        reversal = False
                        if i + 1 < len(candles):
                            next_c = candles[i + 1]
                            reversal = next_c["close"] < next_c["open"]  # Bearish candle
                        elif candle["close"] < candle["open"]:
                            reversal = True  # Current candle is reversal

                        sweep = LiquiditySweep(
                            level=level,
                            sweep_candle_idx=i,
                            sweep_direction="BUYSIDE_SWEEP",
                            reversal_confirmed=reversal,
                            sweep_depth_pips=sweep_depth,
                        )
                        if best_sweep is None or i > best_sweep.sweep_candle_idx:
                            best_sweep = sweep

            elif level.type == "SELLSIDE":
                # Sellside sweep: wick goes below level, close stays above
                if candle["low"] < level.price and candle["close"] > level.price:
                    sweep_depth = (level.price - candle["low"]) / pip_value
                    if sweep_depth >= min_sweep_pips:
                        reversal = False
                        if i + 1 < len(candles):
                            next_c = candles[i + 1]
                            reversal = next_c["close"] > next_c["open"]  # Bullish candle
                        elif candle["close"] > candle["open"]:
                            reversal = True

                        sweep = LiquiditySweep(
                            level=level,
                            sweep_candle_idx=i,
                            sweep_direction="SELLSIDE_SWEEP",
                            reversal_confirmed=reversal,
                            sweep_depth_pips=sweep_depth,
                        )
                        if best_sweep is None or i > best_sweep.sweep_candle_idx:
                            best_sweep = sweep

    return best_sweep
