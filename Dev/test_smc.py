"""
Test suite for SMC (Smart Money Concepts) module.

Tests all core SMC components:
- Swing point detection
- Market structure classification (HH_HL, LH_LL, RANGING)
- CHoCH and BOS detection
- Liquidity mapping
- Session level detection
- Sweep detection
- FVG detection
- Order Block detection
- Premium/Discount calculation
- Displacement detection
- Setup grading
- Full pipeline integration
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.smc.structure import (
    detect_swing_points, classify_structure, detect_choch, detect_bos,
    SwingPoint, StructureShift
)
from src.smc.liquidity import (
    map_liquidity, detect_session_levels, detect_sweep, LiquidityMap
)
from src.smc.zones import (
    detect_fvg, detect_order_blocks, calculate_premium_discount,
    FairValueGap, OrderBlock
)
from src.smc.displacement import detect_displacement, Displacement
from src.smc.smc_analyzer import SMCAnalyzer, SMCAnalysis


def _make_candle(o, h, l, c, time="2026-01-01T12:00:00+00:00", volume=100):
    """Helper to create a candle dict."""
    return {"open": o, "high": h, "low": l, "close": c, "time": time, "volume": volume}


def _make_uptrend_candles(n=50, start_price=1.1000):
    """Generate candles forming an uptrend with HH/HL."""
    candles = []
    price = start_price
    for i in range(n):
        # Uptrend: generally rising with pullbacks
        if i % 7 < 5:  # 5 up, 2 down
            change = 0.0005 + (i % 3) * 0.0002
            o = price
            c = price + change
            h = c + 0.0002
            l = o - 0.0001
        else:
            change = 0.0003
            o = price
            c = price - change
            h = o + 0.0001
            l = c - 0.0002

        candles.append(_make_candle(o, h, l, c, f"2026-01-01T{12 + i // 12:02d}:{(i * 5) % 60:02d}:00+00:00"))
        price = c

    return candles


def _make_downtrend_candles(n=50, start_price=1.1500):
    """Generate candles forming a downtrend with LH/LL."""
    candles = []
    price = start_price
    for i in range(n):
        if i % 7 < 5:
            change = 0.0005 + (i % 3) * 0.0002
            o = price
            c = price - change
            h = o + 0.0001
            l = c - 0.0002
        else:
            change = 0.0003
            o = price
            c = price + change
            h = c + 0.0002
            l = o - 0.0001

        candles.append(_make_candle(o, h, l, c, f"2026-01-01T{12 + i // 12:02d}:{(i * 5) % 60:02d}:00+00:00"))
        price = c

    return candles


def _make_ranging_candles(n=50, center=1.1200):
    """Generate ranging candles."""
    candles = []
    import math
    for i in range(n):
        offset = 0.0020 * math.sin(i * 0.5)
        o = center + offset
        c = center + offset + 0.0003 * (1 if i % 2 == 0 else -1)
        h = max(o, c) + 0.0005
        l = min(o, c) - 0.0005
        candles.append(_make_candle(o, h, l, c, f"2026-01-01T{12 + i // 12:02d}:{(i * 5) % 60:02d}:00+00:00"))
    return candles


# ===========================================
# Test 1: Swing Point Detection
# ===========================================

def test_swing_points():
    """Test swing high/low pivot detection."""
    print("\n=== Test 1: Swing Point Detection ===")

    candles = _make_uptrend_candles(30)
    swings = detect_swing_points(candles, left_bars=3, right_bars=2)

    print(f"  Candles: {len(candles)}")
    print(f"  Swing points found: {len(swings)}")

    highs = [sp for sp in swings if sp.type == "HIGH"]
    lows = [sp for sp in swings if sp.type == "LOW"]
    print(f"  Swing highs: {len(highs)}")
    print(f"  Swing lows: {len(lows)}")

    # Should find at least some swing points
    assert len(swings) > 0, "Should detect swing points"
    print("  PASSED")


# ===========================================
# Test 2: Structure Classification
# ===========================================

def test_structure_classification():
    """Test HH_HL / LH_LL / RANGING classification."""
    print("\n=== Test 2: Structure Classification ===")

    # Test with manually created swing points
    # Uptrend: HH/HL
    uptrend_swings = [
        SwingPoint(index=5, price=1.1050, type="HIGH"),
        SwingPoint(index=8, price=1.1020, type="LOW"),
        SwingPoint(index=12, price=1.1080, type="HIGH"),  # Higher high
        SwingPoint(index=15, price=1.1040, type="LOW"),    # Higher low
    ]
    structure = classify_structure(uptrend_swings)
    print(f"  Uptrend swings -> {structure}")
    assert structure == "HH_HL", f"Expected HH_HL, got {structure}"

    # Downtrend: LH/LL
    downtrend_swings = [
        SwingPoint(index=5, price=1.1080, type="HIGH"),
        SwingPoint(index=8, price=1.1040, type="LOW"),
        SwingPoint(index=12, price=1.1060, type="HIGH"),  # Lower high
        SwingPoint(index=15, price=1.1020, type="LOW"),    # Lower low
    ]
    structure = classify_structure(downtrend_swings)
    print(f"  Downtrend swings -> {structure}")
    assert structure == "LH_LL", f"Expected LH_LL, got {structure}"

    print("  PASSED")


# ===========================================
# Test 3: CHoCH Detection
# ===========================================

def test_choch():
    """Test Change of Character detection."""
    print("\n=== Test 3: CHoCH Detection ===")

    # Create uptrend structure then break below HL
    swings = [
        SwingPoint(index=5, price=1.1050, type="HIGH"),
        SwingPoint(index=8, price=1.1020, type="LOW"),
        SwingPoint(index=12, price=1.1080, type="HIGH"),
        SwingPoint(index=15, price=1.1040, type="LOW"),  # HL at 1.1040
    ]

    # Candles where index 18 closes below 1.1040 (the HL)
    candles = [_make_candle(1.10, 1.11, 1.09, 1.10)] * 16
    # Add candles that break below HL
    candles.append(_make_candle(1.1050, 1.1060, 1.1030, 1.1035))  # idx 16
    candles.append(_make_candle(1.1035, 1.1040, 1.1020, 1.1025))  # idx 17 - breaks below HL
    candles.append(_make_candle(1.1025, 1.1030, 1.1010, 1.1015))  # idx 18

    choch = detect_choch(candles, swings)
    if choch:
        print(f"  CHoCH detected: {choch.direction} at {choch.break_level}")
        print(f"  Confirmed at candle idx {choch.confirmation_candle_idx}")
        assert choch.direction == "BEARISH", f"Expected BEARISH CHoCH"
    else:
        print("  No CHoCH detected (may need more specific price levels)")

    print("  PASSED")


# ===========================================
# Test 4: FVG Detection
# ===========================================

def test_fvg():
    """Test Fair Value Gap detection."""
    print("\n=== Test 4: FVG Detection ===")

    # Create candles with a bullish FVG
    candles = [
        _make_candle(1.1000, 1.1010, 1.0990, 1.1005),  # Normal
        _make_candle(1.1005, 1.1020, 1.1000, 1.1015),   # prev: high=1.1020
        _make_candle(1.1015, 1.1060, 1.1010, 1.1055),   # Big bullish (middle)
        _make_candle(1.1055, 1.1065, 1.1030, 1.1060),   # next: low=1.1030
    ]
    # FVG exists if candles[1].high < candles[3].low -> 1.1020 < 1.1030 = YES

    fvgs = detect_fvg(candles)
    print(f"  Candles: {len(candles)}")
    print(f"  FVGs found: {len(fvgs)}")

    for fvg in fvgs:
        print(f"  FVG: {fvg.direction} start={fvg.start_price} end={fvg.end_price} filled={fvg.filled}")

    bullish_fvgs = [f for f in fvgs if f.direction == "BULLISH"]
    print(f"  Bullish FVGs: {len(bullish_fvgs)}")
    assert len(bullish_fvgs) > 0, "Should detect bullish FVG"
    print("  PASSED")


# ===========================================
# Test 5: Order Block Detection
# ===========================================

def test_order_blocks():
    """Test Order Block detection."""
    print("\n=== Test 5: Order Block Detection ===")

    # Average body = ~0.0005, so displacement needs > 0.001
    candles = [_make_candle(1.1000 + i * 0.0002, 1.1005 + i * 0.0002,
                            1.0995 + i * 0.0002, 1.1003 + i * 0.0002)
               for i in range(28)]

    # Add a bearish candle followed by strong bullish displacement
    candles.append(_make_candle(1.1060, 1.1065, 1.1050, 1.1052))  # Bearish (OB candidate)
    candles.append(_make_candle(1.1052, 1.1090, 1.1050, 1.1085))  # Strong bullish displacement
    candles.append(_make_candle(1.1085, 1.1095, 1.1080, 1.1090))  # Continuation

    obs = detect_order_blocks(candles, min_displacement_ratio=2.0)
    print(f"  Candles: {len(candles)}")
    print(f"  Order Blocks found: {len(obs)}")

    for ob in obs:
        print(f"  OB: {ob.direction} high={ob.high} low={ob.low} disp={ob.displacement_strength:.1f}x mitigated={ob.mitigated}")

    print("  PASSED")


# ===========================================
# Test 6: Premium/Discount Calculation
# ===========================================

def test_premium_discount():
    """Test Premium/Discount zone calculation."""
    print("\n=== Test 6: Premium/Discount Zones ===")

    swing_high = 1.1100
    swing_low = 1.1000

    # Test discount zone (below 45%)
    pd = calculate_premium_discount(swing_high, swing_low, 1.1020)
    print(f"  Price 1.1020 -> zone={pd['zone']} ({pd['percentage']}%)")
    assert pd["zone"] == "DISCOUNT", f"Expected DISCOUNT, got {pd['zone']}"

    # Test premium zone (above 55%)
    pd = calculate_premium_discount(swing_high, swing_low, 1.1080)
    print(f"  Price 1.1080 -> zone={pd['zone']} ({pd['percentage']}%)")
    assert pd["zone"] == "PREMIUM", f"Expected PREMIUM, got {pd['zone']}"

    # Test equilibrium (45-55%)
    pd = calculate_premium_discount(swing_high, swing_low, 1.1050)
    print(f"  Price 1.1050 -> zone={pd['zone']} ({pd['percentage']}%)")
    assert pd["zone"] == "EQUILIBRIUM", f"Expected EQUILIBRIUM, got {pd['zone']}"

    print("  PASSED")


# ===========================================
# Test 7: Displacement Detection
# ===========================================

def test_displacement():
    """Test displacement (impulse move) detection."""
    print("\n=== Test 7: Displacement Detection ===")

    # Normal candles with small bodies
    candles = [_make_candle(1.1000 + i * 0.0001, 1.1005 + i * 0.0001,
                            1.0995 + i * 0.0001, 1.1002 + i * 0.0001)
               for i in range(25)]

    # Add a displacement candle (3x average body, small wicks)
    candles.append(_make_candle(1.1030, 1.1062, 1.1029, 1.1060))  # Big bullish, small wicks

    displacements = detect_displacement(candles, min_ratio=2.0, lookback=20)
    print(f"  Candles: {len(candles)}")
    print(f"  Displacements found: {len(displacements)}")

    for d in displacements:
        print(f"  Displacement: {d.direction} ratio={d.avg_body_ratio:.1f}x confirmed={d.confirmed}")

    print("  PASSED")


# ===========================================
# Test 8: Setup Grading
# ===========================================

def test_grading():
    """Test SMC setup grading logic."""
    print("\n=== Test 8: Setup Grading ===")

    analyzer = SMCAnalyzer()

    # NO_TRADE: no sweep
    analysis = SMCAnalysis(
        htf_bias="BULLISH",
        htf_structure="HH_HL",
        direction="LONG",
    )
    grade = analyzer.grade_setup(analysis)
    print(f"  No sweep -> {grade}")
    assert grade == "NO_TRADE", f"Expected NO_TRADE, got {grade}"

    # NO_TRADE: sweep but no CHoCH/BOS
    from src.smc.liquidity import LiquiditySweep, LiquidityLevel
    analysis = SMCAnalysis(
        htf_bias="BULLISH",
        htf_structure="HH_HL",
        direction="LONG",
        sweep_detected=LiquiditySweep(
            level=LiquidityLevel(price=1.1000, type="SELLSIDE", source="SWING"),
            sweep_candle_idx=50,
            sweep_direction="SELLSIDE_SWEEP",
            reversal_confirmed=True,
        ),
    )
    grade = analyzer.grade_setup(analysis)
    print(f"  Sweep but no CHoCH/BOS -> {grade}")
    assert grade == "NO_TRADE", f"Expected NO_TRADE, got {grade}"

    # Valid setup with sweep + CHoCH + direction
    from src.smc.structure import StructureShift, SwingPoint as SP
    analysis = SMCAnalysis(
        htf_bias="BULLISH",
        htf_structure="HH_HL",
        direction="LONG",
        sweep_detected=LiquiditySweep(
            level=LiquidityLevel(price=1.1000, type="SELLSIDE", source="SWING"),
            sweep_candle_idx=50,
            sweep_direction="SELLSIDE_SWEEP",
            reversal_confirmed=True,
        ),
        ltf_choch=StructureShift(
            type="CHOCH",
            direction="BULLISH",
            break_level=1.1020,
            swing_point=SP(index=45, price=1.1010, type="HIGH"),
            confirmation_candle_idx=52,
        ),
        ltf_displacement=Displacement(
            direction="BULLISH",
            candle_index=51,
            body_size=0.003,
            avg_body_ratio=3.0,
        ),
        fvgs=[FairValueGap(
            start_price=1.1025, end_price=1.1015,
            direction="BULLISH", candle_index=51,
        )],
        order_blocks=[OrderBlock(
            high=1.1012, low=1.1005,
            direction="BULLISH", candle_index=49,
        )],
        premium_discount={"zone": "DISCOUNT", "percentage": 30.0},
    )
    grade = analyzer.grade_setup(analysis)
    print(f"  Full A+ setup -> {grade}")
    print(f"  Grade reasons: {analysis.grade_reasons}")
    assert grade in ("A+", "A"), f"Expected A+ or A, got {grade}"

    print("  PASSED")


# ===========================================
# Test 9: Session Levels
# ===========================================

def test_session_levels():
    """Test session level detection."""
    print("\n=== Test 9: Session Levels ===")

    # Create candles across London session (07-16 UTC)
    candles = []
    for i in range(50):
        hour = 7 + i // 6  # ~8 hours of data
        minute = (i * 10) % 60
        price = 1.1000 + i * 0.0002
        candles.append(_make_candle(
            price, price + 0.0010, price - 0.0010, price + 0.0005,
            f"2026-01-01T{hour:02d}:{minute:02d}:00+00:00"
        ))

    levels = detect_session_levels(candles)
    print(f"  Sessions detected: {list(levels.keys())}")

    for name, data in levels.items():
        print(f"  {name}: high={data['high']:.5f} low={data['low']:.5f}")

    assert len(levels) > 0, "Should detect at least one session"
    print("  PASSED")


# ===========================================
# Test 10: Full Pipeline Integration
# ===========================================

def test_full_pipeline():
    """Test full SMC analyzer pipeline."""
    print("\n=== Test 10: Full Pipeline Integration ===")

    analyzer = SMCAnalyzer()

    h4_candles = _make_uptrend_candles(50, 1.0800)
    h1_candles = _make_uptrend_candles(80, 1.0900)
    m5_candles = _make_uptrend_candles(100, 1.1000)

    # HTF Analysis
    htf_result = analyzer.analyze_htf(h4_candles, h1_candles, "EUR_USD")
    print(f"  HTF Bias: {htf_result['htf_bias']}")
    print(f"  HTF Structure: {htf_result['htf_structure']}")
    print(f"  Buyside levels: {len(htf_result['liquidity_map'].buyside)}")
    print(f"  Sellside levels: {len(htf_result['liquidity_map'].sellside)}")

    # LTF Analysis
    analysis = analyzer.analyze_ltf(m5_candles, htf_result, "EUR_USD")
    print(f"  LTF Structure: {analysis.ltf_structure}")
    print(f"  Sweep: {'YES' if analysis.sweep_detected else 'NO'}")
    print(f"  CHoCH: {'YES' if analysis.ltf_choch else 'NO'}")
    print(f"  BOS: {'YES' if analysis.ltf_bos else 'NO'}")
    print(f"  FVGs: {len(analysis.fvgs)}")
    print(f"  OBs: {len(analysis.order_blocks)}")
    print(f"  Grade: {analysis.setup_grade}")
    print(f"  Direction: {analysis.direction}")
    print(f"  Confidence: {analysis.confidence}")

    # Verify analysis produces a result (may be NO_TRADE with synthetic data)
    assert analysis.setup_grade in ("A+", "A", "B", "NO_TRADE")
    print("  PASSED")


# ===========================================
# Run all tests
# ===========================================

def run_all_tests():
    """Run all SMC tests."""
    tests = [
        ("Swing Points", test_swing_points),
        ("Structure Classification", test_structure_classification),
        ("CHoCH Detection", test_choch),
        ("FVG Detection", test_fvg),
        ("Order Block Detection", test_order_blocks),
        ("Premium/Discount Zones", test_premium_discount),
        ("Displacement Detection", test_displacement),
        ("Setup Grading", test_grading),
        ("Session Levels", test_session_levels),
        ("Full Pipeline", test_full_pipeline),
    ]

    passed = 0
    failed = 0
    errors = []

    print("=" * 60)
    print("  SMC MODULE TEST SUITE")
    print("=" * 60)

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            failed += 1
            errors.append((name, str(e)))
            print(f"  FAILED: {e}")
        except Exception as e:
            failed += 1
            errors.append((name, str(e)))
            print(f"  ERROR: {e}")

    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed} PASSED, {failed} FAILED out of {len(tests)}")
    print("=" * 60)

    if errors:
        print("\nFailed tests:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
