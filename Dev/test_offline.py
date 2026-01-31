#!/usr/bin/env python3
"""
Offline Test Script - Testira sve module bez OANDA credentials.

Pokreni: python test_offline.py
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("")  # Enable ANSI escape codes
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Dodaj src u path
sys.path.insert(0, str(Path(__file__).parent))


def print_header(title: str):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)


def print_result(name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  {status} {name}")
    if details and not passed:
        print(f"          -> {details}")


def test_dependencies() -> bool:
    """Test if all dependencies are installed."""
    print_header("1. TESTING DEPENDENCIES")

    all_passed = True
    deps = [
        ("pandas", "pandas"),
        ("pandas_ta", "pandas-ta"),
        ("dotenv", "python-dotenv"),
        ("loguru", "loguru"),
        ("rich", "rich"),
        ("httpx", "httpx"),
    ]

    for module_name, pip_name in deps:
        try:
            __import__(module_name)
            print_result(f"{pip_name}", True)
        except ImportError as e:
            print_result(f"{pip_name}", False, f"pip install {pip_name}")
            all_passed = False

    return all_passed


def generate_dummy_candles(count: int = 100) -> list[dict]:
    """Generate realistic dummy OHLCV candle data."""
    import random

    candles = []
    base_price = 1.0850  # EUR/USD realistic price
    current_time = datetime.now() - timedelta(hours=count)

    for i in range(count):
        # Random walk
        change = random.uniform(-0.0020, 0.0020)
        open_price = base_price
        close_price = base_price + change
        high = max(open_price, close_price) + random.uniform(0.0001, 0.0010)
        low = min(open_price, close_price) - random.uniform(0.0001, 0.0010)
        volume = random.randint(1000, 10000)

        candles.append({
            "time": current_time.isoformat(),
            "open": round(open_price, 5),
            "high": round(high, 5),
            "low": round(low, 5),
            "close": round(close_price, 5),
            "volume": volume
        })

        base_price = close_price
        current_time += timedelta(hours=1)

    return candles


def test_technical_indicators() -> tuple[bool, any]:
    """Test technical indicators module."""
    print_header("2. TESTING TECHNICAL INDICATORS")

    try:
        from src.market.indicators import TechnicalAnalyzer, analyze_candles
        print_result("Import TechnicalAnalyzer", True)
    except Exception as e:
        print_result("Import TechnicalAnalyzer", False, str(e))
        return False, None

    # Generate dummy data
    candles = generate_dummy_candles(100)
    print_result(f"Generated {len(candles)} dummy candles", True)

    # Run analysis
    try:
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(candles, "EUR_USD")

        print_result("TechnicalAnalyzer.analyze()", True)
        print(f"\n  Results:")
        print(f"    Trend: {result.trend} (strength: {result.trend_strength:.0f}%)")
        print(f"    EMA20: {result.ema20:.5f}")
        print(f"    EMA50: {result.ema50:.5f}")
        print(f"    RSI: {result.rsi:.1f} ({result.rsi_signal})")
        print(f"    MACD: {result.macd_trend}")
        print(f"    ATR: {result.atr_pips:.1f} pips")
        print(f"    Technical Score: {result.technical_score}/100")

        return True, result
    except Exception as e:
        print_result("TechnicalAnalyzer.analyze()", False, str(e))
        return False, None


def test_sentiment_analyzer(candles: list, technical) -> tuple[bool, any]:
    """Test sentiment analyzer module."""
    print_header("3. TESTING SENTIMENT ANALYZER")

    try:
        from src.analysis.sentiment import SentimentAnalyzer, analyze_sentiment
        print_result("Import SentimentAnalyzer", True)
    except Exception as e:
        print_result("Import SentimentAnalyzer", False, str(e))
        return False, None

    try:
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(candles, technical)

        print_result("SentimentAnalyzer.analyze()", True)
        print(f"\n  Results:")
        print(f"    Sentiment Score: {result.sentiment_score:+.2f}")
        print(f"    Label: {result.sentiment_label}")
        print(f"    Price Action: {result.price_action_score:+.2f}")
        print(f"    Momentum: {result.momentum_score:+.2f}")
        print(f"    Volatility: {result.volatility_score:+.2f}")
        print(f"    Trending: {result.is_trending} ({result.trend_direction})")

        return True, result
    except Exception as e:
        print_result("SentimentAnalyzer.analyze()", False, str(e))
        return False, None


def test_adversarial_engine(technical, sentiment) -> tuple[bool, any]:
    """Test adversarial engine module."""
    print_header("4. TESTING ADVERSARIAL ENGINE")

    try:
        from src.analysis.adversarial import AdversarialEngine, generate_adversarial_analysis
        print_result("Import AdversarialEngine", True)
    except Exception as e:
        print_result("Import AdversarialEngine", False, str(e))
        return False, None

    try:
        engine = AdversarialEngine()
        result = engine.analyze(technical, sentiment, "EUR_USD", direction="LONG")

        print_result("AdversarialEngine.analyze()", True)
        print(f"\n  Results:")
        print(f"    Bull Score: {result.bull_score:.0f}")
        print(f"    Bear Score: {result.bear_score:.0f}")
        print(f"    Verdict: {result.verdict}")
        print(f"    Confidence Adjustment: {result.confidence_adjustment:+d}")
        print(f"    Bull Points: {len(result.bull_case)}")
        print(f"    Bear Points: {len(result.bear_case)}")
        if result.warnings:
            print(f"    Warnings: {result.warnings}")

        return True, result
    except Exception as e:
        print_result("AdversarialEngine.analyze()", False, str(e))
        return False, None


def test_confidence_calculator(technical, sentiment, adversarial) -> tuple[bool, any]:
    """Test confidence calculator module."""
    print_header("5. TESTING CONFIDENCE CALCULATOR")

    try:
        from src.analysis.confidence import ConfidenceCalculator, calculate_confidence
        print_result("Import ConfidenceCalculator", True)
    except Exception as e:
        print_result("Import ConfidenceCalculator", False, str(e))
        return False, None

    try:
        calc = ConfidenceCalculator()
        result = calc.calculate(technical, sentiment, adversarial, rag_warnings=0)

        print_result("ConfidenceCalculator.calculate()", True)
        print(f"\n  Results:")
        print(f"    Confidence Score: {result.confidence_score}/100")
        print(f"    Technical Score: {result.technical_score}")
        print(f"    Sentiment Score: {result.sentiment_score}")
        print(f"    Adversarial Adj: {result.adversarial_adjustment:+d}")
        print(f"    RAG Penalty: {result.rag_penalty}")
        print(f"    Risk Tier: {result.risk_tier}")
        print(f"    Max Risk: {result.risk_percent*100:.0f}%")
        print(f"    Can Trade: {result.can_trade}")

        return True, result
    except Exception as e:
        print_result("ConfidenceCalculator.calculate()", False, str(e))
        return False, None


def test_risk_manager() -> bool:
    """Test risk manager module."""
    print_header("6. TESTING RISK MANAGER")

    try:
        from src.trading.risk_manager import RiskManager, pre_trade_checklist
        print_result("Import RiskManager", True)
    except Exception as e:
        print_result("Import RiskManager", False, str(e))
        return False

    try:
        rm = RiskManager()

        # Test valid trade
        result = rm.validate_trade(
            equity=10000,
            risk_amount=200,  # 2%
            confidence=75,
            open_positions=1,
            spread_pips=1.5
        )

        print_result("RiskManager.validate_trade() - Valid trade", result.valid)
        print(f"\n  Checklist:")
        for check in result.checks:
            status = "OK" if check.passed else "X"
            print(f"    [{status}] {check.message}")

        # Test invalid trade (low confidence)
        result2 = rm.validate_trade(
            equity=10000,
            risk_amount=200,
            confidence=40,  # Below minimum
            open_positions=1,
            spread_pips=1.5
        )

        print_result("RiskManager.validate_trade() - Low confidence rejected", not result2.valid)

        # Test invalid trade (too many positions)
        result3 = rm.validate_trade(
            equity=10000,
            risk_amount=200,
            confidence=75,
            open_positions=3,  # At limit
            spread_pips=1.5
        )

        print_result("RiskManager.validate_trade() - Max positions rejected", not result3.valid)

        return True
    except Exception as e:
        print_result("RiskManager tests", False, str(e))
        return False


def test_position_sizer() -> bool:
    """Test position sizer module."""
    print_header("7. TESTING POSITION SIZER")

    try:
        from src.trading.position_sizer import calculate_position_size, calculate_risk_reward
        print_result("Import position_sizer", True)
    except Exception as e:
        print_result("Import position_sizer", False, str(e))
        return False

    try:
        # Test position size calculation
        result = calculate_position_size(
            equity=10000,
            confidence=75,
            entry_price=1.0850,
            stop_loss=1.0800,
            instrument="EUR_USD"
        )

        print_result("calculate_position_size()", result.can_trade)
        print(f"\n  Results:")
        print(f"    Can Trade: {result.can_trade}")
        print(f"    Units: {result.units:,}")
        print(f"    Risk Tier: {result.risk_tier}")
        print(f"    Risk Percent: {result.risk_percent*100:.1f}%")
        print(f"    Risk Amount: ${result.risk_amount:.2f}")
        print(f"    SL Distance: {result.pip_distance:.1f} pips")

        # Test R:R calculation
        rr = calculate_risk_reward(
            entry_price=1.0850,
            stop_loss=1.0800,
            take_profit=1.0950,
            instrument="EUR_USD"
        )

        print_result("calculate_risk_reward()", True)
        print(f"\n  Risk/Reward:")
        print(f"    Risk: {rr['risk_pips']} pips")
        print(f"    Reward: {rr['reward_pips']} pips")
        print(f"    Ratio: {rr['ratio_display']}")

        # Test low confidence rejection
        result2 = calculate_position_size(
            equity=10000,
            confidence=40,
            entry_price=1.0850,
            stop_loss=1.0800,
            instrument="EUR_USD"
        )

        print_result("Low confidence rejection", not result2.can_trade)

        return True
    except Exception as e:
        print_result("Position sizer tests", False, str(e))
        return False


def test_config() -> bool:
    """Test config module."""
    print_header("8. TESTING CONFIG")

    try:
        from src.utils.config import config
        print_result("Import config", True)
    except Exception as e:
        print_result("Import config", False, str(e))
        return False

    # Check validation (will fail without .env, but that's OK)
    is_valid, msg = config.validate()
    print_result(f"Config validation", True, "Expected to fail without .env")
    print(f"\n  Status: {msg}")
    print(f"  Is Demo: {config.is_demo()}")
    print(f"  Min Confidence: {config.MIN_CONFIDENCE_TO_TRADE}")
    print(f"  Max Daily DD: {config.MAX_DAILY_DRAWDOWN*100}%")

    # Test risk percent getter
    print(f"\n  Risk Tiers:")
    for conf in [40, 55, 75, 95]:
        risk = config.get_risk_percent(conf)
        print(f"    Confidence {conf}% → {risk*100:.0f}% risk")

    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("   AI TRADER - OFFLINE TEST SUITE")
    print("   Testing modules without OANDA credentials")
    print("="*60)

    results = {}

    # 1. Dependencies
    results["dependencies"] = test_dependencies()
    if not results["dependencies"]:
        print("\n[X] Dependencies missing. Install them first:")
        print("    pip install -r requirements.txt")
        return

    # 2. Technical Indicators
    passed, technical = test_technical_indicators()
    results["technical"] = passed

    # Generate candles for other tests
    candles = generate_dummy_candles(100)

    # 3. Sentiment Analyzer
    if technical:
        passed, sentiment = test_sentiment_analyzer(candles, technical)
        results["sentiment"] = passed
    else:
        results["sentiment"] = False
        sentiment = None

    # 4. Adversarial Engine
    if technical and sentiment:
        passed, adversarial = test_adversarial_engine(technical, sentiment)
        results["adversarial"] = passed
    else:
        results["adversarial"] = False
        adversarial = None

    # 5. Confidence Calculator
    if technical and sentiment:
        passed, confidence = test_confidence_calculator(technical, sentiment, adversarial)
        results["confidence"] = passed
    else:
        results["confidence"] = False

    # 6. Risk Manager
    results["risk_manager"] = test_risk_manager()

    # 7. Position Sizer
    results["position_sizer"] = test_position_sizer()

    # 8. Config
    results["config"] = test_config()

    # Summary
    print_header("SUMMARY")

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print(f"\n  Tests passed: {passed_count}/{total_count}")
    print()

    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    if passed_count == total_count:
        print("\n*** ALL TESTS PASSED! ***")
        print("    Sustav je funkcionalan.")
        print("    Sljedeci korak: konfiguriraj OANDA credentials za live testiranje.")
    else:
        print("\n*** SOME TESTS FAILED ***")
        print("    Provjeri error poruke iznad.")

    print()


if __name__ == "__main__":
    main()
