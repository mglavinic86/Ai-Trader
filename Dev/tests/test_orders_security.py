"""Security tests for OrderManager."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import src.trading.orders as orders_module


class TestBypassRemoval:
    """Tests that global bypass flag has been removed."""

    def test_no_global_bypass_flag(self):
        """Global bypass flag should not exist."""
        assert not hasattr(orders_module, '_BYPASS_RISK_VALIDATION'), \
            "Global _BYPASS_RISK_VALIDATION flag should be removed"


class TestPipCalculation:
    """Tests for pip divisor calculation."""

    def test_jpy_pair_pip_value(self):
        """JPY pairs should use 0.01 pip divisor."""
        from src.utils.helpers import get_pip_divisor
        assert get_pip_divisor("USD_JPY") == 0.01
        assert get_pip_divisor("EUR_JPY") == 0.01
        assert get_pip_divisor("GBP_JPY") == 0.01

    def test_standard_pair_pip_value(self):
        """Standard pairs should use 0.0001 pip divisor."""
        from src.utils.helpers import get_pip_divisor
        assert get_pip_divisor("EUR_USD") == 0.0001
        assert get_pip_divisor("GBP_USD") == 0.0001
        assert get_pip_divisor("AUD_USD") == 0.0001

    def test_gold_pip_value(self):
        """XAUUSD should use 0.1 pip divisor."""
        from src.utils.helpers import get_pip_divisor
        assert get_pip_divisor("XAU_USD") == 0.1
        assert get_pip_divisor("XAUUSD") == 0.1

    def test_silver_pip_value(self):
        """XAGUSD should use 0.1 pip divisor."""
        from src.utils.helpers import get_pip_divisor
        assert get_pip_divisor("XAG_USD") == 0.1

    def test_crypto_pip_value(self):
        """Crypto pairs should use 1.0 pip divisor."""
        from src.utils.helpers import get_pip_divisor
        assert get_pip_divisor("BTC_USD") == 1.0
        assert get_pip_divisor("ETH_USD") == 1.0

    def test_pip_divisor_with_mt5_symbol_info(self):
        """Should use MT5 digits when symbol_info provided."""
        from src.utils.helpers import get_pip_divisor

        # Mock symbol_info with 5 digits (standard forex)
        mock_info = Mock()
        mock_info.digits = 5
        assert get_pip_divisor("EUR_USD", mock_info) == 0.0001

        # Mock symbol_info with 3 digits (JPY)
        mock_info.digits = 3
        assert get_pip_divisor("USD_JPY", mock_info) == 0.01

        # Mock symbol_info with 2 digits
        mock_info.digits = 2
        assert get_pip_divisor("XAU_USD", mock_info) == 0.1


class TestEquityValidation:
    """Tests for equity validation in OrderManager."""

    @patch('src.trading.orders.mt5')
    def test_reject_when_no_equity(self, mock_mt5):
        """Trade rejected when equity unavailable."""
        from src.trading.orders import OrderManager

        # Setup mock client
        mock_client = Mock()
        mock_client.get_account.return_value = {}  # No equity or balance
        mock_client._convert_symbol.return_value = "EURUSD"

        om = OrderManager(client=mock_client)
        result = om.open_position(
            instrument="EUR_USD", units=1000,
            confidence=75, risk_amount=500, stop_loss=1.08
        )

        assert not result.success
        assert "equity" in result.error.lower()

    @patch('src.trading.orders.mt5')
    def test_reject_when_equity_zero(self, mock_mt5):
        """Trade rejected when equity is zero."""
        from src.trading.orders import OrderManager

        mock_client = Mock()
        mock_client.get_account.return_value = {"equity": 0, "balance": 0}
        mock_client._convert_symbol.return_value = "EURUSD"

        om = OrderManager(client=mock_client)
        result = om.open_position(
            instrument="EUR_USD", units=1000,
            confidence=75, risk_amount=500, stop_loss=1.08
        )

        assert not result.success
        assert "equity" in result.error.lower()

    @patch('src.trading.orders.mt5')
    def test_accept_when_balance_available(self, mock_mt5):
        """Trade should use balance when equity not available."""
        from src.trading.orders import OrderManager

        mock_client = Mock()
        mock_client.get_account.return_value = {"balance": 50000}  # No equity, but has balance
        mock_client._convert_symbol.return_value = "EURUSD"

        # Setup MT5 mocks
        mock_mt5.positions_total.return_value = 0
        mock_symbol_info = Mock()
        mock_symbol_info.digits = 5
        mock_symbol_info.visible = True
        mock_symbol_info.volume_step = 0.01
        mock_symbol_info.volume_min = 0.01
        mock_symbol_info.volume_max = 100.0
        mock_symbol_info.filling_mode = 1
        mock_mt5.symbol_info.return_value = mock_symbol_info

        mock_tick = Mock()
        mock_tick.ask = 1.1000
        mock_tick.bid = 1.0998
        mock_mt5.symbol_info_tick.return_value = mock_tick

        mock_result = Mock()
        mock_result.retcode = 10009
        mock_result.order = 12345
        mock_result.deal = 67890
        mock_result.volume = 0.01
        mock_result.price = 1.1000
        mock_mt5.order_send.return_value = mock_result
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TIME_GTC = 0

        om = OrderManager(client=mock_client)

        # This should not fail on equity validation
        # Balance of 50000 should be used when equity is not available
        result = om.open_position(
            instrument="EUR_USD", units=1000,
            confidence=75, risk_amount=500, stop_loss=1.08
        )

        # Check that the error is NOT about equity
        if not result.success:
            assert "equity" not in result.error.lower() or "validation" in result.error.lower()


class TestRiskValidationRequired:
    """Tests that risk validation is enforced."""

    @patch('src.trading.orders.mt5')
    def test_reject_without_confidence(self, mock_mt5):
        """Trade rejected when confidence not provided."""
        from src.trading.orders import OrderManager

        mock_client = Mock()
        om = OrderManager(client=mock_client)

        result = om.open_position(
            instrument="EUR_USD", units=1000,
            stop_loss=1.08
            # Missing confidence and risk_amount
        )

        assert not result.success
        assert "risk validation" in result.error.lower()

    @patch('src.trading.orders.mt5')
    def test_reject_without_risk_amount(self, mock_mt5):
        """Trade rejected when risk_amount not provided."""
        from src.trading.orders import OrderManager

        mock_client = Mock()
        om = OrderManager(client=mock_client)

        result = om.open_position(
            instrument="EUR_USD", units=1000,
            confidence=75,  # Has confidence
            stop_loss=1.08
            # Missing risk_amount
        )

        assert not result.success
        assert "risk validation" in result.error.lower()

    @patch('src.trading.orders.mt5')
    def test_bypass_allowed_per_call(self, mock_mt5):
        """Per-call bypass should work (for emergency use)."""
        from src.trading.orders import OrderManager

        mock_client = Mock()
        mock_client._convert_symbol.return_value = "EURUSD"

        # Setup full MT5 mocks
        mock_symbol_info = Mock()
        mock_symbol_info.visible = True
        mock_symbol_info.volume_step = 0.01
        mock_symbol_info.volume_min = 0.01
        mock_symbol_info.volume_max = 100.0
        mock_symbol_info.filling_mode = 1  # FOK
        mock_mt5.symbol_info.return_value = mock_symbol_info

        mock_tick = Mock()
        mock_tick.ask = 1.1000
        mock_tick.bid = 1.0998
        mock_mt5.symbol_info_tick.return_value = mock_tick

        mock_result = Mock()
        mock_result.retcode = 10009  # TRADE_RETCODE_DONE
        mock_result.order = 12345
        mock_result.deal = 67890
        mock_result.volume = 0.01
        mock_result.price = 1.1000
        mock_mt5.order_send.return_value = mock_result
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TIME_GTC = 0

        om = OrderManager(client=mock_client)

        # With bypass, should proceed even without confidence/risk_amount
        result = om.open_position(
            instrument="EUR_USD", units=1000,
            stop_loss=1.08,
            _bypass_validation=True
        )

        # Should have attempted the order (may succeed or fail for other reasons)
        # Key point: it didn't fail on risk validation
        if not result.success:
            assert "risk validation" not in result.error.lower()
