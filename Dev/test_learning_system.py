"""
Test script for the automatic learning system.

Tests:
1. ErrorAnalyzer - categorization of losses
2. trade_closed_handler - full lifecycle
3. Database logging
4. Lesson generation
"""

import sys
from pathlib import Path

# Add Dev to path
DEV_DIR = Path(__file__).parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from datetime import datetime
from src.analysis.error_analyzer import ErrorAnalyzer, ErrorCategory, analyze_trade_error
from src.trading.trade_lifecycle import trade_closed_handler, get_learning_stats
from src.utils.database import db
from src.core.settings_manager import settings_manager


def print_header(title: str):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_error_analyzer():
    """Test ErrorAnalyzer categorization."""
    print_header("TEST 1: ErrorAnalyzer Kategorization")

    analyzer = ErrorAnalyzer()

    # Test case 1: Overconfident trade
    print("\n[Test 1.1] High confidence loss...")
    trade_data = {
        "trade_id": "TEST001",
        "instrument": "EUR_USD",
        "direction": "LONG",
        "entry_price": 1.0850,
        "exit_price": 1.0820,
        "pnl": -150.0,
        "pnl_percent": -0.3,
        "confidence_score": 85,
        "sentiment_score": 0.5,
        "timestamp": "2026-01-30T10:00:00",
        "closed_at": "2026-01-30T14:00:00"
    }
    market_context = {
        "technical_score": 70,
        "adversarial_adjustment": -5,
        "atr": 20,  # 20 pips ATR - price move 30 is only 1.5x, not 2x (need >40 for news)
        "price_move_pips": 30
    }

    analysis = analyzer.analyze_loss(trade_data, market_context)
    print(f"   Category: {analysis.category.value}")
    print(f"   Root cause: {analysis.root_cause}")
    print(f"   Severity: {analysis.severity}")
    print(f"   Should add lesson: {analysis.should_add_lesson}")
    assert analysis.category == ErrorCategory.OVERCONFIDENT, f"Expected OVERCONFIDENT, got {analysis.category}"
    print("   [OK] Correctly identified as OVERCONFIDENT")

    # Test case 2: News spike
    print("\n[Test 1.2] News spike (large price move)...")
    trade_data["confidence_score"] = 60
    market_context["price_move_pips"] = 80
    market_context["atr"] = 20  # 20 pips ATR, move is 4x (80 > 40)

    analysis = analyzer.analyze_loss(trade_data, market_context)
    print(f"   Category: {analysis.category.value}")
    print(f"   Root cause: {analysis.root_cause}")
    assert analysis.category == ErrorCategory.NEWS_IGNORED, f"Expected NEWS_IGNORED, got {analysis.category}"
    print("   [OK] Correctly identified as NEWS_IGNORED")

    # Test case 3: Adversarial ignored
    print("\n[Test 1.3] Adversarial warning ignored...")
    trade_data["confidence_score"] = 65
    market_context["price_move_pips"] = 20
    market_context["atr"] = 15  # 15 pips ATR, move is ~1.3x (20 < 30, not news)
    market_context["adversarial_adjustment"] = -15

    analysis = analyzer.analyze_loss(trade_data, market_context)
    print(f"   Category: {analysis.category.value}")
    print(f"   Root cause: {analysis.root_cause}")
    assert analysis.category == ErrorCategory.ADVERSARIAL_IGNORED, f"Expected ADVERSARIAL_IGNORED, got {analysis.category}"
    print("   [OK] Correctly identified as ADVERSARIAL_IGNORED")

    # Test case 4: Technical failure
    print("\n[Test 1.4] Technical setup failure...")
    market_context["adversarial_adjustment"] = 0
    market_context["technical_score"] = 75

    analysis = analyzer.analyze_loss(trade_data, market_context)
    print(f"   Category: {analysis.category.value}")
    print(f"   Root cause: {analysis.root_cause}")
    assert analysis.category == ErrorCategory.TECHNICAL_FAILURE, f"Expected TECHNICAL_FAILURE, got {analysis.category}"
    print("   [OK] Correctly identified as TECHNICAL_FAILURE")

    print("\n[OK] All ErrorAnalyzer tests passed!")
    return True


def test_trade_closed_handler():
    """Test the full trade lifecycle handler."""
    print_header("TEST 2: Trade Closed Handler")

    # Simulate a losing trade
    print("\n[Test 2.1] Simulating losing trade closure...")

    result = trade_closed_handler(
        trade_id="TEST_LIFECYCLE_001",
        instrument="GBP_USD",
        direction="SHORT",
        entry_price=1.2650,
        exit_price=1.2700,
        pnl=-250.0,
        pnl_percent=-0.5,
        close_reason="SL",
        confidence_score=72,
        technical_score=68,
        sentiment_score=-0.3,
        adversarial_adjustment=-8
    )

    print(f"   Success: {result['success']}")
    print(f"   Trade updated: {result['trade_updated']}")
    print(f"   Error logged: {result['error_logged']}")
    print(f"   Lesson added: {result['lesson_added']}")
    print(f"   Error category: {result['error_category']}")

    assert result['success'], "Handler should succeed"
    assert result['error_logged'], "Error should be logged for loss"
    print("\n[OK] Trade closed handler works correctly!")

    # Test winning trade (should not log error)
    print("\n[Test 2.2] Simulating winning trade closure...")

    result = trade_closed_handler(
        trade_id="TEST_LIFECYCLE_002",
        instrument="EUR_USD",
        direction="LONG",
        entry_price=1.0850,
        exit_price=1.0900,
        pnl=250.0,
        pnl_percent=0.5,
        close_reason="TP",
        confidence_score=75
    )

    print(f"   Success: {result['success']}")
    print(f"   Error logged: {result['error_logged']}")

    assert result['success'], "Handler should succeed"
    assert not result['error_logged'], "Error should NOT be logged for win"
    print("\n[OK] Winning trade correctly handled (no error logged)!")

    return True


def test_database_integration():
    """Test database operations."""
    print_header("TEST 3: Database Integration")

    # Check errors table
    print("\n[Test 3.1] Checking errors in database...")
    errors = db.find_similar_errors("GBP_USD", limit=5)
    print(f"   Found {len(errors)} error(s) for GBP_USD")

    if errors:
        latest = errors[0]
        print(f"   Latest error:")
        print(f"     - Category: {latest.get('error_category')}")
        print(f"     - Root cause: {latest.get('root_cause', '')[:50]}...")
        print(f"     - Lesson: {latest.get('lessons', '')[:50]}...")

    # Check error categories summary
    print("\n[Test 3.2] Error categories summary...")
    categories = db.get_error_categories_summary()
    print(f"   Categories: {categories}")

    # Check performance stats
    print("\n[Test 3.3] Performance stats...")
    stats = db.get_performance_stats()
    print(f"   Total trades: {stats.get('total_trades', 0)}")
    print(f"   Win rate: {stats.get('win_rate', 0)}%")

    print("\n[OK] Database integration works!")
    return True


def test_lesson_generation():
    """Test lesson text generation."""
    print_header("TEST 4: Lesson Generation")

    analyzer = ErrorAnalyzer()

    # Test significant loss (should generate lesson)
    print("\n[Test 4.1] Testing significant loss lesson generation...")
    trade_data = {
        "trade_id": "TEST_LESSON_001",
        "instrument": "USD_JPY",
        "direction": "LONG",
        "entry_price": 150.50,
        "exit_price": 149.00,
        "pnl": -750.0,
        "pnl_percent": -1.5,  # > 1% = significant
        "confidence_score": 78,
        "sentiment_score": 0.4,
        "timestamp": "2026-01-30T09:00:00",
        "closed_at": "2026-01-30T15:00:00"
    }
    market_context = {
        "technical_score": 65,
        "adversarial_adjustment": -5,
        "atr": 50,  # 50 pips ATR
        "price_move_pips": 150  # 150 pips > 100 (2x ATR) = news spike
    }

    analysis = analyzer.analyze_loss(trade_data, market_context)

    print(f"   Category: {analysis.category.value}")
    print(f"   Should add lesson: {analysis.should_add_lesson}")
    print(f"   Severity: {analysis.severity}")

    if analysis.lesson_text:
        print(f"\n   Generated lesson preview:")
        print("   " + "-"*50)
        # Print first few lines
        lines = analysis.lesson_text.split('\n')[:8]
        for line in lines:
            print(f"   {line}")
        print("   ...")

    assert analysis.should_add_lesson, "Significant loss should trigger lesson"
    assert analysis.lesson_text is not None, "Lesson text should be generated"
    print("\n[OK] Lesson generation works!")

    return True


def test_learning_stats():
    """Test learning statistics function."""
    print_header("TEST 5: Learning Stats")

    stats = get_learning_stats()

    print(f"\n   Error categories: {stats.get('error_categories', {})}")
    print(f"   Total errors logged: {stats.get('total_errors_logged', 0)}")
    print(f"   Top repeated errors: {stats.get('top_repeated_errors', [])}")

    print("\n[OK] Learning stats retrieved!")
    return True


def test_rag_query():
    """Test RAG query for similar errors."""
    print_header("TEST 6: RAG Query Simulation")

    # Simulate what happens during analysis
    print("\n   Querying similar errors for EUR_USD LONG...")

    similar_errors = db.find_similar_errors("EUR_USD", "LONG", limit=3)

    if similar_errors:
        print(f"   Found {len(similar_errors)} similar error(s):")
        for i, err in enumerate(similar_errors, 1):
            print(f"\n   Error {i}:")
            print(f"     Category: {err.get('error_category')}")
            print(f"     Direction: {err.get('direction')}")
            print(f"     Loss: {err.get('loss_percent', 0):.2f}%")
            print(f"     Lesson: {err.get('lessons', 'N/A')[:60]}...")
    else:
        print("   No similar errors found (this is OK for fresh database)")

    # Calculate RAG penalty
    rag_warnings = len(similar_errors)
    rag_penalty = min(rag_warnings * 10, 30) * -1
    print(f"\n   RAG warnings: {rag_warnings}")
    print(f"   Confidence penalty: {rag_penalty}")

    print("\n[OK] RAG query works!")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  AUTOMATIC LEARNING SYSTEM - TEST SUITE")
    print("="*60)
    print(f"\n  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Database: {db.db_path}")

    tests = [
        ("ErrorAnalyzer", test_error_analyzer),
        ("Trade Closed Handler", test_trade_closed_handler),
        ("Database Integration", test_database_integration),
        ("Lesson Generation", test_lesson_generation),
        ("Learning Stats", test_learning_stats),
        ("RAG Query", test_rag_query),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n[FAIL] {name}: {e}")
            results.append((name, False))

    # Summary
    print_header("TEST SUMMARY")

    passed = sum(1 for _, p in results if p)
    total = len(results)

    for name, p in results:
        status = "[OK]" if p else "[FAIL]"
        print(f"   {status} {name}")

    print(f"\n   Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n   [SUCCESS] All tests passed!")
        print("   Learning system is ready for use.")
    else:
        print("\n   [WARNING] Some tests failed. Check output above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
