"""
SMC Analyzer - Main orchestrator for Smart Money Concepts analysis.

Combines all SMC components into a single analysis pipeline:
1. HTF Bias (H4/H1): structure + liquidity map
2. LTF Signal (M5): sweep + CHoCH/BOS + FVG + displacement
3. Setup Grading: A+/A/B/NO_TRADE
4. Entry/SL/TP calculation based on SMC zones
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from src.smc.structure import (
    SwingPoint, StructureShift,
    detect_swing_points, classify_structure, detect_choch, detect_bos
)
from src.smc.liquidity import (
    LiquidityMap, LiquiditySweep,
    map_liquidity, detect_session_levels, detect_sweep
)
from src.smc.zones import (
    FairValueGap, OrderBlock,
    detect_fvg, detect_order_blocks, calculate_premium_discount
)
from src.smc.displacement import Displacement, detect_displacement
from src.smc.liquidity_heat_map import LiquidityHeatMapper, LiquidityHeatMap
from src.utils.instrument_profiles import get_profile
from src.utils.logger import logger


@dataclass
class SMCAnalysis:
    """Complete SMC analysis result."""

    # HTF Bias
    htf_bias: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    htf_structure: str = "RANGING"  # HH_HL, LH_LL, RANGING
    htf_swing_high: float = 0.0
    htf_swing_low: float = 0.0

    # Liquidity
    liquidity_map: Optional[LiquidityMap] = None
    session_levels: Dict = field(default_factory=dict)
    sweep_detected: Optional[LiquiditySweep] = None

    # LTF Signal
    ltf_structure: str = "RANGING"
    ltf_choch: Optional[StructureShift] = None
    ltf_bos: Optional[StructureShift] = None
    ltf_displacement: Optional[Displacement] = None

    # Entry Zones
    fvgs: List[FairValueGap] = field(default_factory=list)
    order_blocks: List[OrderBlock] = field(default_factory=list)
    premium_discount: Dict = field(default_factory=dict)

    # Setup Grade
    setup_grade: str = "NO_TRADE"  # "A+", "A", "B", "NO_TRADE"
    grade_reasons: List[str] = field(default_factory=list)
    confidence: int = 0  # 0-100 mapped from grade

    # Direction
    direction: Optional[str] = None  # LONG, SHORT, None
    current_price: float = 0.0  # Current price at analysis time

    # Entry/SL/TP (SMC-based)
    entry_zone: Optional[tuple] = None  # (low, high) of entry zone
    stop_loss: Optional[float] = None  # Behind sweep/inducement
    take_profit: Optional[float] = None  # At next liquidity level
    risk_reward: Optional[float] = None

    # ISI: Liquidity Heat Map
    heat_map: Optional[Any] = None  # LiquidityHeatMap data
    sweep_direction_probability: float = 0.5

    def to_dict(self) -> dict:
        return {
            "htf_bias": self.htf_bias,
            "htf_structure": self.htf_structure,
            "htf_swing_high": self.htf_swing_high,
            "htf_swing_low": self.htf_swing_low,
            "liquidity_map": self.liquidity_map.to_dict() if self.liquidity_map else None,
            "session_levels": self.session_levels,
            "sweep_detected": self.sweep_detected.to_dict() if self.sweep_detected else None,
            "ltf_structure": self.ltf_structure,
            "ltf_choch": self.ltf_choch.to_dict() if self.ltf_choch else None,
            "ltf_bos": self.ltf_bos.to_dict() if self.ltf_bos else None,
            "ltf_displacement": self.ltf_displacement.to_dict() if self.ltf_displacement else None,
            "fvg_count": len(self.fvgs),
            "ob_count": len(self.order_blocks),
            "premium_discount": self.premium_discount,
            "setup_grade": self.setup_grade,
            "grade_reasons": self.grade_reasons,
            "confidence": self.confidence,
            "direction": self.direction,
            "entry_zone": self.entry_zone,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_reward": self.risk_reward,
            "heat_map": self.heat_map.to_dict() if self.heat_map else None,
            "sweep_direction_probability": self.sweep_direction_probability,
        }


class SMCAnalyzer:
    """
    Main SMC analysis orchestrator.

    Pipeline:
    1. analyze_htf() - H4/H1 structure + liquidity
    2. analyze_ltf() - M5 sweep + structure shift + zones
    3. grade_setup() - Grade the setup quality
    4. calculate_sl_tp() - SMC-based SL/TP
    """

    def analyze_htf(
        self,
        h4_candles: List[Dict],
        h1_candles: List[Dict],
        instrument: str
    ) -> Dict[str, Any]:
        """
        Step 1+2: Determine HTF bias and build liquidity map.

        Uses H4 for overall structure and H1 for finer detail.

        Args:
            h4_candles: H4 OHLC data
            h1_candles: H1 OHLC data
            instrument: Instrument symbol

        Returns:
            Dict with htf_bias, htf_structure, liquidity_map, session_levels, swing points
        """
        result = {
            "htf_bias": "NEUTRAL",
            "htf_structure": "RANGING",
            "htf_swing_high": 0.0,
            "htf_swing_low": 0.0,
            "liquidity_map": LiquidityMap(),
            "session_levels": {},
            "h4_swing_points": [],
            "h1_swing_points": [],
        }

        # H4 structure analysis (broad view)
        if len(h4_candles) >= 20:
            h4_swings = detect_swing_points(h4_candles, left_bars=5, right_bars=2)
            h4_structure = classify_structure(h4_swings)
            result["h4_swing_points"] = h4_swings
            result["htf_structure"] = h4_structure

            # Determine bias
            if h4_structure == "HH_HL":
                result["htf_bias"] = "BULLISH"
            elif h4_structure == "LH_LL":
                result["htf_bias"] = "BEARISH"
            else:
                result["htf_bias"] = "NEUTRAL"

            # Get swing high/low
            highs = [sp for sp in h4_swings if sp.type == "HIGH"]
            lows = [sp for sp in h4_swings if sp.type == "LOW"]
            if highs:
                result["htf_swing_high"] = max(sp.price for sp in highs)
            if lows:
                result["htf_swing_low"] = min(sp.price for sp in lows)

        # H1 liquidity map
        if len(h1_candles) >= 20:
            h1_swings = detect_swing_points(h1_candles, left_bars=5, right_bars=2)
            result["h1_swing_points"] = h1_swings

            # Build liquidity map from H1
            result["liquidity_map"] = map_liquidity(
                h1_candles, h1_swings, instrument
            )

            # Session levels from H1
            result["session_levels"] = detect_session_levels(h1_candles)

            # If H4 didn't provide enough data, use H1 structure
            if result["htf_bias"] == "NEUTRAL" and len(h1_swings) >= 4:
                h1_structure = classify_structure(h1_swings)
                if h1_structure != "RANGING":
                    result["htf_structure"] = h1_structure
                    result["htf_bias"] = "BULLISH" if h1_structure == "HH_HL" else "BEARISH"

                if not result["htf_swing_high"]:
                    h1_highs = [sp for sp in h1_swings if sp.type == "HIGH"]
                    if h1_highs:
                        result["htf_swing_high"] = max(sp.price for sp in h1_highs)
                if not result["htf_swing_low"]:
                    h1_lows = [sp for sp in h1_swings if sp.type == "LOW"]
                    if h1_lows:
                        result["htf_swing_low"] = min(sp.price for sp in h1_lows)

        # ISI: Build liquidity heat map
        heat_mapper = LiquidityHeatMapper()
        result["heat_map"] = heat_mapper.build(
            h1_candles, result["liquidity_map"],
            result["session_levels"], instrument,
        )

        logger.info(
            f"HTF Analysis: bias={result['htf_bias']}, "
            f"structure={result['htf_structure']}, "
            f"buyside={len(result['liquidity_map'].buyside)}, "
            f"sellside={len(result['liquidity_map'].sellside)}, "
            f"heat_map_bias={result['heat_map'].temporal_bias}"
        )

        return result

    def analyze_ltf(
        self,
        m5_candles: List[Dict],
        htf_result: Dict[str, Any],
        instrument: str
    ) -> SMCAnalysis:
        """
        Steps 3-7: LTF analysis - sweep, structure shift, zones, grading.

        Args:
            m5_candles: M5 OHLC data
            htf_result: Result from analyze_htf()
            instrument: Instrument symbol

        Returns:
            Complete SMCAnalysis
        """
        profile = get_profile(instrument)
        sweep_source = profile.get("session_sweep_source", "london_ny")

        analysis = SMCAnalysis(
            htf_bias=htf_result["htf_bias"],
            htf_structure=htf_result["htf_structure"],
            htf_swing_high=htf_result["htf_swing_high"],
            htf_swing_low=htf_result["htf_swing_low"],
            liquidity_map=htf_result["liquidity_map"],
            session_levels=htf_result["session_levels"],
            heat_map=htf_result.get("heat_map"),
            sweep_direction_probability=(
                htf_result["heat_map"].sweep_direction_probability
                if htf_result.get("heat_map") else 0.5
            ),
        )

        if len(m5_candles) < 30:
            analysis.setup_grade = "NO_TRADE"
            analysis.grade_reasons = ["Insufficient M5 data"]
            return analysis

        # Step 3: Detect liquidity sweep
        analysis.sweep_detected = detect_sweep(
            m5_candles,
            htf_result["liquidity_map"],
            htf_result["session_levels"],
            sweep_source=sweep_source,
            instrument=instrument,
        )

        # Step 4: LTF structure analysis
        ltf_swings = detect_swing_points(m5_candles, left_bars=3, right_bars=2)
        analysis.ltf_structure = classify_structure(ltf_swings)

        # Detect CHoCH and BOS on M5
        analysis.ltf_choch = detect_choch(m5_candles, ltf_swings)
        analysis.ltf_bos = detect_bos(m5_candles, ltf_swings)

        # Step 5: Detect displacement
        displacements = detect_displacement(m5_candles, min_ratio=2.0, lookback=20)
        if displacements:
            # Use most recent displacement
            analysis.ltf_displacement = displacements[-1]

        # Step 6: Detect FVGs and Order Blocks
        analysis.fvgs = detect_fvg(m5_candles)
        analysis.order_blocks = detect_order_blocks(m5_candles)

        # Step 7: Premium/Discount
        if analysis.htf_swing_high > 0 and analysis.htf_swing_low > 0:
            current_price = m5_candles[-1]["close"]
            analysis.premium_discount = calculate_premium_discount(
                analysis.htf_swing_high,
                analysis.htf_swing_low,
                current_price,
            )

        # Store current price for entry zone proximity check
        analysis.current_price = m5_candles[-1]["close"]

        # Determine direction from SMC confluence
        candidate_direction = self._candidate_direction_from_sweep(analysis)
        analysis.direction = self._determine_smc_direction(analysis)

        # Grade the setup
        analysis.setup_grade = self.grade_setup(analysis, instrument)

        # Map grade to confidence
        grade_confidence = {
            "A+": 92,
            "A": 82,
            "B": 68,
            "NO_TRADE": 30,
        }
        analysis.confidence = grade_confidence.get(analysis.setup_grade, 30)

        # Calculate SL/TP if we have a valid setup
        if analysis.direction and analysis.setup_grade != "NO_TRADE":
            self._calculate_sl_tp(analysis, m5_candles, instrument)

        logger.info(
            f"LTF Analysis: sweep={'YES' if analysis.sweep_detected else 'NO'}, "
            f"choch={'YES' if analysis.ltf_choch else 'NO'}, "
            f"bos={'YES' if analysis.ltf_bos else 'NO'}, "
            f"displacement={'YES' if analysis.ltf_displacement else 'NO'}, "
            f"fvgs_detected={len(analysis.fvgs)}, "
            f"fvgs_valid_strict=0, "
            f"candidate_direction={candidate_direction}, "
            f"confirmed_direction={analysis.direction if analysis.direction else 'NONE'}, "
            f"obs={len(analysis.order_blocks)}, "
            f"grade={analysis.setup_grade}, direction={analysis.direction}"
        )

        return analysis

    def _candidate_direction_from_sweep(self, analysis: SMCAnalysis) -> str:
        """Directional candidate before HTF-aligned confirmation."""
        if not analysis.sweep_detected:
            return "NONE"
        if analysis.sweep_detected.sweep_direction == "SELLSIDE_SWEEP":
            return "LONG"
        if analysis.sweep_detected.sweep_direction == "BUYSIDE_SWEEP":
            return "SHORT"
        return "NONE"

    def _determine_smc_direction(self, analysis: SMCAnalysis) -> Optional[str]:
        """
        Determine trade direction from SMC confluence.

        Logic:
        - Sellside sweep + bullish CHoCH/BOS = LONG
        - Buyside sweep + bearish CHoCH/BOS = SHORT
        - Must align with HTF bias
        """
        sweep = analysis.sweep_detected
        choch = analysis.ltf_choch
        bos = analysis.ltf_bos

        # No sweep = no trade direction
        if not sweep:
            return None

        # Determine direction from sweep + structure
        sweep_direction = None

        if sweep.sweep_direction == "SELLSIDE_SWEEP":
            # Sellside swept (stops below taken out) → expect LONG
            # Need bullish CHoCH or BOS to confirm
            if choch and choch.direction == "BULLISH":
                sweep_direction = "LONG"
            elif bos and bos.direction == "BULLISH":
                sweep_direction = "LONG"

        elif sweep.sweep_direction == "BUYSIDE_SWEEP":
            # Buyside swept (stops above taken out) → expect SHORT
            if choch and choch.direction == "BEARISH":
                sweep_direction = "SHORT"
            elif bos and bos.direction == "BEARISH":
                sweep_direction = "SHORT"

        if not sweep_direction:
            return None

        # Check HTF alignment
        htf = analysis.htf_bias
        if htf == "NEUTRAL":
            # Neutral HTF - still allow trade but will be graded lower
            return sweep_direction

        # HTF opposes direction → no trade
        if (htf == "BULLISH" and sweep_direction == "SHORT") or \
           (htf == "BEARISH" and sweep_direction == "LONG"):
            analysis.grade_reasons.append(
                f"HTF {htf} opposes LTF {sweep_direction}"
            )
            return None

        return sweep_direction

    def _check_entry_zone_proximity(
        self, current_price: float, entry_zone: tuple,
        direction: str, pip_value: float
    ) -> tuple:
        """
        Check if current price is near the optimal entry zone (FVG/OB).

        Returns:
            (in_zone: bool, reason: str, confidence_modifier: int)
        """
        zone_low, zone_high = entry_zone
        zone_mid = (zone_low + zone_high) / 2

        if direction == "LONG":
            # For longs, we want price near or in the FVG/OB below
            if zone_low <= current_price <= zone_high:
                return True, "Price inside entry zone", 10
            dist_pips = abs(current_price - zone_mid) / pip_value
            if dist_pips <= 5:
                return False, f"Price near entry zone ({dist_pips:.1f} pips)", 5
            if dist_pips > 10:
                return False, f"Price far from entry zone ({dist_pips:.1f} pips)", -15
        else:
            # For shorts, we want price near or in the FVG/OB above
            if zone_low <= current_price <= zone_high:
                return True, "Price inside entry zone", 10
            dist_pips = abs(current_price - zone_mid) / pip_value
            if dist_pips <= 5:
                return False, f"Price near entry zone ({dist_pips:.1f} pips)", 5
            if dist_pips > 10:
                return False, f"Price far from entry zone ({dist_pips:.1f} pips)", -15

        return False, "Price at moderate distance from entry zone", 0

    def grade_setup(self, analysis: SMCAnalysis, instrument: str = "") -> str:
        """
        Grade the setup quality based on SMC criteria.

        A+ (92 conf): All elements present and aligned
        A  (82 conf): Missing one non-critical element
        B  (68 conf): Multiple elements weaker
        NO_TRADE (30): Missing critical element
        """
        reasons = list(analysis.grade_reasons)  # Preserve existing reasons
        score = 0

        # === HARD GATES (NO_TRADE if missing) ===

        # Gate 1: Must have sweep
        if analysis.sweep_detected:
            score += 25
            reasons.append("Sweep detected")
            if analysis.sweep_detected.reversal_confirmed:
                score += 5
                reasons.append("Sweep reversal confirmed")
        else:
            reasons.append("NO SWEEP - cannot trade")
            analysis.grade_reasons = reasons
            return "NO_TRADE"

        # Gate 2: Must have CHoCH or BOS
        has_structure_shift = analysis.ltf_choch or analysis.ltf_bos
        if has_structure_shift:
            score += 20
            if analysis.ltf_choch:
                reasons.append(f"CHoCH {analysis.ltf_choch.direction}")
            if analysis.ltf_bos:
                reasons.append(f"BOS {analysis.ltf_bos.direction}")
        else:
            reasons.append("NO CHoCH/BOS - cannot trade")
            analysis.grade_reasons = reasons
            return "NO_TRADE"

        # Gate 3: Must have direction
        if not analysis.direction:
            reasons.append("No clear direction")
            analysis.grade_reasons = reasons
            return "NO_TRADE"

        # === QUALITY FACTORS ===

        # HTF alignment
        if analysis.htf_bias != "NEUTRAL":
            if (analysis.htf_bias == "BULLISH" and analysis.direction == "LONG") or \
               (analysis.htf_bias == "BEARISH" and analysis.direction == "SHORT"):
                score += 15
                reasons.append(f"HTF aligned ({analysis.htf_bias})")
        else:
            reasons.append("HTF neutral (weaker setup)")

        # Displacement
        if analysis.ltf_displacement:
            disp = analysis.ltf_displacement
            if (analysis.direction == "LONG" and disp.direction == "BULLISH") or \
               (analysis.direction == "SHORT" and disp.direction == "BEARISH"):
                score += 10
                reasons.append(f"Displacement {disp.direction} ({disp.avg_body_ratio:.1f}x)")

        # FVG in direction
        relevant_fvgs = [
            f for f in analysis.fvgs
            if not f.filled and (
                (analysis.direction == "LONG" and f.direction == "BULLISH") or
                (analysis.direction == "SHORT" and f.direction == "BEARISH")
            )
        ]
        if relevant_fvgs:
            score += 10
            reasons.append(f"{len(relevant_fvgs)} unfilled FVG(s)")

        # Order Block in direction
        relevant_obs = [
            ob for ob in analysis.order_blocks
            if not ob.mitigated and (
                (analysis.direction == "LONG" and ob.direction == "BULLISH") or
                (analysis.direction == "SHORT" and ob.direction == "BEARISH")
            )
        ]
        if relevant_obs:
            score += 10
            reasons.append(f"{len(relevant_obs)} fresh OB(s)")

        # Premium/Discount alignment
        pd = analysis.premium_discount
        if pd:
            zone = pd.get("zone", "UNKNOWN")
            if (analysis.direction == "LONG" and zone == "DISCOUNT") or \
               (analysis.direction == "SHORT" and zone == "PREMIUM"):
                score += 10
                reasons.append(f"Price in {zone} zone ({pd.get('percentage', 50):.0f}%)")
            elif zone == "EQUILIBRIUM":
                reasons.append("Price in equilibrium (weaker)")
                score -= 5

        # Entry zone proximity check
        if analysis.direction and analysis.current_price > 0 and instrument:
            # Find entry zone for proximity check
            entry_zone = self._find_entry_zone(analysis, analysis.direction, analysis.current_price)
            if entry_zone:
                pip_value = self._get_pip_value(instrument)
                in_zone, prox_reason, prox_modifier = self._check_entry_zone_proximity(
                    analysis.current_price, entry_zone, analysis.direction, pip_value
                )
                score += prox_modifier
                reasons.append(prox_reason)

        # === FINAL GRADE ===
        analysis.grade_reasons = reasons

        if score >= 80:
            return "A+"
        elif score >= 60:
            return "A"
        elif score >= 45:
            return "B"
        else:
            return "NO_TRADE"

    def _calculate_sl_tp(
        self,
        analysis: SMCAnalysis,
        m5_candles: List[Dict],
        instrument: str
    ) -> None:
        """
        Calculate SL and TP based on SMC zones.

        SL: Behind the sweep level (gives room for the liquidity grab)
        TP: At next opposing liquidity level
        """
        if not analysis.sweep_detected or not analysis.direction:
            return

        profile = get_profile(instrument)
        pip_value = self._get_pip_value(instrument)
        max_sl_pips = profile.get("max_sl_pips", 30.0)
        min_sl_pips = profile.get("min_sl_pips", 12.0)
        sl_atr_mult = profile.get("sl_atr_multiplier", 1.5)
        min_rr = profile.get("target_rr", 2.0)

        # Dynamic SL buffer based on ATR
        atr_value = self._calculate_atr_from_candles(m5_candles)
        atr_pips = atr_value / pip_value if atr_value > 0 else 0
        dynamic_buffer = max(min_sl_pips, atr_pips * sl_atr_mult) if atr_pips > 0 else min_sl_pips
        sl_buffer = dynamic_buffer * pip_value

        current_price = m5_candles[-1]["close"]
        sweep = analysis.sweep_detected
        liq_map = analysis.liquidity_map
        heat_map = analysis.heat_map

        if analysis.direction == "LONG":
            # SL behind the sweep low (sellside was swept)
            sl_reference = sweep.level.price
            sl = sl_reference - sl_buffer

            # Cap SL distance
            sl_distance_pips = (current_price - sl) / pip_value
            if sl_distance_pips > max_sl_pips:
                sl = current_price - (max_sl_pips * pip_value)
                sl_distance_pips = max_sl_pips

            # TP at nearest buyside liquidity (heat map preferred)
            tp = None
            heat_map = analysis.heat_map
            if heat_map and heat_map.buyside_levels:
                # Use strongest buyside level as TP target
                best = max(heat_map.buyside_levels, key=lambda l: l.density_score)
                if best.price > current_price:
                    tp = best.price
            if not tp and liq_map and liq_map.nearest_buyside:
                tp = liq_map.nearest_buyside.price
            # Fallback: use min R:R
            if not tp or tp <= current_price:
                sl_distance = current_price - sl
                tp = current_price + (sl_distance * min_rr)

            # Entry zone: nearest bullish FVG or OB
            entry_zone = self._find_entry_zone(analysis, "LONG", current_price)
            analysis.entry_zone = entry_zone

        else:  # SHORT
            # SL behind the sweep high (buyside was swept)
            sl_reference = sweep.level.price
            sl = sl_reference + sl_buffer

            sl_distance_pips = (sl - current_price) / pip_value
            if sl_distance_pips > max_sl_pips:
                sl = current_price + (max_sl_pips * pip_value)
                sl_distance_pips = max_sl_pips

            tp = None
            if heat_map and heat_map.sellside_levels:
                best = max(heat_map.sellside_levels, key=lambda l: l.density_score)
                if best.price < current_price:
                    tp = best.price
            if not tp and liq_map and liq_map.nearest_sellside:
                tp = liq_map.nearest_sellside.price
            if not tp or tp >= current_price:
                sl_distance = sl - current_price
                tp = current_price - (sl_distance * min_rr)

            entry_zone = self._find_entry_zone(analysis, "SHORT", current_price)
            analysis.entry_zone = entry_zone

        analysis.stop_loss = round(sl, 5)
        analysis.take_profit = round(tp, 5)

        # Calculate R:R
        risk = abs(current_price - sl)
        reward = abs(tp - current_price)
        analysis.risk_reward = round(reward / risk, 2) if risk > 0 else 0

    def _find_entry_zone(
        self,
        analysis: SMCAnalysis,
        direction: str,
        current_price: float
    ) -> Optional[tuple]:
        """Find the best entry zone from FVGs and OBs."""
        # Look for unfilled FVGs in direction
        for fvg in analysis.fvgs:
            if fvg.filled:
                continue
            if direction == "LONG" and fvg.direction == "BULLISH":
                return (min(fvg.start_price, fvg.end_price),
                        max(fvg.start_price, fvg.end_price))
            if direction == "SHORT" and fvg.direction == "BEARISH":
                return (min(fvg.start_price, fvg.end_price),
                        max(fvg.start_price, fvg.end_price))

        # Look for fresh Order Blocks
        for ob in analysis.order_blocks:
            if ob.mitigated:
                continue
            if direction == "LONG" and ob.direction == "BULLISH":
                return (ob.low, ob.high)
            if direction == "SHORT" and ob.direction == "BEARISH":
                return (ob.low, ob.high)

        return None

    def _calculate_atr_from_candles(self, candles: list, period: int = 14) -> float:
        """
        Calculate ATR (Average True Range) from candle data.

        Uses simple manual calculation (no external deps).
        Returns 0.0 if insufficient data.
        """
        if len(candles) < period + 1:
            return 0.0

        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return 0.0

        # Simple moving average of last `period` true ranges
        return sum(true_ranges[-period:]) / period

    def _get_pip_value(self, instrument: str) -> float:
        """Get pip value for an instrument."""
        if "XAU" in instrument:
            return 0.1
        if "BTC" in instrument or "ETH" in instrument:
            return 1.0
        if "JPY" in instrument:
            return 0.01
        return 0.0001
