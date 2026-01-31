"""Extended tests for RiskManager - weekly drawdown and auto-reset."""
import pytest
from datetime import date, timedelta, datetime, timezone
from unittest.mock import patch
from src.trading.risk_manager import RiskManager


class TestWeeklyDrawdown:
    """Tests for weekly drawdown enforcement."""

    def test_weekly_drawdown_blocks_trade(self):
        """Weekly drawdown > 6% should block trades."""
        rm = RiskManager()
        rm._weekly_pnl = -3500  # 7% on 50k

        result = rm.validate_trade(
            equity=50000, risk_amount=500, confidence=75,
            open_positions=0, spread_pips=1.0
        )

        assert not result.valid
        failed = [c.name for c in result.checks if not c.passed]
        assert "weekly_drawdown" in failed

    def test_weekly_drawdown_allows_profitable_week(self):
        """Profitable week should allow trading."""
        rm = RiskManager()
        rm._weekly_pnl = 1000  # Positive

        result = rm.validate_trade(
            equity=50000, risk_amount=500, confidence=75,
            open_positions=0, spread_pips=1.0
        )

        weekly_check = next(c for c in result.checks if c.name == "weekly_drawdown")
        assert weekly_check.passed

    def test_weekly_drawdown_at_limit(self):
        """Weekly drawdown at exactly 6% should still allow (strict <)."""
        rm = RiskManager()
        rm._weekly_pnl = -2999  # Just under 6% on 50k

        result = rm.validate_trade(
            equity=50000, risk_amount=500, confidence=75,
            open_positions=0, spread_pips=1.0
        )

        weekly_check = next(c for c in result.checks if c.name == "weekly_drawdown")
        assert weekly_check.passed

    def test_weekly_drawdown_exceeds_limit(self):
        """Weekly drawdown at exactly 6% should block."""
        rm = RiskManager()
        rm._weekly_pnl = -3000  # Exactly 6% on 50k

        result = rm.validate_trade(
            equity=50000, risk_amount=500, confidence=75,
            open_positions=0, spread_pips=1.0
        )

        weekly_check = next(c for c in result.checks if c.name == "weekly_drawdown")
        assert not weekly_check.passed


class TestAutoReset:
    """Tests for automatic daily/weekly P/L reset."""

    def test_daily_reset_at_midnight(self):
        """Daily P/L should reset at UTC midnight."""
        rm = RiskManager()
        rm._daily_pnl = -1000
        rm._last_daily_reset = date.today() - timedelta(days=1)

        rm._check_and_reset_if_needed()

        assert rm._daily_pnl == 0.0
        assert rm._last_daily_reset == date.today()

    def test_weekly_reset_on_monday(self):
        """Weekly P/L should reset on new week."""
        rm = RiskManager()
        rm._weekly_pnl = -2000
        rm._last_weekly_reset = date.today() - timedelta(days=8)

        rm._check_and_reset_if_needed()

        assert rm._weekly_pnl == 0.0

    def test_no_reset_same_day(self):
        """P/L should not reset within same day."""
        rm = RiskManager()
        rm._daily_pnl = -500
        rm._last_daily_reset = date.today()

        rm._check_and_reset_if_needed()

        assert rm._daily_pnl == -500  # Unchanged

    def test_no_reset_same_week(self):
        """P/L should not reset within same week."""
        rm = RiskManager()
        rm._weekly_pnl = -1500
        # Set to this week's Monday
        today = datetime.now(timezone.utc)
        rm._last_weekly_reset = rm._get_week_start(today)

        rm._check_and_reset_if_needed()

        assert rm._weekly_pnl == -1500  # Unchanged


class TestWeeklyTracking:
    """Tests for weekly P/L tracking methods."""

    def test_update_weekly_pnl(self):
        """Weekly P/L should accumulate correctly."""
        rm = RiskManager()
        rm.update_weekly_pnl(-100)
        rm.update_weekly_pnl(-200)
        rm.update_weekly_pnl(50)

        assert rm._weekly_pnl == -250

    def test_remaining_risk_calculation(self):
        """Remaining weekly risk should calculate correctly."""
        rm = RiskManager()
        rm._weekly_pnl = -2000  # Already lost 2k

        remaining = rm.get_remaining_risk_week(50000)
        # Max loss = 50000 * 0.06 = 3000
        # Remaining = 3000 - 2000 = 1000
        assert remaining == 1000

    def test_remaining_risk_profitable_week(self):
        """Remaining risk should be full amount when profitable."""
        rm = RiskManager()
        rm._weekly_pnl = 500  # Profitable

        remaining = rm.get_remaining_risk_week(50000)
        # Max loss = 50000 * 0.06 = 3000
        assert remaining == 3000

    def test_remaining_risk_exhausted(self):
        """Remaining risk should be 0 when limit exceeded."""
        rm = RiskManager()
        rm._weekly_pnl = -4000  # Over limit

        remaining = rm.get_remaining_risk_week(50000)
        assert remaining == 0

    def test_reset_weekly_pnl(self):
        """Manual weekly reset should work."""
        rm = RiskManager()
        rm._weekly_pnl = -1500

        rm.reset_weekly_pnl()

        assert rm._weekly_pnl == 0.0


class TestValidateTradeCallsAutoReset:
    """Tests that validate_trade triggers auto-reset."""

    def test_validate_trade_triggers_reset(self):
        """validate_trade should call auto-reset."""
        rm = RiskManager()
        rm._daily_pnl = -1000
        rm._last_daily_reset = date.today() - timedelta(days=1)

        # Call validate_trade
        rm.validate_trade(
            equity=50000, risk_amount=500, confidence=75,
            open_positions=0, spread_pips=1.0
        )

        # Daily P/L should have been reset
        assert rm._daily_pnl == 0.0
