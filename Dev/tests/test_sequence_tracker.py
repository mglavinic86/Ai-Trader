"""Tests for Sequence Tracker (ISI Phase 2)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.smc.sequence_tracker import SequenceTracker, SequenceState, PHASES, PHASE_CONFIDENCE_MODIFIERS
from src.utils.database import Database


def get_test_db():
    """Create a fresh test database."""
    test_path = Path(__file__).parent / "test_sequence.db"
    if test_path.exists():
        test_path.unlink()
    return Database(test_path)


def make_mock_smc(
    sweep=False, sweep_direction="SELLSIDE_SWEEP",
    choch=False, choch_direction="BULLISH",
    bos=False, bos_direction="BULLISH",
    displacement=False, displacement_ratio=2.5,
    htf_bias="BULLISH", htf_structure="HH_HL",
    setup_grade="A", direction="LONG",
    fvgs=None, order_blocks=None,
    entry_zone=None,
    htf_swing_high=1.1000, htf_swing_low=1.0900,
):
    """Create a mock SMC analysis object."""
    smc = MagicMock()
    smc.htf_bias = htf_bias
    smc.htf_structure = htf_structure
    smc.setup_grade = setup_grade
    smc.direction = direction
    smc.htf_swing_high = htf_swing_high
    smc.htf_swing_low = htf_swing_low

    if sweep:
        smc.sweep_detected = MagicMock()
        smc.sweep_detected.level = MagicMock(price=1.0950)
        smc.sweep_detected.sweep_direction = sweep_direction
        smc.sweep_detected.reversal_confirmed = True
    else:
        smc.sweep_detected = None

    if choch:
        smc.ltf_choch = MagicMock(direction=choch_direction)
    else:
        smc.ltf_choch = None

    if bos:
        smc.ltf_bos = MagicMock(direction=bos_direction)
    else:
        smc.ltf_bos = None

    if displacement:
        smc.ltf_displacement = MagicMock(
            direction="BULLISH" if choch_direction == "BULLISH" else "BEARISH",
            avg_body_ratio=displacement_ratio,
        )
    else:
        smc.ltf_displacement = None

    smc.fvgs = fvgs or []
    smc.order_blocks = order_blocks or []
    smc.entry_zone = entry_zone

    return smc


def make_mock_technical(regime="RANGING", adx=20, bb_pct=30):
    """Create a mock technical analysis."""
    tech = MagicMock()
    tech.market_regime = regime
    tech.adx = adx
    tech.bollinger_width_percentile = bb_pct
    tech.regime_strength = 50
    return tech


def test_initial_state():
    """New instruments should start at Phase 1 (Accumulation)."""
    db = get_test_db()
    tracker = SequenceTracker(db)

    smc = make_mock_smc(sweep=False, choch=False)
    tech = make_mock_technical(regime="RANGING")

    state = tracker.update("EUR_USD", smc, tech)

    assert state.current_phase == 1
    assert state.phase_name == "ACCUMULATION"
    assert state.confidence_modifier() == -20
    print("  [PASS] Initial state: Phase 1 (Accumulation)")


def test_accumulation_to_manipulation():
    """Phase 1 -> 2: Sweep detected in range."""
    db = get_test_db()
    tracker = SequenceTracker(db)

    # First: establish accumulation
    smc_range = make_mock_smc(sweep=False)
    tech_range = make_mock_technical(regime="RANGING", adx=18)
    tracker.update("EUR_USD", smc_range, tech_range)

    # Then: sweep detected
    smc_sweep = make_mock_smc(sweep=True, sweep_direction="SELLSIDE_SWEEP")
    state = tracker.update("EUR_USD", smc_sweep, tech_range)

    assert state.current_phase == 2
    assert state.phase_name == "MANIPULATION"
    assert state.sweep_level == 1.0950
    assert state.sweep_direction == "SELLSIDE_SWEEP"
    print("  [PASS] Phase 1 -> 2: Accumulation -> Manipulation")


def test_manipulation_to_displacement():
    """Phase 2 -> 3: Displacement + structure shift."""
    db = get_test_db()
    tracker = SequenceTracker(db)

    # Set up phase 2
    tracker.states["EUR_USD"] = SequenceState(
        instrument="EUR_USD",
        current_phase=2,
        phase_name="MANIPULATION",
        phase_confidence=70.0,
        sweep_level=1.0950,
        sweep_direction="SELLSIDE_SWEEP",
    )

    smc = make_mock_smc(
        sweep=True, choch=True, choch_direction="BULLISH",
        displacement=True, displacement_ratio=3.0,
    )
    tech = make_mock_technical(regime="TRENDING")

    state = tracker.update("EUR_USD", smc, tech)

    assert state.current_phase == 3
    assert state.phase_name == "DISPLACEMENT"
    assert state.displacement_magnitude == 3.0
    print("  [PASS] Phase 2 -> 3: Manipulation -> Displacement")


def test_displacement_to_retracement():
    """Phase 3 -> 4: Price returns to entry zone."""
    db = get_test_db()
    tracker = SequenceTracker(db)

    # Set up phase 3
    tracker.states["EUR_USD"] = SequenceState(
        instrument="EUR_USD",
        current_phase=3,
        phase_name="DISPLACEMENT",
        phase_confidence=80.0,
        sweep_direction="SELLSIDE_SWEEP",
    )

    # Simulate FVG available and price in zone
    mock_fvg = MagicMock(filled=False, direction="BULLISH")
    smc = make_mock_smc(
        sweep=True, choch=True, displacement=False,
        fvgs=[mock_fvg], entry_zone=(1.0940, 1.0960),
    )
    tech = make_mock_technical(regime="TRENDING")

    state = tracker.update("EUR_USD", smc, tech)

    assert state.current_phase == 4
    assert state.phase_name == "RETRACEMENT"
    assert state.confidence_modifier() == 15  # Optimal entry!
    print("  [PASS] Phase 3 -> 4: Displacement -> Retracement (OPTIMAL)")


def test_retracement_to_continuation():
    """Phase 4 -> 5: Price continues in displacement direction."""
    db = get_test_db()
    tracker = SequenceTracker(db)

    tracker.states["EUR_USD"] = SequenceState(
        instrument="EUR_USD",
        current_phase=4,
        phase_name="RETRACEMENT",
        phase_confidence=85.0,
        sweep_direction="SELLSIDE_SWEEP",
    )

    smc = make_mock_smc(
        sweep=True, choch=True, displacement=True,
        direction="LONG",
    )
    tech = make_mock_technical(regime="TRENDING")

    state = tracker.update("EUR_USD", smc, tech)

    assert state.current_phase == 5
    assert state.phase_name == "CONTINUATION"
    print("  [PASS] Phase 4 -> 5: Retracement -> Continuation")


def test_continuation_to_accumulation():
    """Phase 5 -> 1: Range forms again."""
    db = get_test_db()
    tracker = SequenceTracker(db)

    tracker.states["EUR_USD"] = SequenceState(
        instrument="EUR_USD",
        current_phase=5,
        phase_name="CONTINUATION",
        phase_confidence=60.0,
        sweep_direction="SELLSIDE_SWEEP",
    )

    smc = make_mock_smc(htf_bias="NEUTRAL")
    tech = make_mock_technical(regime="RANGING")

    state = tracker.update("EUR_USD", smc, tech)

    assert state.current_phase == 1
    assert state.phase_name == "ACCUMULATION"
    print("  [PASS] Phase 5 -> 1: Continuation -> Accumulation (cycle reset)")


def test_all_confidence_modifiers():
    """Verify confidence modifiers for all phases."""
    for phase, expected in PHASE_CONFIDENCE_MODIFIERS.items():
        state = SequenceState(instrument="TEST", current_phase=phase)
        assert state.confidence_modifier() == expected, \
            f"Phase {phase}: expected {expected}, got {state.confidence_modifier()}"
    print("  [PASS] All confidence modifiers correct")


def test_db_persistence():
    """States should persist across tracker instances."""
    db = get_test_db()

    # Create and update
    tracker1 = SequenceTracker(db)
    smc_sweep = make_mock_smc(sweep=True, sweep_direction="SELLSIDE_SWEEP")
    tech = make_mock_technical(regime="RANGING")
    tracker1.update("EUR_USD", smc_sweep, tech)

    # Create new tracker - should load state from DB
    tracker2 = SequenceTracker(db)
    assert "EUR_USD" in tracker2.states
    state = tracker2.states["EUR_USD"]
    assert state.current_phase == 2  # Should be in manipulation
    print("  [PASS] DB persistence works")


def test_to_dict():
    """to_dict should return serializable dict."""
    state = SequenceState(
        instrument="EUR_USD",
        current_phase=4,
        phase_name="RETRACEMENT",
        phase_confidence=85.0,
        sweep_level=1.0950,
        sweep_direction="SELLSIDE_SWEEP",
    )
    d = state.to_dict()
    assert d["phase"] == 4
    assert d["phase_name"] == "RETRACEMENT"
    assert d["confidence_modifier"] == 15
    assert d["sweep_level"] == 1.0950
    print("  [PASS] to_dict returns correct structure")


def cleanup():
    test_path = Path(__file__).parent / "test_sequence.db"
    if test_path.exists():
        test_path.unlink()


if __name__ == "__main__":
    print("\n=== Testing Sequence Tracker (ISI Phase 2) ===\n")

    tests = [
        test_initial_state,
        test_accumulation_to_manipulation,
        test_manipulation_to_displacement,
        test_displacement_to_retracement,
        test_retracement_to_continuation,
        test_continuation_to_accumulation,
        test_all_confidence_modifiers,
        test_db_persistence,
        test_to_dict,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    cleanup()
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print(f"{'='*50}\n")

    sys.exit(1 if failed > 0 else 0)
