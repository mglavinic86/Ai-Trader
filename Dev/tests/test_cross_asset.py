"""Tests for Cross-Asset Divergence Detector (ISI Phase 4)."""

import sys
import math
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.cross_asset_detector import (
    CrossAssetDetector, DivergenceSignal,
    CORRELATION_PAIRS, DIVERGENCE_THRESHOLD_SIGMA,
)
from src.utils.database import Database


def get_test_db():
    """Create a fresh test database."""
    test_path = Path(__file__).parent / "test_cross_asset.db"
    if test_path.exists():
        test_path.unlink()
    return Database(test_path)


import random

def make_correlated_candles(n=30, base_price=1.1000, trend_pct=0.001, noise_seed=42):
    """Generate candles with known price movement and shared noise pattern."""
    random.seed(noise_seed)
    candles = []
    price = base_price
    for i in range(n):
        noise = random.gauss(0, 0.0005)  # Small random noise
        price *= (1 + trend_pct + noise)
        candles.append({
            "close": price,
            "open": price * 0.999,
            "high": price * 1.001,
            "low": price * 0.998,
        })
    return candles


def make_divergent_candles(n=30, base_price=1.3000, trend_pct=-0.001, noise_seed=42):
    """Generate candles moving in opposite direction with same noise pattern (anti-correlated)."""
    random.seed(noise_seed)
    candles = []
    price = base_price
    for i in range(n):
        noise = random.gauss(0, 0.0005)
        price *= (1 + trend_pct - noise)  # Negate noise for anti-correlation
        candles.append({
            "close": price,
            "open": price * 0.999,
            "high": price * 1.001,
            "low": price * 0.998,
        })
    return candles


def test_correlation_calculation():
    """Test Pearson correlation on known data."""
    db = get_test_db()
    mock_client = MagicMock()
    detector = CrossAssetDetector(mock_client, db)

    # Perfectly correlated (both trending up)
    candles1 = make_correlated_candles(30, 1.1000, 0.001)
    candles2 = make_correlated_candles(30, 1.3000, 0.001)

    corr = detector._calculate_rolling_correlation(candles1, candles2)
    assert corr is not None
    assert corr > 0.8, f"Expected high positive correlation, got {corr:.3f}"

    # Anti-correlated
    candles3 = make_divergent_candles(30, 1.3000, -0.001)
    corr_neg = detector._calculate_rolling_correlation(candles1, candles3)
    assert corr_neg is not None
    assert corr_neg < -0.5, f"Expected negative correlation, got {corr_neg:.3f}"
    print("  [PASS] Correlation calculation: positive and negative")


def test_too_few_candles():
    """Should return None with insufficient data."""
    db = get_test_db()
    mock_client = MagicMock()
    detector = CrossAssetDetector(mock_client, db)

    short = [{"close": 1.1 + i * 0.001} for i in range(5)]
    result = detector._calculate_rolling_correlation(short, short)
    assert result is None
    print("  [PASS] Returns None for insufficient data")


def test_divergence_detection():
    """Should detect divergence when correlation drops significantly."""
    db = get_test_db()
    mock_client = MagicMock()
    detector = CrossAssetDetector(mock_client, db)

    # EUR_USD going up, GBP_USD going down (divergence from 0.85 correlation)
    eur_candles = make_correlated_candles(30, 1.1000, 0.002)
    gbp_candles = make_divergent_candles(30, 1.3000, -0.002)

    mock_client.get_candles = MagicMock(side_effect=lambda inst, tf, count:
        eur_candles if "EUR" in inst else gbp_candles
    )

    signals = detector.analyze("EUR_USD", "LONG")

    # Should find divergence with GBP_USD
    assert len(signals) > 0, "Expected divergence signal"
    sig = signals[0]
    assert sig.divergence_sigma > 0
    assert sig.pair2 == "GBP_USD"
    print(f"  [PASS] Divergence detected: {sig.divergence_sigma:.2f}sigma, modifier={sig.confidence_modifier}")


def test_no_divergence_when_correlated():
    """Should have smaller divergence when correlation is normal."""
    db = get_test_db()
    mock_client = MagicMock()
    detector = CrossAssetDetector(mock_client, db)

    # Both trending up with same noise (high correlation)
    eur_candles = make_correlated_candles(30, 1.1000, 0.001, noise_seed=42)
    gbp_candles = make_correlated_candles(30, 1.3000, 0.001, noise_seed=42)

    mock_client.get_candles = MagicMock(side_effect=lambda inst, tf, count:
        eur_candles if "EUR" in inst else gbp_candles
    )

    # The correlation should be high, so modifier should be small
    modifier = detector.get_confidence_modifier("EUR_USD", "LONG")
    assert -10 <= modifier <= 15, f"Modifier out of bounds: {modifier}"
    print(f"  [PASS] Correlated pairs: modifier={modifier} (expected small)")


def test_confidence_modifier_bounds():
    """Modifier should be clamped to [-10, +15]."""
    db = get_test_db()
    mock_client = MagicMock()
    detector = CrossAssetDetector(mock_client, db)

    # Create extreme divergence
    eur_candles = make_correlated_candles(30, 1.1000, 0.005)
    gbp_candles = make_divergent_candles(30, 1.3000, -0.005)

    mock_client.get_candles = MagicMock(side_effect=lambda inst, tf, count:
        eur_candles if "EUR" in inst else gbp_candles
    )

    modifier = detector.get_confidence_modifier("EUR_USD", "LONG")
    assert -10 <= modifier <= 15, f"Modifier out of bounds: {modifier}"
    print(f"  [PASS] Confidence modifier in bounds: {modifier}")


def test_unknown_instrument():
    """Instrument not in any pair should return no signals."""
    db = get_test_db()
    mock_client = MagicMock()
    detector = CrossAssetDetector(mock_client, db)

    signals = detector.analyze("USD_JPY", "LONG")
    assert len(signals) == 0
    print("  [PASS] Unknown instrument returns no signals")


def test_caching():
    """Second call should use cached candles."""
    db = get_test_db()
    mock_client = MagicMock()
    detector = CrossAssetDetector(mock_client, db)

    candles = make_correlated_candles(30)
    mock_client.get_candles = MagicMock(return_value=candles)

    # First call
    detector._get_candles_cached("EUR_USD")
    # Second call should use cache
    detector._get_candles_cached("EUR_USD")

    assert mock_client.get_candles.call_count == 1
    print("  [PASS] Candle caching works")


def test_divergence_signal_to_dict():
    """DivergenceSignal.to_dict should be serializable."""
    sig = DivergenceSignal(
        pair1="EUR_USD",
        pair2="GBP_USD",
        divergence_sigma=2.5,
        expected_correlation=0.85,
        current_correlation=0.20,
        implication="EUR_USD_LONG_preference",
        confidence_modifier=10,
        reasoning="Test reasoning",
    )
    d = sig.to_dict()
    assert d["pair1"] == "EUR_USD"
    assert d["divergence_sigma"] == 2.5
    assert d["confidence_modifier"] == 10
    print("  [PASS] to_dict returns correct structure")


def test_db_logging():
    """Correlation snapshots should be logged to DB."""
    db = get_test_db()
    mock_client = MagicMock()
    detector = CrossAssetDetector(mock_client, db)

    detector._log_snapshot("EUR_USD", "GBP_USD", 0.30, 0.85, 3.67, "LONG_preference")

    with db._connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM correlation_snapshots")
        count = cursor.fetchone()[0]
        assert count == 1
    print("  [PASS] DB logging works")


def cleanup():
    test_path = Path(__file__).parent / "test_cross_asset.db"
    if test_path.exists():
        test_path.unlink()


if __name__ == "__main__":
    print("\n=== Testing Cross-Asset Detector (ISI Phase 4) ===\n")

    tests = [
        test_correlation_calculation,
        test_too_few_candles,
        test_divergence_detection,
        test_no_divergence_when_correlated,
        test_confidence_modifier_bounds,
        test_unknown_instrument,
        test_caching,
        test_divergence_signal_to_dict,
        test_db_logging,
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
