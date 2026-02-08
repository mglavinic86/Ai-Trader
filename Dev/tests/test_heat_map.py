"""Tests for Liquidity Heat Map (ISI Phase 3)."""

import sys
import math
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.smc.liquidity_heat_map import (
    LiquidityHeatMapper, LiquidityHeatMap, HeatMapLevel,
    DECAY_RATE, SESSION_WEIGHTS,
)


def make_mock_liquidity_map(buyside_levels=None, sellside_levels=None):
    """Create a mock LiquidityMap."""
    lm = MagicMock()
    lm.buyside = buyside_levels or []
    lm.sellside = sellside_levels or []
    return lm


def make_mock_level(price, source="SWING", strength=1, swept=False):
    """Create a mock LiquidityLevel."""
    level = MagicMock()
    level.price = price
    level.source = source
    level.strength = strength
    level.swept = swept
    level.type = "BUYSIDE" if price > 1.1 else "SELLSIDE"
    return level


def test_temporal_decay():
    """Older levels should have lower density."""
    mapper = LiquidityHeatMapper()

    # 0 hours = weight 1.0
    assert abs(mapper._temporal_decay(0) - 1.0) < 0.001

    # 10 hours → exp(-0.05*10) = exp(-0.5) ≈ 0.607
    decay_10 = mapper._temporal_decay(10)
    expected = math.exp(-DECAY_RATE * 10)
    assert abs(decay_10 - expected) < 0.001

    # 100 hours → very small weight
    decay_100 = mapper._temporal_decay(100)
    assert decay_100 < 0.01

    # Monotonically decreasing
    assert mapper._temporal_decay(0) > mapper._temporal_decay(10) > mapper._temporal_decay(50)
    print("  [PASS] Temporal decay: older = lower weight")


def test_sweep_direction_prediction():
    """More sellside density → higher P(sellside sweep) = bullish."""
    mapper = LiquidityHeatMapper()

    # Sellside heavy → expect sellside sweep (bullish reversal)
    prob_sell_heavy = mapper._predict_sweep_direction(10.0, 30.0, "NEUTRAL")
    assert prob_sell_heavy > 0.5, f"Expected > 0.5, got {prob_sell_heavy}"

    # Buyside heavy → expect buyside sweep (bearish reversal)
    prob_buy_heavy = mapper._predict_sweep_direction(30.0, 10.0, "NEUTRAL")
    assert prob_buy_heavy < 0.5, f"Expected < 0.5, got {prob_buy_heavy}"

    # Balanced
    prob_balanced = mapper._predict_sweep_direction(20.0, 20.0, "NEUTRAL")
    assert abs(prob_balanced - 0.5) < 0.1

    # HTF bias adjustment
    prob_bull_bias = mapper._predict_sweep_direction(20.0, 20.0, "BULLISH")
    prob_bear_bias = mapper._predict_sweep_direction(20.0, 20.0, "BEARISH")
    assert prob_bull_bias > prob_bear_bias
    print("  [PASS] Sweep direction prediction: density + HTF bias")


def test_primary_target_selection():
    """Primary target should be closest + strongest level."""
    mapper = LiquidityHeatMapper()
    current_price = 1.1000

    levels = [
        HeatMapLevel(price=1.1050, type="BUYSIDE", density_score=20.0),
        HeatMapLevel(price=1.1200, type="BUYSIDE", density_score=50.0),
        HeatMapLevel(price=1.1010, type="BUYSIDE", density_score=15.0),
    ]

    target = mapper._find_primary_target(levels, current_price)

    assert target is not None
    # Closest strong level should win (1.1010 is closest but weak, 1.1050 is good balance)
    assert target.price in (1.1050, 1.1010), f"Unexpected target: {target.price}"
    print("  [PASS] Primary target: closest + strongest")


def test_empty_map():
    """Should handle empty liquidity gracefully."""
    mapper = LiquidityHeatMapper()
    liq_map = make_mock_liquidity_map()

    result = mapper.build([], liq_map, {}, "EUR_USD")

    assert isinstance(result, LiquidityHeatMap)
    assert result.buyside_total_density == 0
    assert result.sellside_total_density == 0
    assert result.temporal_bias == "BALANCED"
    assert result.primary_target is None
    print("  [PASS] Empty map handled gracefully")


def test_build_with_levels():
    """Full build with buyside and sellside levels."""
    mapper = LiquidityHeatMapper()

    buyside = [
        make_mock_level(1.1050, "EQUAL_HIGHS", strength=3),
        make_mock_level(1.1100, "SWING", strength=1),
    ]
    sellside = [
        make_mock_level(1.0950, "EQUAL_LOWS", strength=2),
    ]
    liq_map = make_mock_liquidity_map(buyside, sellside)

    h1_candles = [{"close": 1.1000, "high": 1.1010, "low": 1.0990, "open": 1.0995}] * 50

    result = mapper.build(h1_candles, liq_map, {}, "EUR_USD", current_price=1.1000)

    assert result.buyside_total_density > 0
    assert result.sellside_total_density > 0
    assert len(result.buyside_levels) >= 2
    assert len(result.sellside_levels) >= 1
    assert result.primary_target is not None
    print("  [PASS] Build with levels produces scored heat map")


def test_session_levels_integration():
    """Session levels should be added to heat map."""
    mapper = LiquidityHeatMapper()
    liq_map = make_mock_liquidity_map()

    session_levels = {
        "london_high": 1.1080,
        "london_low": 1.0920,
        "ny_high": 1.1060,
        "ny_low": 1.0940,
    }

    h1_candles = [{"close": 1.1000}] * 20

    result = mapper.build(h1_candles, liq_map, session_levels, "EUR_USD", current_price=1.1000)

    # Should have buyside (above) and sellside (below) from sessions
    assert len(result.buyside_levels) >= 2  # london_high, ny_high
    assert len(result.sellside_levels) >= 2  # london_low, ny_low
    print("  [PASS] Session levels integrated into heat map")


def test_swept_levels_excluded():
    """Already swept levels should not appear in heat map."""
    mapper = LiquidityHeatMapper()

    buyside = [
        make_mock_level(1.1050, "SWING", strength=2, swept=True),
        make_mock_level(1.1100, "SWING", strength=1, swept=False),
    ]
    liq_map = make_mock_liquidity_map(buyside, [])

    h1_candles = [{"close": 1.1000}] * 20

    result = mapper.build(h1_candles, liq_map, {}, "EUR_USD", current_price=1.1000)

    # Only unswept level should be in heat map
    assert len(result.buyside_levels) == 1
    assert result.buyside_levels[0].price == 1.1100
    print("  [PASS] Swept levels excluded from heat map")


def test_to_dict():
    """HeatMap to_dict should be serializable."""
    hm = LiquidityHeatMap(
        buyside_total_density=25.5,
        sellside_total_density=30.2,
        sweep_direction_probability=0.65,
        temporal_bias="SELLSIDE_HEAVY",
        primary_target=HeatMapLevel(
            price=1.0950, type="SELLSIDE", density_score=15.0,
        ),
    )
    d = hm.to_dict()
    assert d["buyside_density"] == 25.5
    assert d["sellside_density"] == 30.2
    assert d["sweep_direction_prob"] == 0.65
    assert d["temporal_bias"] == "SELLSIDE_HEAVY"
    assert d["primary_target"]["price"] == 1.0950
    print("  [PASS] to_dict returns correct structure")


if __name__ == "__main__":
    print("\n=== Testing Liquidity Heat Map (ISI Phase 3) ===\n")

    tests = [
        test_temporal_decay,
        test_sweep_direction_prediction,
        test_primary_target_selection,
        test_empty_map,
        test_build_with_levels,
        test_session_levels_integration,
        test_swept_levels_excluded,
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

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print(f"{'='*50}\n")

    sys.exit(1 if failed > 0 else 0)
