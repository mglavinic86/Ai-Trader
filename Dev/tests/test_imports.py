"""
Smoke test for all module imports.

Run with: python -m pytest tests/test_imports.py -v
Or simply: python tests/test_imports.py
"""

import sys
from pathlib import Path

# Add Dev to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_trading_module():
    """Test trading module imports."""
    from src.trading import MT5Client, MT5Error
    from src.trading import OrderManager, OrderResult
    from src.trading import RiskManager, ValidationResult
    from src.trading import calculate_position_size, PositionSizeResult
    from src.trading import calculate_risk_reward
    from src.trading import pre_trade_checklist

    assert MT5Client is not None
    assert OrderManager is not None
    assert RiskManager is not None
    print("[OK] Trading module imports successful")


def test_analysis_module():
    """Test analysis module imports."""
    from src.analysis import SentimentAnalyzer, SentimentResult, analyze_sentiment
    from src.analysis import AdversarialEngine, AdversarialResult
    from src.analysis import ConfidenceCalculator, ConfidenceResult, calculate_confidence
    from src.analysis import ErrorAnalyzer, analyze_trade_error

    assert SentimentAnalyzer is not None
    assert AdversarialEngine is not None
    assert ConfidenceCalculator is not None
    print("[OK] Analysis module imports successful")


def test_market_module():
    """Test market module imports."""
    from src.market import TechnicalAnalyzer, TechnicalAnalysis, analyze_candles

    assert TechnicalAnalyzer is not None
    print("[OK] Market module imports successful")


def test_utils_module():
    """Test utils module imports."""
    from src.utils import config, logger, db
    from src.utils import format_price, generate_trade_id

    assert config is not None
    assert logger is not None
    print("[OK] Utils module imports successful")


def test_root_package():
    """Test root package imports (convenience imports)."""
    from src import (
        MT5Client, OrderManager, RiskManager,
        calculate_position_size, calculate_confidence,
        config, logger, db
    )

    assert MT5Client is not None
    assert OrderManager is not None
    assert RiskManager is not None
    print("[OK] Root package imports successful")


def test_position_sizer_logic():
    """Test position sizer basic logic."""
    from src.trading import calculate_position_size

    # Test with valid inputs
    result = calculate_position_size(
        equity=10000,
        confidence=75,
        entry_price=1.0843,
        stop_loss=1.0800,
        instrument="EUR_USD"
    )

    assert result.can_trade == True
    assert result.units > 0
    assert result.risk_percent == 0.02  # Tier 2 = 2%
    assert result.risk_tier == "TIER 2 (Good Confidence: 2%)"
    print(f"[OK] Position sizer: {result.units} units, {result.risk_percent*100}% risk")


def test_risk_manager_logic():
    """Test risk manager validation."""
    from src.trading import RiskManager

    rm = RiskManager()

    # Test valid trade
    result = rm.validate_trade(
        equity=10000,
        risk_amount=200,  # 2%
        confidence=75,
        open_positions=0,
        spread_pips=1.5,
        daily_pnl=0,
        weekly_pnl=0
    )

    assert result.valid == True
    print(f"[OK] Risk manager: {len(result.checks)} checks passed")


def test_low_confidence_rejection():
    """Test that low confidence trades are rejected."""
    from src.trading import calculate_position_size

    result = calculate_position_size(
        equity=10000,
        confidence=40,  # Below 50%
        entry_price=1.0843,
        stop_loss=1.0800,
        instrument="EUR_USD"
    )

    assert result.can_trade == False
    assert "below minimum" in result.reason.lower()
    print("[OK] Low confidence correctly rejected")


if __name__ == "__main__":
    print("=" * 60)
    print("AI Trader - Import Smoke Test")
    print("=" * 60)

    tests = [
        test_trading_module,
        test_analysis_module,
        test_market_module,
        test_utils_module,
        test_root_package,
        test_position_sizer_logic,
        test_risk_manager_logic,
        test_low_confidence_rejection,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
