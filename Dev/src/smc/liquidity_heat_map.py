"""
Liquidity Heat Map - Predictive liquidity density scoring.

Instead of waiting for a sweep to happen, PREDICTS where sweeps
are most likely to occur based on:

1. Existing liquidity levels (buyside/sellside)
2. Session highs/lows (London/NY/Asian)
3. Equal highs/lows strength
4. Temporal decay (older levels = less relevant)
5. Touch count (more tests = more stop-losses clustered)

Output: sweep_direction_probability (0-1) and primary target level.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict

from src.utils.logger import logger


@dataclass
class HeatMapLevel:
    """A level on the heat map with estimated density."""
    price: float
    type: str  # BUYSIDE / SELLSIDE
    density_score: float  # 0-100
    sources: List[str] = field(default_factory=list)
    touch_count: int = 1
    age_hours: float = 0.0
    temporal_weight: float = 1.0
    estimated_attraction: float = 0.0  # How "magnetic" for institutions

    def to_dict(self) -> dict:
        return {
            "price": self.price,
            "type": self.type,
            "density_score": round(self.density_score, 1),
            "sources": self.sources,
            "touch_count": self.touch_count,
            "age_hours": round(self.age_hours, 1),
            "temporal_weight": round(self.temporal_weight, 3),
            "estimated_attraction": round(self.estimated_attraction, 1),
        }


@dataclass
class LiquidityHeatMap:
    """Predictive liquidity map."""
    buyside_levels: List[HeatMapLevel] = field(default_factory=list)
    sellside_levels: List[HeatMapLevel] = field(default_factory=list)
    buyside_total_density: float = 0.0
    sellside_total_density: float = 0.0
    sweep_direction_probability: float = 0.5  # P(sellside sweep) = bullish reversal
    primary_target: Optional[HeatMapLevel] = None
    temporal_bias: str = "BALANCED"  # BUYSIDE_HEAVY / SELLSIDE_HEAVY / BALANCED

    def to_dict(self) -> dict:
        return {
            "buyside_density": round(self.buyside_total_density, 1),
            "sellside_density": round(self.sellside_total_density, 1),
            "sweep_direction_prob": round(self.sweep_direction_probability, 3),
            "temporal_bias": self.temporal_bias,
            "primary_target": self.primary_target.to_dict() if self.primary_target else None,
            "buyside_levels": len(self.buyside_levels),
            "sellside_levels": len(self.sellside_levels),
        }


# Session level weights (importance for stop-loss clustering)
SESSION_WEIGHTS = {
    "london_high": 3.0,
    "london_low": 3.0,
    "ny_high": 2.5,
    "ny_low": 2.5,
    "asian_high": 2.0,
    "asian_low": 2.0,
}

EQUAL_LEVEL_WEIGHT = 3.0
SWING_WEIGHT = 1.5
DECAY_RATE = 0.05  # Exponential decay per hour


class LiquidityHeatMapper:
    """Builds predictive liquidity heat maps."""

    def build(
        self,
        h1_candles: List[Dict],
        liquidity_map,
        session_levels: Dict,
        instrument: str,
        current_price: Optional[float] = None,
    ) -> LiquidityHeatMap:
        """
        Build heat map combining all liquidity sources.

        Args:
            h1_candles: H1 candle data for timing
            liquidity_map: LiquidityMap from SMC HTF analysis
            session_levels: Session levels dict
            instrument: Instrument symbol
            current_price: Current price (for distance calc)

        Returns:
            LiquidityHeatMap with scored levels
        """
        heat_map = LiquidityHeatMap()
        now = datetime.now(timezone.utc)

        if current_price is None and h1_candles:
            current_price = h1_candles[-1]["close"]

        # 1. Score levels from LiquidityMap
        if liquidity_map:
            for level in getattr(liquidity_map, 'buyside', []):
                if level.swept:
                    continue  # Already swept, no longer relevant
                hm_level = self._score_liquidity_level(level, "BUYSIDE", now, h1_candles)
                heat_map.buyside_levels.append(hm_level)

            for level in getattr(liquidity_map, 'sellside', []):
                if level.swept:
                    continue
                hm_level = self._score_liquidity_level(level, "SELLSIDE", now, h1_candles)
                heat_map.sellside_levels.append(hm_level)

        # 2. Add session levels
        self._add_session_levels(heat_map, session_levels, current_price, now)

        # 3. Calculate total densities
        heat_map.buyside_total_density = sum(
            l.density_score for l in heat_map.buyside_levels
        )
        heat_map.sellside_total_density = sum(
            l.density_score for l in heat_map.sellside_levels
        )

        # 4. Determine temporal bias
        total = heat_map.buyside_total_density + heat_map.sellside_total_density
        if total > 0:
            buy_ratio = heat_map.buyside_total_density / total
            if buy_ratio > 0.6:
                heat_map.temporal_bias = "BUYSIDE_HEAVY"
            elif buy_ratio < 0.4:
                heat_map.temporal_bias = "SELLSIDE_HEAVY"
            else:
                heat_map.temporal_bias = "BALANCED"

        # 5. Predict sweep direction
        htf_bias = self._infer_htf_bias(h1_candles) if h1_candles else "NEUTRAL"
        heat_map.sweep_direction_probability = self._predict_sweep_direction(
            heat_map.buyside_total_density,
            heat_map.sellside_total_density,
            htf_bias,
        )

        # 6. Find primary target
        heat_map.primary_target = self._find_primary_target(
            heat_map.buyside_levels + heat_map.sellside_levels,
            current_price,
        )

        return heat_map

    def _score_liquidity_level(self, level, level_type, now, h1_candles) -> HeatMapLevel:
        """Score a liquidity level based on density factors."""
        sources = [level.source]
        touch_count = level.strength

        # Estimate age from candle data (approximate)
        age_hours = 24.0  # Default
        if h1_candles and len(h1_candles) > 0:
            # Rough estimate: each H1 candle = 1 hour
            age_hours = min(len(h1_candles), 100)

        temporal_weight = self._temporal_decay(age_hours)

        # Base density from touch count and source
        if level.source == "EQUAL_HIGHS" or level.source == "EQUAL_LOWS":
            base_density = EQUAL_LEVEL_WEIGHT * touch_count
        elif level.source == "SESSION":
            base_density = SESSION_WEIGHTS.get("london_high", 2.0) * touch_count
        else:
            base_density = SWING_WEIGHT * touch_count

        density = base_density * temporal_weight
        attraction = density * (1.0 + touch_count * 0.5)

        return HeatMapLevel(
            price=level.price,
            type=level_type,
            density_score=round(density, 1),
            sources=sources,
            touch_count=touch_count,
            age_hours=age_hours,
            temporal_weight=temporal_weight,
            estimated_attraction=round(attraction, 1),
        )

    def _add_session_levels(self, heat_map, session_levels, current_price, now):
        """Add session highs/lows to heat map."""
        if not session_levels or not current_price:
            return

        for session_key, weight in SESSION_WEIGHTS.items():
            price = session_levels.get(session_key)
            if price is None or price == 0:
                continue

            # Determine if buyside or sellside
            if price > current_price:
                level_type = "BUYSIDE"
            else:
                level_type = "SELLSIDE"

            # Session levels are recent (within 24h)
            age_hours = 12.0  # Average
            temporal_weight = self._temporal_decay(age_hours)

            density = weight * temporal_weight
            attraction = density * 1.5  # Session levels are important

            hm_level = HeatMapLevel(
                price=price,
                type=level_type,
                density_score=round(density, 1),
                sources=[session_key.upper()],
                touch_count=1,
                age_hours=age_hours,
                temporal_weight=temporal_weight,
                estimated_attraction=round(attraction, 1),
            )

            if level_type == "BUYSIDE":
                heat_map.buyside_levels.append(hm_level)
            else:
                heat_map.sellside_levels.append(hm_level)

    def _temporal_decay(self, age_hours: float) -> float:
        """Exponential decay based on age."""
        return math.exp(-DECAY_RATE * age_hours)

    def _predict_sweep_direction(
        self,
        buyside_density: float,
        sellside_density: float,
        htf_bias: str,
    ) -> float:
        """
        Predict sweep direction probability.

        Returns: P(sellside sweep first) = probability of bullish reversal.
        Higher = more likely sellside gets swept (bullish setup).
        """
        total = buyside_density + sellside_density
        if total == 0:
            base = 0.5
        else:
            # More sellside density → more likely it gets targeted
            base = sellside_density / total

        # Adjust for HTF bias
        if htf_bias == "BULLISH":
            base = min(1.0, base + 0.1)  # More likely sellside sweep → bull
        elif htf_bias == "BEARISH":
            base = max(0.0, base - 0.1)  # More likely buyside sweep → bear

        return max(0.0, min(1.0, base))

    def _find_primary_target(
        self,
        all_levels: List[HeatMapLevel],
        current_price: Optional[float],
    ) -> Optional[HeatMapLevel]:
        """Find the strongest nearest level as primary sweep target."""
        if not all_levels or not current_price:
            return None

        # Score by density * proximity
        best = None
        best_score = -1.0

        for level in all_levels:
            distance = abs(level.price - current_price)
            if distance == 0:
                continue
            # Closer + denser = more attractive target
            proximity_score = 1.0 / (1.0 + distance / current_price * 1000)
            combined = level.density_score * proximity_score
            if combined > best_score:
                best_score = combined
                best = level

        return best

    def _infer_htf_bias(self, h1_candles: List[Dict]) -> str:
        """Simple HTF bias inference from H1 candles."""
        if not h1_candles or len(h1_candles) < 10:
            return "NEUTRAL"
        # Use last 20 candles
        recent = h1_candles[-20:]
        closes = [c["close"] for c in recent]
        if len(closes) < 2:
            return "NEUTRAL"
        # Simple: compare first half to second half
        mid = len(closes) // 2
        first_avg = sum(closes[:mid]) / mid
        second_avg = sum(closes[mid:]) / (len(closes) - mid)
        diff_pct = (second_avg - first_avg) / first_avg * 100
        if diff_pct > 0.1:
            return "BULLISH"
        elif diff_pct < -0.1:
            return "BEARISH"
        return "NEUTRAL"
