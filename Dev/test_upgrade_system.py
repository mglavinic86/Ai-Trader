"""
Test script for Self-Upgrade System.

Tests all components:
1. BaseFilter and FilterRegistry
2. PerformanceAnalyzer
3. CodeGenerator
4. CodeValidator
5. UpgradeExecutor
6. UpgradeManager
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def test_base_filter():
    """Test BaseFilter and FilterResult."""
    print("\n" + "="*60)
    print("TEST 1: BaseFilter and FilterResult")
    print("="*60)

    from src.upgrade.base_filter import BaseFilter, FilterResult, FilterStats

    # Test FilterResult
    result = FilterResult(passed=True)
    assert result.passed == True
    print("  [OK] FilterResult(passed=True)")

    result = FilterResult(passed=False, reason="Test reason", filter_name="test_filter")
    assert result.passed == False
    assert result.reason == "Test reason"
    print("  [OK] FilterResult(passed=False, reason=...)")

    # Test FilterStats
    stats = FilterStats()
    stats.signals_checked = 100
    stats.signals_blocked = 25
    stats.true_positives = 20
    stats.false_positives = 5

    assert stats.block_rate == 25.0
    assert stats.accuracy == 80.0
    print("  [OK] FilterStats calculations")

    print("\n  PASSED: BaseFilter module works correctly!")
    return True


def test_filter_registry():
    """Test FilterRegistry."""
    print("\n" + "="*60)
    print("TEST 2: FilterRegistry")
    print("="*60)

    from src.upgrade.filter_registry import FilterRegistry
    from src.upgrade.base_filter import BaseFilter, FilterResult

    # Create a test filter
    class TestFilter(BaseFilter):
        def __init__(self):
            super().__init__(
                name="test_filter",
                description="Test filter",
                priority=50
            )
            self.block_instrument = "TEST_USD"

        def check(self, signal_data: dict) -> FilterResult:
            if signal_data.get("instrument") == self.block_instrument:
                return FilterResult(passed=False, reason="Blocked TEST_USD")
            return FilterResult(passed=True)

    # Test registry
    registry = FilterRegistry()
    test_filter = TestFilter()
    registry.register(test_filter)

    assert registry.get("test_filter") is not None
    print("  [OK] Filter registered")

    # Test filter chain
    result = registry.run_all_filters({"instrument": "EUR_USD"})
    assert result.passed == True
    print("  [OK] Signal passed for EUR_USD")

    result = registry.run_all_filters({"instrument": "TEST_USD"})
    assert result.passed == False
    assert result.blocking_filter == "test_filter"
    print("  [OK] Signal blocked for TEST_USD")

    # Test stats
    stats = registry.get_stats()
    assert stats["total_filters"] >= 1
    print(f"  [OK] Registry stats: {stats['total_filters']} filters")

    # Cleanup
    registry.unregister("test_filter")

    print("\n  PASSED: FilterRegistry works correctly!")
    return True


def test_builtin_filters():
    """Test builtin filters load correctly."""
    print("\n" + "="*60)
    print("TEST 3: Builtin Filters")
    print("="*60)

    from src.upgrade.filter_registry import get_filter_registry

    registry = get_filter_registry()
    stats = registry.get_stats()

    print(f"  Total filters: {stats['total_filters']}")
    print(f"  Builtin filters: {stats['builtin_count']}")
    print(f"  AI-generated filters: {stats['ai_generated_count']}")

    # List all filters
    for f in registry.get_all():
        print(f"    - {f.name} (priority={f.priority}, type={f.filter_type})")

    print("\n  PASSED: Builtin filters loaded!")
    return True


def test_performance_analyzer():
    """Test PerformanceAnalyzer."""
    print("\n" + "="*60)
    print("TEST 4: PerformanceAnalyzer")
    print("="*60)

    from src.upgrade.performance_analyzer import PerformanceAnalyzer, LosingPattern

    analyzer = PerformanceAnalyzer()

    # Test pattern creation
    pattern = LosingPattern(
        pattern_type="instrument",
        pattern_key="EUR_USD",
        total_trades=10,
        losing_trades=8,
        total_loss=-200.0,
        avg_loss=-25.0,
        win_rate=15.0  # Must be < 20 for CRITICAL
    )

    assert pattern.severity == "CRITICAL"
    print(f"  [OK] Pattern severity: {pattern.severity}")

    # Test analysis (may return empty if no recent trades)
    patterns = analyzer.analyze_recent_performance(days=7)
    print(f"  [OK] Analyzed recent performance: {len(patterns)} patterns found")

    # Get summary
    summary = analyzer.get_analysis_summary()
    print(f"  [OK] Analysis summary: {summary['total_patterns']} total patterns")

    print("\n  PASSED: PerformanceAnalyzer works correctly!")
    return True


def test_code_validator():
    """Test CodeValidator."""
    print("\n" + "="*60)
    print("TEST 5: CodeValidator")
    print("="*60)

    from src.upgrade.code_validator import CodeValidator

    validator = CodeValidator()

    # Test valid code
    valid_code = '''
from src.upgrade.base_filter import BaseFilter, FilterResult
from datetime import datetime

class TestFilter(BaseFilter):
    def __init__(self):
        super().__init__(name="test", description="Test", priority=50)

    def check(self, signal_data: dict) -> FilterResult:
        return FilterResult(passed=True)
'''

    result = validator.validate(valid_code)
    assert result.ast_valid == True
    assert result.has_base_filter == True
    assert result.has_check_method == True
    assert result.is_valid == True
    print("  [OK] Valid code passes validation")

    # Test code with forbidden import
    bad_code_import = '''
import os
from src.upgrade.base_filter import BaseFilter, FilterResult

class BadFilter(BaseFilter):
    def check(self, signal_data: dict) -> FilterResult:
        os.system("rm -rf /")  # Evil!
        return FilterResult(passed=True)
'''

    result = validator.validate(bad_code_import)
    assert result.is_valid == False
    assert any("os" in e.lower() for e in result.errors)
    print("  [OK] Code with 'import os' rejected")

    # Test code with exec
    bad_code_exec = '''
from src.upgrade.base_filter import BaseFilter, FilterResult

class BadFilter(BaseFilter):
    def check(self, signal_data: dict) -> FilterResult:
        exec("print('hacked')")
        return FilterResult(passed=True)
'''

    result = validator.validate(bad_code_exec)
    assert result.is_valid == False
    assert any("exec" in e.lower() for e in result.errors)
    print("  [OK] Code with 'exec()' rejected")

    # Test code with open
    bad_code_open = '''
from src.upgrade.base_filter import BaseFilter, FilterResult

class BadFilter(BaseFilter):
    def check(self, signal_data: dict) -> FilterResult:
        f = open("/etc/passwd", "r")
        return FilterResult(passed=True)
'''

    result = validator.validate(bad_code_open)
    assert result.is_valid == False
    assert any("open" in e.lower() for e in result.errors)
    print("  [OK] Code with 'open()' rejected")

    # Test code missing BaseFilter
    bad_code_no_base = '''
class NotAFilter:
    def check(self, signal_data: dict):
        return True
'''

    result = validator.validate(bad_code_no_base)
    assert result.is_valid == False
    assert result.has_base_filter == False
    print("  [OK] Code without BaseFilter inheritance rejected")

    print("\n  PASSED: CodeValidator security checks work!")
    return True


def test_code_generator():
    """Test CodeGenerator."""
    print("\n" + "="*60)
    print("TEST 6: CodeGenerator")
    print("="*60)

    from src.upgrade.code_generator import CodeGenerator
    from src.upgrade.performance_analyzer import FilterProposal, LosingPattern

    generator = CodeGenerator()

    # Create a test proposal
    pattern = LosingPattern(
        pattern_type="instrument",
        pattern_key="TEST_USD",
        total_trades=10,
        losing_trades=8,
        total_loss=-200.0,
        avg_loss=-25.0,
        win_rate=20.0
    )

    proposal = FilterProposal(
        proposal_id="test_001",
        pattern=pattern,
        filter_name="block_test_usd_filter",
        filter_description="Block TEST_USD due to poor performance",
        filter_logic="Block instrument == 'TEST_USD'"
    )

    # Generate code synchronously (template-based)
    result = generator.generate_filter_code_sync(proposal)

    if not result.success:
        print(f"  [DEBUG] Generation failed: {result.error}")
        print(f"  [DEBUG] Safety violations: {result.safety_violations}")

    assert result.success == True, f"Code generation failed: {result.error}"
    assert "class BlockTestUsdFilter" in result.code
    assert "BaseFilter" in result.code
    assert "def check" in result.code
    print("  [OK] Generated instrument filter code")
    print(f"  [OK] Code length: {len(result.code)} chars")

    # Validate the generated code
    from src.upgrade.code_validator import CodeValidator
    validator = CodeValidator()
    validation = validator.validate(result.code)

    assert validation.is_valid == True
    print("  [OK] Generated code passes validation")

    # Test session filter generation
    session_pattern = LosingPattern(
        pattern_type="session",
        pattern_key="london",
        total_trades=15,
        losing_trades=10,
        total_loss=-150.0,
        avg_loss=-15.0,
        win_rate=33.3,
        details={"instruments_affected": ["EUR_USD", "GBP_USD"]}
    )

    session_proposal = FilterProposal(
        proposal_id="test_002",
        pattern=session_pattern,
        filter_name="block_london_session_filter",
        filter_description="Block london session",
        filter_logic="Block session == 'london'"
    )

    result = generator.generate_filter_code_sync(session_proposal)
    assert result.success == True
    print("  [OK] Generated session filter code")

    print("\n  PASSED: CodeGenerator works correctly!")
    return True


def test_upgrade_manager():
    """Test UpgradeManager initialization."""
    print("\n" + "="*60)
    print("TEST 7: UpgradeManager")
    print("="*60)

    from src.upgrade.upgrade_manager import UpgradeManager, UpgradeConfig

    config = UpgradeConfig(
        enabled=True,
        analysis_interval_hours=24,
        min_trades_for_analysis=20,
        max_proposals_per_cycle=3,
        min_robustness_score=60.0
    )

    manager = UpgradeManager(config)

    # Test status
    status = manager.get_upgrade_status()
    assert status["enabled"] == True
    assert status["config"]["analysis_interval_hours"] == 24
    print(f"  [OK] UpgradeManager initialized")
    print(f"  [OK] Status: enabled={status['enabled']}")

    # Test should_run check
    should_run = manager.should_run_upgrade_cycle()
    print(f"  [OK] Should run upgrade cycle: {should_run}")

    # Get analysis summary
    summary = manager.get_analysis_summary()
    print(f"  [OK] Analysis summary: {summary['total_patterns']} patterns")

    print("\n  PASSED: UpgradeManager works correctly!")
    return True


def test_filter_chain_integration():
    """Test filter chain integration in scanner context."""
    print("\n" + "="*60)
    print("TEST 8: Filter Chain Integration")
    print("="*60)

    from src.upgrade.filter_registry import get_filter_registry
    from datetime import datetime, timezone

    registry = get_filter_registry()

    # Simulate signal data like auto_scanner provides
    signal_data = {
        "instrument": "EUR_USD",
        "direction": "LONG",
        "confidence": 75,
        "technical": {
            "trend": "BULLISH",
            "trend_strength": 60,
            "rsi": 55,
            "macd_trend": "BULLISH",
            "atr_pips": 8.5,
            "market_regime": "TRENDING",
            "regime_strength": 70,
            "adx": 28
        },
        "market_regime": "TRENDING",
        "regime_strength": 70,
        "sentiment": 0.3,
        "session": "london",
        "timestamp": datetime.now(timezone.utc)
    }

    # Run filter chain
    result = registry.run_all_filters(signal_data)

    print(f"  Signal: EUR_USD LONG (conf=75%)")
    print(f"  Filter chain result: passed={result.passed}")
    print(f"  Filters run: {result.filters_run}/{result.total_filters}")
    print(f"  Execution time: {result.execution_time_ms}ms")

    if not result.passed:
        print(f"  Blocked by: {result.blocking_filter}")
        print(f"  Reason: {result.reason}")

    print("\n  PASSED: Filter chain integration works!")
    return True


async def test_full_upgrade_cycle():
    """Test a full upgrade cycle (dry run)."""
    print("\n" + "="*60)
    print("TEST 9: Full Upgrade Cycle (Dry Run)")
    print("="*60)

    from src.upgrade.upgrade_manager import UpgradeManager, UpgradeConfig

    # Create manager with test config
    config = UpgradeConfig(
        enabled=True,
        analysis_interval_hours=24,
        min_trades_for_analysis=5,  # Lower threshold for testing
        max_proposals_per_cycle=1,
        min_robustness_score=60.0
    )

    manager = UpgradeManager(config)

    print("  Running upgrade cycle...")
    result = await manager.run_daily_upgrade_cycle()

    print(f"  Patterns found: {result.patterns_found}")
    print(f"  Proposals generated: {result.proposals_generated}")
    print(f"  Filters deployed: {result.filters_deployed}")
    print(f"  Filters rolled back: {result.filters_rolled_back}")

    if result.errors:
        print(f"  Errors: {result.errors[:3]}")

    if result.deployed_filters:
        print(f"  Deployed: {result.deployed_filters}")

    duration = (result.completed_at - result.started_at).total_seconds()
    print(f"  Duration: {duration:.2f}s")

    print("\n  PASSED: Full upgrade cycle completed!")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  SELF-UPGRADE SYSTEM - TEST SUITE")
    print("="*60)

    tests = [
        ("BaseFilter", test_base_filter),
        ("FilterRegistry", test_filter_registry),
        ("Builtin Filters", test_builtin_filters),
        ("PerformanceAnalyzer", test_performance_analyzer),
        ("CodeValidator", test_code_validator),
        ("CodeGenerator", test_code_generator),
        ("UpgradeManager", test_upgrade_manager),
        ("Filter Chain Integration", test_filter_chain_integration),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
                print(f"\n  FAILED: {name}")
        except Exception as e:
            failed += 1
            print(f"\n  FAILED: {name}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()

    # Run async test
    print("\n" + "="*60)
    print("  Running async tests...")
    print("="*60)

    try:
        asyncio.run(test_full_upgrade_cycle())
        passed += 1
    except Exception as e:
        failed += 1
        print(f"\n  FAILED: Full Upgrade Cycle")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    print(f"\n  Total: {passed + failed}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")

    if failed == 0:
        print("\n  ALL TESTS PASSED!")
    else:
        print(f"\n  {failed} TEST(S) FAILED!")

    print("="*60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
