"""Tests for Bayesian Confidence Calibrator (ISI Phase 1)."""

import sys
import os
import math
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.confidence_calibrator import ConfidenceCalibrator
from src.utils.database import Database


def get_test_db():
    """Create a fresh in-memory-like test database."""
    test_path = Path(__file__).parent / "test_calibrator.db"
    if test_path.exists():
        test_path.unlink()
    return Database(test_path)


def test_uncalibrated_returns_original():
    """Uncalibrated system should return raw confidence unchanged."""
    db = get_test_db()
    cal = ConfidenceCalibrator(db)

    assert not cal.is_fitted
    assert cal.calibrate(85) == 85
    assert cal.calibrate(50) == 50
    assert cal.calibrate(0) == 0
    assert cal.calibrate(100) == 100
    print("  [PASS] Uncalibrated returns original")


def test_calibrate_returns_int_0_100():
    """Calibrated score must be int in [0, 100]."""
    db = get_test_db()
    cal = ConfidenceCalibrator(db)

    # Manually set fitted params
    cal.param_a = 2.0
    cal.param_b = -1.0
    cal.is_fitted = True

    for raw in range(0, 101, 10):
        result = cal.calibrate(raw)
        assert isinstance(result, int), f"Expected int, got {type(result)}"
        assert 0 <= result <= 100, f"Out of range: {result}"
    print("  [PASS] Calibrate returns int 0-100")


def test_fit_needs_min_trades():
    """Fit should refuse with too few trades."""
    db = get_test_db()
    cal = ConfidenceCalibrator(db)

    # Insert fewer than min_trades
    with db._connection() as conn:
        cursor = conn.cursor()
        for i in range(10):
            cursor.execute("""
                INSERT INTO trades (trade_id, timestamp, instrument, direction,
                    confidence_score, pnl, status, closed_at)
                VALUES (?, ?, 'EUR_USD', 'LONG', ?, ?, 'CLOSED', ?)
            """, (f"test_{i}", "2026-01-01", 80, 10.0 if i < 5 else -10.0, "2026-01-01"))

    result = cal.fit()
    assert not result["fitted"]
    assert "Need" in result["reason"]
    print("  [PASS] Fit needs minimum trades")


def test_fit_with_data():
    """Fit should work with enough trades and produce reasonable params."""
    db = get_test_db()
    cal = ConfidenceCalibrator(db)
    cal.min_trades_to_fit = 10  # Lower for testing

    # Insert 30 trades with 50% win rate
    with db._connection() as conn:
        cursor = conn.cursor()
        for i in range(30):
            conf = 70 + (i % 20)  # 70-89
            pnl = 50.0 if i % 2 == 0 else -30.0
            cursor.execute("""
                INSERT INTO trades (trade_id, timestamp, instrument, direction,
                    confidence_score, pnl, status, closed_at)
                VALUES (?, ?, 'EUR_USD', 'LONG', ?, ?, 'CLOSED', ?)
            """, (f"fit_{i}", "2026-01-01", conf, pnl, "2026-01-01"))

    result = cal.fit()
    assert result["fitted"]
    assert result["training_trades"] == 30
    assert 0 < result["brier_score"] < 1.0
    assert cal.is_fitted
    print(f"  [PASS] Fit with data: A={result['param_a']:.4f}, B={result['param_b']:.4f}, Brier={result['brier_score']:.4f}")


def test_refit_trigger():
    """Should trigger refit after enough new trades."""
    db = get_test_db()
    cal = ConfidenceCalibrator(db)
    cal._last_trade_count = 30
    cal.refit_interval = 10

    # Not enough new trades
    with db._connection() as conn:
        cursor = conn.cursor()
        for i in range(35):
            cursor.execute("""
                INSERT INTO trades (trade_id, timestamp, instrument, direction,
                    confidence_score, pnl, status, closed_at)
                VALUES (?, ?, 'EUR_USD', 'LONG', 80, 10, 'CLOSED', ?)
            """, (f"refit_{i}", "2026-01-01", "2026-01-01"))

    assert not cal.should_refit()  # 35 - 30 = 5 < 10

    # Add more
    with db._connection() as conn:
        cursor = conn.cursor()
        for i in range(10):
            cursor.execute("""
                INSERT INTO trades (trade_id, timestamp, instrument, direction,
                    confidence_score, pnl, status, closed_at)
                VALUES (?, ?, 'EUR_USD', 'LONG', 80, 10, 'CLOSED', ?)
            """, (f"refit_extra_{i}", "2026-01-01", "2026-01-01"))

    assert cal.should_refit()  # 45 - 30 = 15 >= 10
    print("  [PASS] Refit trigger logic")


def test_get_stats():
    """Stats should return dict with expected keys."""
    db = get_test_db()
    cal = ConfidenceCalibrator(db)
    stats = cal.get_stats()

    assert "is_fitted" in stats
    assert "param_a" in stats
    assert "param_b" in stats
    assert isinstance(stats["is_fitted"], bool)
    print("  [PASS] get_stats returns expected keys")


def cleanup():
    """Remove test database."""
    test_path = Path(__file__).parent / "test_calibrator.db"
    if test_path.exists():
        test_path.unlink()


if __name__ == "__main__":
    print("\n=== Testing Confidence Calibrator (ISI Phase 1) ===\n")

    tests = [
        test_uncalibrated_returns_original,
        test_calibrate_returns_int_0_100,
        test_fit_needs_min_trades,
        test_fit_with_data,
        test_refit_trigger,
        test_get_stats,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            failed += 1

    cleanup()
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print(f"{'='*50}\n")

    sys.exit(1 if failed > 0 else 0)
