"""
Test Risk Validation Gate in OrderManager.

Tests the fix that enforces risk validation before trade execution.
"""

import sys
from pathlib import Path

# Add Dev to path
DEV_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(DEV_DIR))

from unittest.mock import Mock, patch, MagicMock
import MetaTrader5 as mt5


def test_reject_without_validation_params():
    """Test: Trade rejected when confidence/risk_amount not provided."""
    print("\n" + "="*60)
    print("TEST 1: Reject trade without validation parameters")
    print("="*60)

    with patch('src.trading.orders.mt5') as mock_mt5:
        from src.trading.orders import OrderManager, OrderResult
        from src.trading.mt5_client import MT5Client

        # Mock MT5Client
        mock_client = Mock(spec=MT5Client)
        mock_client._convert_symbol.return_value = "EURUSD"
        mock_client.get_account.return_value = {"equity": 50000, "balance": 50000}

        om = OrderManager(client=mock_client)

        # Try to open position WITHOUT confidence/risk_amount
        result = om.open_position(
            instrument="EUR_USD",
            units=1000,
            stop_loss=1.0800,
            take_profit=1.0900
        )

        print(f"   Success: {result.success}")
        print(f"   Error: {result.error}")

        assert result.success == False, "Should reject trade"
        assert "Risk validation required" in result.error, "Should mention risk validation"

        print("   PASSED: Trade correctly rejected without validation params")
        return True


def test_reject_low_confidence():
    """Test: Trade rejected when confidence is too low."""
    print("\n" + "="*60)
    print("TEST 2: Reject trade with low confidence (<50%)")
    print("="*60)

    with patch('src.trading.orders.mt5') as mock_mt5:
        from src.trading.orders import OrderManager
        from src.trading.mt5_client import MT5Client

        # Mock MT5Client
        mock_client = Mock(spec=MT5Client)
        mock_client._convert_symbol.return_value = "EURUSD"
        mock_client.get_account.return_value = {"equity": 50000, "balance": 50000}

        # Mock MT5 functions
        mock_mt5.positions_total.return_value = 0
        mock_tick = Mock()
        mock_tick.ask = 1.0850
        mock_tick.bid = 1.0848
        mock_mt5.symbol_info_tick.return_value = mock_tick

        # Mock symbol_info for spread calculation
        mock_symbol = Mock()
        mock_symbol.digits = 5
        mock_mt5.symbol_info.return_value = mock_symbol

        om = OrderManager(client=mock_client)

        # Try with LOW confidence (30%)
        result = om.open_position(
            instrument="EUR_USD",
            units=1000,
            stop_loss=1.0800,
            take_profit=1.0900,
            confidence=30,  # Too low!
            risk_amount=100
        )

        print(f"   Success: {result.success}")
        print(f"   Error: {result.error}")

        assert result.success == False, "Should reject low confidence trade"
        assert "confidence" in result.error.lower(), "Should mention confidence"

        print("   PASSED: Low confidence trade correctly rejected")
        return True


def test_reject_too_many_positions():
    """Test: Trade rejected when max positions reached."""
    print("\n" + "="*60)
    print("TEST 3: Reject trade when max positions (3) reached")
    print("="*60)

    with patch('src.trading.orders.mt5') as mock_mt5:
        from src.trading.orders import OrderManager
        from src.trading.mt5_client import MT5Client

        # Mock MT5Client
        mock_client = Mock(spec=MT5Client)
        mock_client._convert_symbol.return_value = "EURUSD"
        mock_client.get_account.return_value = {"equity": 50000, "balance": 50000}

        # Mock: Already 3 positions open
        mock_mt5.positions_total.return_value = 3
        mock_tick = Mock()
        mock_tick.ask = 1.0850
        mock_tick.bid = 1.0848
        mock_mt5.symbol_info_tick.return_value = mock_tick

        # Mock symbol_info for spread calculation
        mock_symbol = Mock()
        mock_symbol.digits = 5
        mock_mt5.symbol_info.return_value = mock_symbol

        om = OrderManager(client=mock_client)

        # Try with good confidence but max positions reached
        result = om.open_position(
            instrument="EUR_USD",
            units=1000,
            stop_loss=1.0800,
            take_profit=1.0900,
            confidence=75,
            risk_amount=500
        )

        print(f"   Success: {result.success}")
        print(f"   Error: {result.error}")

        assert result.success == False, "Should reject when max positions"
        assert "concurrent_positions" in result.error.lower() or "position" in result.error.lower(), \
            "Should mention positions"

        print("   PASSED: Max positions trade correctly rejected")
        return True


def test_bypass_validation():
    """Test: _bypass_validation allows trade without checks."""
    print("\n" + "="*60)
    print("TEST 4: Bypass validation (emergency mode)")
    print("="*60)

    with patch('src.trading.orders.mt5') as mock_mt5:
        from src.trading.orders import OrderManager
        from src.trading.mt5_client import MT5Client

        # Mock MT5Client
        mock_client = Mock(spec=MT5Client)
        mock_client._convert_symbol.return_value = "EURUSD"

        # Mock symbol_info
        mock_symbol = Mock()
        mock_symbol.visible = True
        mock_symbol.volume_step = 0.01
        mock_symbol.volume_min = 0.01
        mock_symbol.volume_max = 100
        mock_symbol.filling_mode = 1  # FOK
        mock_mt5.symbol_info.return_value = mock_symbol

        # Mock tick
        mock_tick = Mock()
        mock_tick.ask = 1.0850
        mock_tick.bid = 1.0848
        mock_mt5.symbol_info_tick.return_value = mock_tick

        # Mock order_send - simulate success
        mock_result = Mock()
        mock_result.retcode = 10009  # TRADE_RETCODE_DONE
        mock_result.order = 12345
        mock_result.deal = 67890
        mock_result.volume = 0.01
        mock_result.price = 1.0850
        mock_result.comment = "OK"
        mock_mt5.order_send.return_value = mock_result
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TIME_GTC = 0

        om = OrderManager(client=mock_client)

        # Bypass validation - should proceed even without confidence/risk_amount
        result = om.open_position(
            instrument="EUR_USD",
            units=1000,
            stop_loss=1.0800,
            take_profit=1.0900,
            _bypass_validation=True  # Emergency bypass!
        )

        print(f"   Success: {result.success}")
        print(f"   Order ID: {result.order_id}")

        # Should have called order_send (bypassed validation)
        assert mock_mt5.order_send.called, "Should have attempted to execute"

        print("   PASSED: Bypass validation works for emergency")
        return True


def test_valid_trade_passes():
    """Test: Valid trade with good params passes validation and executes."""
    print("\n" + "="*60)
    print("TEST 5: Valid trade passes validation")
    print("="*60)

    with patch('src.trading.orders.mt5') as mock_mt5:
        from src.trading.orders import OrderManager
        from src.trading.mt5_client import MT5Client

        # Mock MT5Client
        mock_client = Mock(spec=MT5Client)
        mock_client._convert_symbol.return_value = "EURUSD"
        mock_client.get_account.return_value = {"equity": 50000, "balance": 50000}

        # Mock: No positions open, good spread
        mock_mt5.positions_total.return_value = 0
        mock_tick = Mock()
        mock_tick.ask = 1.0850
        mock_tick.bid = 1.0848  # 2 pip spread
        mock_mt5.symbol_info_tick.return_value = mock_tick

        # Mock symbol_info (with all needed attributes)
        mock_symbol = Mock()
        mock_symbol.visible = True
        mock_symbol.volume_step = 0.01
        mock_symbol.volume_min = 0.01
        mock_symbol.volume_max = 100
        mock_symbol.filling_mode = 1
        mock_symbol.digits = 5  # For spread calculation
        mock_mt5.symbol_info.return_value = mock_symbol

        # Mock order_send success
        mock_result = Mock()
        mock_result.retcode = 10009
        mock_result.order = 12345
        mock_result.deal = 67890
        mock_result.volume = 0.01
        mock_result.price = 1.0850
        mock_mt5.order_send.return_value = mock_result
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TIME_GTC = 0

        om = OrderManager(client=mock_client)

        # Valid trade: 75% confidence, 2% risk ($1000 on $50k)
        result = om.open_position(
            instrument="EUR_USD",
            units=1000,
            stop_loss=1.0800,
            take_profit=1.0900,
            confidence=75,
            risk_amount=1000  # 2% of 50k
        )

        print(f"   Success: {result.success}")
        print(f"   Order ID: {result.order_id}")
        print(f"   Price: {result.price}")

        assert result.success == True, f"Should pass validation and execute: {result.error}"
        assert mock_mt5.order_send.called, "Should have executed order"

        print("   PASSED: Valid trade executed successfully")
        return True


def run_all_tests():
    """Run all risk validation tests."""
    print("\n" + "="*60)
    print("RISK VALIDATION GATE - TEST SUITE")
    print("="*60)

    tests = [
        ("Reject without params", test_reject_without_validation_params),
        ("Reject low confidence", test_reject_low_confidence),
        ("Reject max positions", test_reject_too_many_positions),
        ("Bypass validation", test_bypass_validation),
        ("Valid trade passes", test_valid_trade_passes),
    ]

    results = []
    for name, test_func in tests:
        try:
            # Need to reimport for each test due to mocking
            import importlib
            import src.trading.orders
            importlib.reload(src.trading.orders)

            passed = test_func()
            results.append((name, passed, None))
        except Exception as e:
            print(f"   FAILED: {e}")
            results.append((name, False, str(e)))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, p, _ in results if p)
    total = len(results)

    for name, success, error in results:
        status = "PASS" if success else "FAIL"
        print(f"   [{status}] {name}")
        if error:
            print(f"          Error: {error}")

    print(f"\n   Results: {passed}/{total} tests passed")
    print("="*60)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
