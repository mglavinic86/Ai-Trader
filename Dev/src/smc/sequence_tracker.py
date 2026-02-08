"""
Sequence Tracker - Tracks institutional cycle phases per instrument.

Instead of point-in-time scoring, tracks WHERE in the institutional
cycle an instrument currently sits:

Phase 1: ACCUMULATION  - Range, tight BB, low ADX
Phase 2: MANIPULATION  - Liquidity sweep (false breakout)
Phase 3: DISPLACEMENT  - Impulsive move, BOS/CHoCH
Phase 4: RETRACEMENT   - Pullback into FVG/OB → OPTIMAL ENTRY
Phase 5: CONTINUATION  - Continuation in displacement direction

Confidence modifiers:
  Phase 1: -20 (don't trade, wait)
  Phase 2: -10 (sweep in progress, early)
  Phase 3:  +5 (confirmation, but late for entry)
  Phase 4: +15 (OPTIMAL ENTRY!)
  Phase 5:  +0 (ok but riskier)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.utils.logger import logger


PHASES = {
    1: "ACCUMULATION",
    2: "MANIPULATION",
    3: "DISPLACEMENT",
    4: "RETRACEMENT",
    5: "CONTINUATION",
}

PHASE_CONFIDENCE_MODIFIERS = {
    1: -20,  # Don't trade
    2: -10,  # Sweep in progress
    3:  +5,  # Confirmation but late
    4: +15,  # OPTIMAL ENTRY
    5:   0,  # OK but riskier
}


@dataclass
class SequenceState:
    """State of the institutional cycle for one instrument."""
    instrument: str
    current_phase: int = 1
    phase_name: str = "ACCUMULATION"
    phase_confidence: float = 0.0
    phase_entered_at: Optional[str] = None

    # Phase-specific data
    accumulation_range_high: Optional[float] = None
    accumulation_range_low: Optional[float] = None
    sweep_level: Optional[float] = None
    sweep_direction: Optional[str] = None
    displacement_magnitude: Optional[float] = None
    expected_target: Optional[float] = None

    # Historical completion
    completion_rate: float = 0.0

    def confidence_modifier(self) -> int:
        """Return confidence modifier for current phase."""
        return PHASE_CONFIDENCE_MODIFIERS.get(self.current_phase, 0)

    def to_dict(self) -> dict:
        return {
            "instrument": self.instrument,
            "phase": self.current_phase,
            "phase_name": self.phase_name,
            "phase_confidence": round(self.phase_confidence, 1),
            "phase_entered_at": self.phase_entered_at,
            "confidence_modifier": self.confidence_modifier(),
            "accumulation_range": (
                [self.accumulation_range_low, self.accumulation_range_high]
                if self.accumulation_range_low is not None else None
            ),
            "sweep_level": self.sweep_level,
            "sweep_direction": self.sweep_direction,
            "displacement_magnitude": self.displacement_magnitude,
            "expected_target": self.expected_target,
            "completion_rate": round(self.completion_rate, 1),
        }


class SequenceTracker:
    """Tracks institutional sequence for each instrument."""

    def __init__(self, db):
        self.db = db
        self.states: Dict[str, SequenceState] = {}
        self._load_states()

    def update(self, instrument: str, smc_analysis, technical) -> SequenceState:
        """
        Update sequence state based on new SMC and technical analysis.

        Transitions:
        1→2: Sweep detected in RANGING regime
        2→3: Displacement detected + CHoCH/BOS
        3→4: Price returns to FVG/OB zone
        4→5: Price continues in displacement direction
        5→1: Structure breaks or range begins
        """
        if instrument not in self.states:
            self.states[instrument] = SequenceState(
                instrument=instrument,
                phase_entered_at=datetime.now(timezone.utc).isoformat(),
            )

        state = self.states[instrument]
        old_phase = state.current_phase
        now = datetime.now(timezone.utc).isoformat()

        # Detect transitions
        if state.current_phase == 1:
            self._update_accumulation(state, smc_analysis, technical)
        elif state.current_phase == 2:
            self._update_manipulation(state, smc_analysis)
        elif state.current_phase == 3:
            self._update_displacement(state, smc_analysis)
        elif state.current_phase == 4:
            self._update_retracement(state, smc_analysis)
        elif state.current_phase == 5:
            self._update_continuation(state, smc_analysis, technical)

        # If phase changed, log transition
        if state.current_phase != old_phase:
            state.phase_name = PHASES.get(state.current_phase, "UNKNOWN")
            state.phase_entered_at = now

            reason = self._transition_reason(old_phase, state.current_phase, smc_analysis)
            self._log_transition(instrument, old_phase, state.current_phase, reason,
                                 smc_analysis.setup_grade if smc_analysis else None)

            logger.info(
                f"SEQUENCE {instrument}: Phase {old_phase}→{state.current_phase} "
                f"({PHASES.get(old_phase)}→{state.phase_name}) | {reason}"
            )

        # Update completion rate from history
        state.completion_rate = self._get_completion_rate(instrument)

        # Save state
        self._save_state(state)

        return state

    def get_confidence_modifier(self, instrument: str) -> int:
        """Get confidence modifier for current phase."""
        state = self.states.get(instrument)
        if not state:
            return 0
        return state.confidence_modifier()

    def get_state(self, instrument: str) -> Optional[SequenceState]:
        """Get current sequence state for an instrument."""
        return self.states.get(instrument)

    # === Phase update methods ===

    def _update_accumulation(self, state: SequenceState, smc, technical):
        """
        Phase 1 → 2 transition: Detect sweep starting in a range.

        Criteria for staying in Phase 1:
        - RANGING structure (ADX < 25 or BB squeeze)

        Transition to Phase 2 when:
        - Sweep detected AND we were in a range
        """
        # Track accumulation range
        regime = getattr(technical, 'market_regime', 'UNKNOWN')

        if regime in ("RANGING", "LOW_VOLATILITY"):
            # We're in accumulation - track the range
            adx = getattr(technical, 'adx', 50)
            bb_pct = getattr(technical, 'bollinger_width_percentile', 50)

            # Confidence in accumulation phase
            state.phase_confidence = max(0, min(100,
                (100 - adx) * 0.5 + (100 - bb_pct) * 0.5
            ))

            # Track range bounds from HTF swing points
            if smc and smc.htf_swing_high > 0:
                state.accumulation_range_high = smc.htf_swing_high
            if smc and smc.htf_swing_low > 0:
                state.accumulation_range_low = smc.htf_swing_low

        # Transition to Phase 2: sweep detected
        if smc and smc.sweep_detected:
            state.current_phase = 2
            state.sweep_level = smc.sweep_detected.level.price
            state.sweep_direction = smc.sweep_detected.sweep_direction
            state.phase_confidence = 70.0
            return

        # Also check for regime change → could skip to 3 on strong displacement
        if smc and smc.ltf_displacement:
            state.current_phase = 3
            state.displacement_magnitude = smc.ltf_displacement.avg_body_ratio
            state.phase_confidence = 60.0

    def _update_manipulation(self, state: SequenceState, smc):
        """
        Phase 2 → 3 transition: Sweep confirmed, waiting for displacement.

        Stay in Phase 2:
        - Sweep detected but no CHoCH/BOS yet

        Transition to Phase 3:
        - Displacement + (CHoCH or BOS)
        """
        if not smc:
            return

        # Update sweep info
        if smc.sweep_detected:
            state.sweep_level = smc.sweep_detected.level.price
            state.sweep_direction = smc.sweep_detected.sweep_direction

        # Check for displacement + structure shift
        has_shift = smc.ltf_choch or smc.ltf_bos
        has_displacement = smc.ltf_displacement is not None

        if has_shift and has_displacement:
            state.current_phase = 3
            state.displacement_magnitude = smc.ltf_displacement.avg_body_ratio
            state.phase_confidence = 80.0
        elif has_shift:
            # Structure shift without displacement - weaker transition
            state.current_phase = 3
            state.displacement_magnitude = 0.0
            state.phase_confidence = 55.0
        else:
            # Still in manipulation
            state.phase_confidence = max(40.0, state.phase_confidence - 2.0)

        # Reset to Phase 1 if too long without transition
        if state.phase_confidence < 20.0:
            state.current_phase = 1
            state.phase_confidence = 30.0

    def _update_displacement(self, state: SequenceState, smc):
        """
        Phase 3 → 4 transition: Waiting for retracement.

        Stay in Phase 3:
        - Strong momentum, no pullback yet

        Transition to Phase 4:
        - Price pulls back into FVG or OB zone
        """
        if not smc:
            return

        # Check for retracement into entry zones
        has_unfilled_fvg = any(not f.filled for f in smc.fvgs) if smc.fvgs else False
        has_fresh_ob = any(not ob.mitigated for ob in smc.order_blocks) if smc.order_blocks else False

        # If price is near FVG/OB and momentum has slowed, it's retracing
        if has_unfilled_fvg or has_fresh_ob:
            # Check if current price is in a zone
            if smc.entry_zone is not None:
                state.current_phase = 4
                state.phase_confidence = 85.0
                return

        # Still in displacement
        if smc.ltf_displacement:
            state.displacement_magnitude = smc.ltf_displacement.avg_body_ratio
            state.phase_confidence = max(50.0, state.phase_confidence - 3.0)
        else:
            # Displacement fading, could be retracing
            state.phase_confidence -= 5.0
            if state.phase_confidence < 30.0:
                # Likely retracing even without clear zone
                state.current_phase = 4
                state.phase_confidence = 50.0

    def _update_retracement(self, state: SequenceState, smc):
        """
        Phase 4 → 5 transition: Optimal entry phase.

        Stay in Phase 4:
        - Price is in FVG/OB zone

        Transition to Phase 5:
        - Price starts moving in displacement direction again

        Reset to Phase 1:
        - Structure breaks against us
        """
        if not smc:
            return

        # Check for continuation
        if smc.direction:
            # Direction established - moving into continuation
            # Check if it aligns with the sweep direction
            expected_dir = "LONG" if state.sweep_direction == "SELLSIDE_SWEEP" else "SHORT"
            if smc.direction == expected_dir:
                state.current_phase = 5
                state.phase_confidence = 70.0
                return

        # Check for structure break against us (invalidation)
        if smc.ltf_choch:
            expected_dir = "BULLISH" if state.sweep_direction == "SELLSIDE_SWEEP" else "BEARISH"
            if smc.ltf_choch.direction != expected_dir:
                # Structure broke against the expected direction
                state.current_phase = 1
                state.phase_confidence = 20.0
                return

        # Still in retracement
        state.phase_confidence = max(40.0, state.phase_confidence - 1.0)

    def _update_continuation(self, state: SequenceState, smc, technical):
        """
        Phase 5 → 1 transition: Sequence completing.

        Stay in Phase 5:
        - New HH/HL (long) or LH/LL (short) after retracement

        Transition to Phase 1:
        - Structure breaks or range begins
        - Target reached
        """
        if not smc:
            return

        regime = getattr(technical, 'market_regime', 'UNKNOWN')

        # Check for range formation (back to accumulation)
        if regime in ("RANGING", "LOW_VOLATILITY"):
            # Log completion
            self._log_completion(state)
            state.current_phase = 1
            state.phase_confidence = 40.0
            state.sweep_level = None
            state.sweep_direction = None
            state.displacement_magnitude = None
            return

        # Check for structure break (invalidation)
        if smc.htf_bias == "NEUTRAL":
            self._log_completion(state)
            state.current_phase = 1
            state.phase_confidence = 30.0
            return

        # Still in continuation
        state.phase_confidence = max(30.0, state.phase_confidence - 2.0)
        if state.phase_confidence < 30.0:
            self._log_completion(state)
            state.current_phase = 1
            state.phase_confidence = 30.0

    # === Helper methods ===

    def _transition_reason(self, old_phase: int, new_phase: int, smc) -> str:
        """Generate human-readable transition reason."""
        reasons = {
            (1, 2): "Sweep detected in range",
            (1, 3): "Direct displacement (skipped manipulation)",
            (2, 3): "Displacement + structure shift after sweep",
            (2, 1): "Manipulation phase timed out",
            (3, 4): "Price retracing to entry zone",
            (4, 5): "Continuation in displacement direction",
            (4, 1): "Structure invalidated during retracement",
            (5, 1): "Sequence complete (range or structure break)",
        }
        return reasons.get((old_phase, new_phase), f"Phase {old_phase}→{new_phase}")

    def _log_transition(self, instrument, old_phase, new_phase, reason, smc_grade=None):
        """Log phase transition to DB."""
        try:
            with self.db._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sequence_transitions (
                        timestamp, instrument, old_phase, new_phase,
                        old_phase_name, new_phase_name, reason, smc_grade
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    instrument,
                    old_phase, new_phase,
                    PHASES.get(old_phase, "UNKNOWN"),
                    PHASES.get(new_phase, "UNKNOWN"),
                    reason, smc_grade,
                ))
        except Exception as e:
            logger.warning(f"Failed to log sequence transition: {e}")

    def _log_completion(self, state: SequenceState):
        """Log a sequence completion."""
        try:
            with self.db._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sequence_completions (
                        instrument, started_at, completed_at,
                        phases_completed, max_phase_reached
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    state.instrument,
                    state.phase_entered_at,
                    datetime.now(timezone.utc).isoformat(),
                    state.current_phase,
                    state.current_phase,
                ))
        except Exception as e:
            logger.warning(f"Failed to log sequence completion: {e}")

    def _get_completion_rate(self, instrument: str) -> float:
        """Get historical completion rate (% of sequences reaching phase 4+)."""
        try:
            with self.db._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN max_phase_reached >= 4 THEN 1 ELSE 0 END) as completed
                    FROM sequence_completions
                    WHERE instrument = ?
                """, (instrument,))
                row = cursor.fetchone()
                total = row["total"] or 0
                completed = row["completed"] or 0
                return (completed / total * 100) if total > 0 else 50.0
        except Exception:
            return 50.0

    def _save_state(self, state: SequenceState):
        """Save sequence state to DB."""
        try:
            with self.db._connection() as conn:
                cursor = conn.cursor()
                # Deactivate old state for this instrument
                cursor.execute(
                    "UPDATE sequence_states SET active = 0 WHERE instrument = ? AND active = 1",
                    (state.instrument,)
                )
                # Insert new state
                cursor.execute("""
                    INSERT INTO sequence_states (
                        timestamp, instrument, current_phase, phase_name,
                        phase_confidence, phase_entered_at,
                        accumulation_range_high, accumulation_range_low,
                        sweep_level, sweep_direction,
                        displacement_magnitude, expected_target, active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    state.instrument,
                    state.current_phase,
                    state.phase_name,
                    state.phase_confidence,
                    state.phase_entered_at,
                    state.accumulation_range_high,
                    state.accumulation_range_low,
                    state.sweep_level,
                    state.sweep_direction,
                    state.displacement_magnitude,
                    state.expected_target,
                ))
        except Exception as e:
            logger.warning(f"Failed to save sequence state: {e}")

    def _load_states(self):
        """Load active sequence states from DB."""
        try:
            with self.db._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM sequence_states WHERE active = 1
                """)
                for row in cursor.fetchall():
                    row = dict(row)
                    state = SequenceState(
                        instrument=row["instrument"],
                        current_phase=row["current_phase"],
                        phase_name=row["phase_name"],
                        phase_confidence=row["phase_confidence"] or 0.0,
                        phase_entered_at=row["phase_entered_at"],
                        accumulation_range_high=row["accumulation_range_high"],
                        accumulation_range_low=row["accumulation_range_low"],
                        sweep_level=row["sweep_level"],
                        sweep_direction=row["sweep_direction"],
                        displacement_magnitude=row["displacement_magnitude"],
                        expected_target=row["expected_target"],
                    )
                    self.states[state.instrument] = state
                if self.states:
                    logger.info(f"Loaded {len(self.states)} sequence states from DB")
        except Exception:
            # Tables may not exist yet
            pass
