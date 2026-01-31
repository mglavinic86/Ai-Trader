"""
Risk Manager - Enforces hard-coded risk limits.

CRITICAL: These limits CANNOT be overridden!
- Max risk per trade: 1-3% (confidence-based)
- Max daily drawdown: 3%
- Max weekly drawdown: 6%
- Max concurrent positions: 3

Usage:
    from src.trading.risk_manager import RiskManager

    rm = RiskManager()
    result = rm.validate_trade(equity=10000, risk_amount=200, ...)
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta, timezone, date

from src.utils.config import config
from src.utils.logger import logger


@dataclass
class CheckResult:
    """Result of a single risk check."""
    name: str
    passed: bool
    message: str
    value: Optional[float] = None
    limit: Optional[float] = None


@dataclass
class ValidationResult:
    """Result of trade validation."""
    valid: bool
    checks: list[CheckResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "value": c.value,
                    "limit": c.limit
                }
                for c in self.checks
            ]
        }

    def get_failed_checks(self) -> list[CheckResult]:
        """Get list of failed checks."""
        return [c for c in self.checks if not c.passed]

    def format_checklist(self) -> str:
        """Format as readable checklist."""
        lines = ["Pre-trade Checklist:", "─" * 40]
        for check in self.checks:
            status = "✓" if check.passed else "✗"
            lines.append(f"[{status}] {check.message}")
        return "\n".join(lines)


class RiskManager:
    """
    Risk Manager for enforcing trading limits.

    All limits are hard-coded and cannot be changed at runtime.
    """

    # HARD-CODED LIMITS (DO NOT CHANGE!)
    MAX_RISK_PER_TRADE = 0.03  # 3% absolute max
    MAX_DAILY_DRAWDOWN = 0.03  # 3%
    MAX_WEEKLY_DRAWDOWN = 0.06  # 6%
    MAX_CONCURRENT_POSITIONS = 3
    MAX_SPREAD_PIPS = 3.0
    MIN_CONFIDENCE = 50

    def __init__(self):
        """Initialize risk manager."""
        self._daily_pnl = 0.0
        self._weekly_pnl = 0.0
        self._last_daily_reset = datetime.now(timezone.utc).date()
        self._last_weekly_reset = self._get_week_start(datetime.now(timezone.utc))
        logger.info("RiskManager initialized with hard-coded limits")

    def _get_week_start(self, dt: datetime) -> date:
        """Get Monday of the week containing dt."""
        return (dt - timedelta(days=dt.weekday())).date()

    def _check_and_reset_if_needed(self) -> None:
        """Auto-reset daily/weekly P/L at UTC boundaries."""
        now = datetime.now(timezone.utc)
        today = now.date()
        current_week_start = self._get_week_start(now)

        # Daily reset at UTC midnight
        if today > self._last_daily_reset:
            logger.info(f"Auto-resetting daily P/L (new day: {today})")
            self._daily_pnl = 0.0
            self._last_daily_reset = today

        # Weekly reset on Monday UTC
        if current_week_start > self._last_weekly_reset:
            logger.info(f"Auto-resetting weekly P/L (new week)")
            self._weekly_pnl = 0.0
            self._last_weekly_reset = current_week_start

    def validate_trade(
        self,
        equity: float,
        risk_amount: float,
        confidence: int,
        open_positions: int,
        spread_pips: float,
        daily_pnl: Optional[float] = None
    ) -> ValidationResult:
        """
        Validate a trade against all risk limits.

        Args:
            equity: Current account equity
            risk_amount: Amount at risk for this trade
            confidence: Confidence score (0-100)
            open_positions: Number of currently open positions
            spread_pips: Current spread in pips
            daily_pnl: Today's P/L (optional, uses internal tracking if None)

        Returns:
            ValidationResult with all check results
        """
        # Auto-reset at start of day/week
        self._check_and_reset_if_needed()

        checks = []

        # Use provided daily_pnl or internal tracking
        if daily_pnl is None:
            daily_pnl = self._daily_pnl

        # 1. Check confidence minimum
        confidence_check = self._check_confidence(confidence)
        checks.append(confidence_check)

        # 2. Check risk per trade
        risk_check = self._check_risk_per_trade(equity, risk_amount, confidence)
        checks.append(risk_check)

        # 3. Check daily drawdown
        daily_check = self._check_daily_drawdown(equity, daily_pnl)
        checks.append(daily_check)

        # 4. Check weekly drawdown
        weekly_check = self._check_weekly_drawdown(equity, self._weekly_pnl)
        checks.append(weekly_check)

        # 5. Check concurrent positions
        position_check = self._check_positions(open_positions)
        checks.append(position_check)

        # 6. Check spread
        spread_check = self._check_spread(spread_pips)
        checks.append(spread_check)

        # All checks must pass
        all_passed = all(c.passed for c in checks)

        result = ValidationResult(valid=all_passed, checks=checks)

        if not all_passed:
            failed = result.get_failed_checks()
            logger.warning(f"Trade validation FAILED: {[c.name for c in failed]}")
        else:
            logger.info("Trade validation PASSED all checks")

        return result

    def _check_confidence(self, confidence: int) -> CheckResult:
        """Check if confidence meets minimum threshold."""
        passed = confidence >= self.MIN_CONFIDENCE
        return CheckResult(
            name="confidence",
            passed=passed,
            message=f"Confidence {confidence}% {'≥' if passed else '<'} {self.MIN_CONFIDENCE}%",
            value=confidence,
            limit=self.MIN_CONFIDENCE
        )

    def _check_risk_per_trade(
        self,
        equity: float,
        risk_amount: float,
        confidence: int
    ) -> CheckResult:
        """Check if risk is within allowed tier."""
        # Get allowed risk for this confidence level
        allowed_percent = config.get_risk_percent(confidence)
        allowed_amount = equity * allowed_percent

        # Also check absolute max
        absolute_max = equity * self.MAX_RISK_PER_TRADE

        passed = risk_amount <= allowed_amount and risk_amount <= absolute_max
        actual_percent = (risk_amount / equity * 100) if equity > 0 else 0

        return CheckResult(
            name="risk_per_trade",
            passed=passed,
            message=f"Risk {actual_percent:.1f}% {'≤' if passed else '>'} {allowed_percent*100:.1f}% (tier limit)",
            value=actual_percent,
            limit=allowed_percent * 100
        )

    def _check_daily_drawdown(self, equity: float, daily_pnl: float) -> CheckResult:
        """Check if daily drawdown is within limit."""
        if daily_pnl >= 0:
            # Profitable day, no drawdown
            return CheckResult(
                name="daily_drawdown",
                passed=True,
                message=f"Daily P/L: +${daily_pnl:.2f} (no drawdown)",
                value=0,
                limit=self.MAX_DAILY_DRAWDOWN * 100
            )

        # Calculate drawdown percentage
        drawdown_percent = abs(daily_pnl) / equity if equity > 0 else 0
        limit = self.MAX_DAILY_DRAWDOWN
        passed = drawdown_percent < limit

        return CheckResult(
            name="daily_drawdown",
            passed=passed,
            message=f"Daily drawdown {drawdown_percent*100:.1f}% {'<' if passed else '≥'} {limit*100:.1f}%",
            value=drawdown_percent * 100,
            limit=limit * 100
        )

    def _check_weekly_drawdown(self, equity: float, weekly_pnl: float) -> CheckResult:
        """Check if weekly drawdown is within limit."""
        if weekly_pnl >= 0:
            return CheckResult(
                name="weekly_drawdown",
                passed=True,
                message=f"Weekly P/L: +${weekly_pnl:.2f}",
                value=0,
                limit=self.MAX_WEEKLY_DRAWDOWN * 100
            )

        drawdown_percent = abs(weekly_pnl) / equity if equity > 0 else 0
        limit = self.MAX_WEEKLY_DRAWDOWN
        passed = drawdown_percent < limit

        return CheckResult(
            name="weekly_drawdown",
            passed=passed,
            message=f"Weekly drawdown {drawdown_percent*100:.1f}% {'<' if passed else '≥'} {limit*100:.1f}%",
            value=drawdown_percent * 100,
            limit=limit * 100
        )

    def _check_positions(self, open_positions: int) -> CheckResult:
        """Check if position count is within limit."""
        passed = open_positions < self.MAX_CONCURRENT_POSITIONS
        return CheckResult(
            name="concurrent_positions",
            passed=passed,
            message=f"Open positions {open_positions} {'<' if passed else '≥'} {self.MAX_CONCURRENT_POSITIONS}",
            value=open_positions,
            limit=self.MAX_CONCURRENT_POSITIONS
        )

    def _check_spread(self, spread_pips: float) -> CheckResult:
        """Check if spread is acceptable."""
        passed = spread_pips <= self.MAX_SPREAD_PIPS
        return CheckResult(
            name="spread",
            passed=passed,
            message=f"Spread {spread_pips:.1f} pips {'≤' if passed else '>'} {self.MAX_SPREAD_PIPS}",
            value=spread_pips,
            limit=self.MAX_SPREAD_PIPS
        )

    def update_daily_pnl(self, pnl: float) -> None:
        """Update daily P/L tracking."""
        self._daily_pnl += pnl
        logger.debug(f"Daily P/L updated: {self._daily_pnl:.2f}")

    def reset_daily_pnl(self) -> None:
        """Reset daily P/L (call at start of trading day)."""
        self._daily_pnl = 0.0
        self._last_daily_reset = datetime.now(timezone.utc).date()
        logger.info("Daily P/L reset to 0")

    def update_weekly_pnl(self, pnl: float) -> None:
        """Update weekly P/L tracking."""
        self._weekly_pnl += pnl
        logger.debug(f"Weekly P/L updated: {self._weekly_pnl:.2f}")

    def reset_weekly_pnl(self) -> None:
        """Reset weekly P/L (call at start of week)."""
        self._weekly_pnl = 0.0
        self._last_weekly_reset = self._get_week_start(datetime.now(timezone.utc))
        logger.info("Weekly P/L reset to 0")

    def get_remaining_risk_week(self, equity: float) -> float:
        """Calculate remaining risk budget for this week."""
        max_loss = equity * self.MAX_WEEKLY_DRAWDOWN
        if self._weekly_pnl >= 0:
            return max_loss
        current_loss = abs(self._weekly_pnl)
        return max(0, max_loss - current_loss)

    def can_trade_today(self, equity: float) -> tuple[bool, str]:
        """
        Quick check if trading is allowed today.

        Returns:
            (can_trade, reason)
        """
        if self._daily_pnl >= 0:
            return True, "Profitable day, trading allowed"

        drawdown = abs(self._daily_pnl) / equity if equity > 0 else 0
        if drawdown >= self.MAX_DAILY_DRAWDOWN:
            return False, f"Daily drawdown limit reached ({drawdown*100:.1f}%)"

        return True, f"Current drawdown {drawdown*100:.1f}% within limit"

    def get_remaining_risk_today(self, equity: float) -> float:
        """
        Calculate remaining risk budget for today.

        Returns:
            Remaining risk amount in account currency
        """
        max_loss = equity * self.MAX_DAILY_DRAWDOWN
        if self._daily_pnl >= 0:
            return max_loss

        current_loss = abs(self._daily_pnl)
        remaining = max_loss - current_loss
        return max(0, remaining)


# Pre-trade checklist as a function
def pre_trade_checklist(
    equity: float,
    confidence: int,
    risk_amount: float,
    open_positions: int,
    spread_pips: float,
    daily_pnl: float = 0.0,
    adversarial_done: bool = False,
    rag_checked: bool = False,
    sentiment_calculated: bool = False
) -> ValidationResult:
    """
    Complete pre-trade checklist including AI requirements.

    Args:
        equity: Account equity
        confidence: Confidence score
        risk_amount: Risk amount
        open_positions: Open position count
        spread_pips: Current spread
        daily_pnl: Today's P/L
        adversarial_done: Was Bull vs Bear analysis done?
        rag_checked: Was RAG error memory checked?
        sentiment_calculated: Was sentiment calculated?

    Returns:
        ValidationResult with all checks
    """
    rm = RiskManager()

    # Get standard risk checks
    result = rm.validate_trade(
        equity=equity,
        risk_amount=risk_amount,
        confidence=confidence,
        open_positions=open_positions,
        spread_pips=spread_pips,
        daily_pnl=daily_pnl
    )

    # Add AI-specific checks
    result.checks.append(CheckResult(
        name="adversarial",
        passed=adversarial_done,
        message=f"Adversarial analysis {'completed' if adversarial_done else 'NOT done'}"
    ))

    result.checks.append(CheckResult(
        name="rag_check",
        passed=rag_checked,
        message=f"RAG error check {'completed' if rag_checked else 'NOT done'}"
    ))

    result.checks.append(CheckResult(
        name="sentiment",
        passed=sentiment_calculated,
        message=f"Sentiment {'calculated' if sentiment_calculated else 'NOT calculated'}"
    ))

    # Update overall validity
    result.valid = all(c.passed for c in result.checks)

    return result
