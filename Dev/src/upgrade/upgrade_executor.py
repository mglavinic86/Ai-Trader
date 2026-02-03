"""
Upgrade Executor for AI Trader Self-Upgrade System.

Handles backtesting and deployment of new filters.
Includes rollback functionality for underperforming filters.

Usage:
    from src.upgrade.upgrade_executor import UpgradeExecutor

    executor = UpgradeExecutor()
    result = await executor.test_and_deploy(filter_code, filter_name)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import importlib.util
import sys
from pathlib import Path

from src.upgrade.base_filter import BaseFilter, FilterResult
from src.upgrade.code_validator import CodeValidator, ValidationResult
from src.upgrade.filter_registry import get_filter_registry
from src.utils.database import db
from src.utils.logger import logger


@dataclass
class BacktestResult:
    """Result of backtesting a filter."""
    total_signals: int = 0
    signals_blocked: int = 0
    would_have_won: int = 0
    would_have_lost: int = 0
    estimated_pnl_impact: float = 0.0
    robustness_score: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def block_rate(self) -> float:
        """Percentage of signals blocked."""
        if self.total_signals == 0:
            return 0.0
        return (self.signals_blocked / self.total_signals) * 100

    @property
    def accuracy(self) -> float:
        """Accuracy of blocking (blocked losers / total blocked)."""
        total_blocked = self.would_have_won + self.would_have_lost
        if total_blocked == 0:
            return 0.0
        return (self.would_have_lost / total_blocked) * 100


@dataclass
class DeploymentResult:
    """Result of deploying a filter."""
    success: bool
    filter_name: str = ""
    deployed_at: Optional[datetime] = None
    backtest_result: Optional[BacktestResult] = None
    error: str = ""


class UpgradeExecutor:
    """
    Executes filter deployment pipeline.

    Pipeline:
    1. Validate code (AST + security)
    2. Backtest on historical data
    3. Calculate robustness score
    4. Deploy if score >= threshold
    5. Monitor and rollback if needed
    """

    MIN_ROBUSTNESS_SCORE = 60.0  # Minimum score to deploy
    MIN_SIGNALS_FOR_BACKTEST = 20  # Minimum signals needed for valid backtest
    MAX_BLOCK_RATE = 50.0  # Maximum acceptable block rate

    def __init__(self):
        self.validator = CodeValidator()
        self._deployed_filters: Dict[str, datetime] = {}

    async def test_and_deploy(
        self,
        filter_code: str,
        filter_name: str,
        proposal_id: Optional[str] = None
    ) -> DeploymentResult:
        """
        Test a filter and deploy if it passes validation and backtesting.

        Args:
            filter_code: Python code for the filter
            filter_name: Unique name for the filter
            proposal_id: ID of the proposal (for audit logging)

        Returns:
            DeploymentResult with deployment status
        """
        # Step 1: Validate code
        validation = self.validator.validate_and_test(filter_code)
        if not validation.is_valid:
            self._log_audit("validate", proposal_id, False, "; ".join(validation.errors))
            return DeploymentResult(
                success=False,
                filter_name=filter_name,
                error=f"Validation failed: {'; '.join(validation.errors)}"
            )

        logger.info(f"Filter {filter_name} passed validation")

        # Step 2: Run backtest
        backtest = await self._run_backtest(filter_code, filter_name)
        if backtest.total_signals < self.MIN_SIGNALS_FOR_BACKTEST:
            self._log_audit("backtest", proposal_id, False, f"Insufficient signals: {backtest.total_signals}")
            return DeploymentResult(
                success=False,
                filter_name=filter_name,
                backtest_result=backtest,
                error=f"Insufficient signals for backtest ({backtest.total_signals} < {self.MIN_SIGNALS_FOR_BACKTEST})"
            )

        # Step 3: Check robustness score
        if backtest.robustness_score < self.MIN_ROBUSTNESS_SCORE:
            self._log_audit("backtest", proposal_id, False, f"Low robustness: {backtest.robustness_score:.1f}")
            return DeploymentResult(
                success=False,
                filter_name=filter_name,
                backtest_result=backtest,
                error=f"Robustness score too low ({backtest.robustness_score:.1f}% < {self.MIN_ROBUSTNESS_SCORE}%)"
            )

        # Step 4: Check block rate isn't too high
        if backtest.block_rate > self.MAX_BLOCK_RATE:
            self._log_audit("backtest", proposal_id, False, f"Block rate too high: {backtest.block_rate:.1f}%")
            return DeploymentResult(
                success=False,
                filter_name=filter_name,
                backtest_result=backtest,
                error=f"Block rate too high ({backtest.block_rate:.1f}% > {self.MAX_BLOCK_RATE}%)"
            )

        logger.info(f"Filter {filter_name} passed backtest (robustness: {backtest.robustness_score:.1f}%)")

        # Step 5: Deploy
        registry = get_filter_registry()
        if registry.deploy_filter(filter_code, filter_name):
            self._deployed_filters[filter_name] = datetime.now()
            self._log_audit("deploy", proposal_id, True)
            self._log_deployed_filter(filter_name, backtest)

            return DeploymentResult(
                success=True,
                filter_name=filter_name,
                deployed_at=datetime.now(),
                backtest_result=backtest
            )
        else:
            self._log_audit("deploy", proposal_id, False, "Registry deployment failed")
            return DeploymentResult(
                success=False,
                filter_name=filter_name,
                backtest_result=backtest,
                error="Failed to deploy filter to registry"
            )

    async def _run_backtest(
        self,
        filter_code: str,
        filter_name: str,
        days: int = 30
    ) -> BacktestResult:
        """
        Run backtest on historical signals.

        Simulates running the filter on past signals and calculates
        how many winning/losing trades would have been blocked.
        """
        result = BacktestResult()

        try:
            # Load the filter class
            filter_instance = self._instantiate_filter(filter_code)
            if filter_instance is None:
                result.robustness_score = 0
                return result

            # Get historical signals with outcomes
            signals = self._get_historical_signals(days)
            result.total_signals = len(signals)

            if result.total_signals == 0:
                result.robustness_score = 0
                return result

            # Run filter on each signal
            for signal in signals:
                signal_data = self._signal_to_dict(signal)
                filter_result = filter_instance.check(signal_data)

                if not filter_result.passed:
                    result.signals_blocked += 1

                    # Check actual outcome
                    pnl = signal.get("pnl", 0) or 0
                    if pnl < 0:
                        result.would_have_lost += 1
                        result.estimated_pnl_impact += abs(pnl)  # Saved loss
                    else:
                        result.would_have_won += 1
                        result.estimated_pnl_impact -= pnl  # Missed gain

            # Calculate robustness score
            result.robustness_score = self._calculate_robustness(result)

            result.details = {
                "days_tested": days,
                "filter_name": filter_name,
                "block_rate": f"{result.block_rate:.1f}%",
                "accuracy": f"{result.accuracy:.1f}%",
            }

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            result.robustness_score = 0

        return result

    def _instantiate_filter(self, filter_code: str) -> Optional[BaseFilter]:
        """Instantiate a filter from code string."""
        try:
            # Use a more permissive namespace that allows actual imports
            # This is safe because we've already validated the code
            import datetime
            from dataclasses import dataclass, field
            from typing import Dict, List, Optional, Any

            namespace = {
                "__builtins__": __builtins__,
                "datetime": datetime.datetime,
                "timedelta": datetime.timedelta,
                "timezone": datetime.timezone,
                "dataclass": dataclass,
                "field": field,
                "Dict": Dict,
                "List": List,
                "Optional": Optional,
                "Any": Any,
                "BaseFilter": BaseFilter,
                "FilterResult": FilterResult,
            }

            # Execute the code
            exec(compile(filter_code, "<filter>", "exec"), namespace)

            # Find the filter class
            for name, obj in namespace.items():
                if (
                    isinstance(obj, type) and
                    issubclass(obj, BaseFilter) and
                    obj is not BaseFilter
                ):
                    return obj()

            return None

        except Exception as e:
            logger.error(f"Failed to instantiate filter: {e}")
            return None

    def _get_historical_signals(self, days: int = 30) -> List[Dict]:
        """Get historical signals with outcomes from database."""
        cutoff = datetime.now() - timedelta(days=days)

        try:
            with db._connection() as conn:
                cursor = conn.cursor()

                # Get signals that were executed with their outcomes
                cursor.execute("""
                    SELECT
                        s.instrument,
                        s.direction,
                        s.confidence,
                        s.entry_price,
                        s.stop_loss,
                        s.take_profit,
                        s.risk_reward,
                        s.timestamp,
                        t.pnl,
                        t.close_reason,
                        r.regime as market_regime,
                        r.regime_strength
                    FROM auto_signals s
                    LEFT JOIN trades t ON s.trade_id = t.trade_id
                    LEFT JOIN market_regimes r ON t.trade_id = r.trade_id
                    WHERE s.timestamp >= ?
                    AND s.executed = 1
                    ORDER BY s.timestamp
                """, (cutoff.isoformat(),))

                signals = []
                for row in cursor.fetchall():
                    signals.append(dict(row))

                return signals

        except Exception as e:
            logger.error(f"Failed to get historical signals: {e}")
            return []

    def _signal_to_dict(self, signal: Dict) -> Dict:
        """Convert database signal to format expected by filters."""
        # Parse timestamp
        timestamp = signal.get("timestamp")
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                timestamp = datetime.now()

        # Determine session
        hour = timestamp.hour if timestamp else 12
        if 7 <= hour < 16:
            session = "london"
        elif 12 <= hour < 21:
            session = "newyork"
        elif 0 <= hour < 9:
            session = "tokyo"
        else:
            session = "sydney"

        return {
            "instrument": signal.get("instrument", ""),
            "direction": signal.get("direction", ""),
            "confidence": signal.get("confidence", 0),
            "entry_price": signal.get("entry_price", 0),
            "stop_loss": signal.get("stop_loss", 0),
            "take_profit": signal.get("take_profit", 0),
            "risk_reward": signal.get("risk_reward", 0),
            "timestamp": timestamp,
            "session": session,
            "market_regime": signal.get("market_regime", ""),
            "regime_strength": signal.get("regime_strength", 0),
            "technical": {
                "market_regime": signal.get("market_regime", ""),
                "regime_strength": signal.get("regime_strength", 0),
            },
            "sentiment": 0.0,  # Not available in historical data
        }

    def _calculate_robustness(self, result: BacktestResult) -> float:
        """
        Calculate robustness score for a filter.

        Score is based on:
        - Accuracy (blocking losers vs blocking winners): 50%
        - Block rate (not blocking too many): 30%
        - PnL impact (net positive): 20%
        """
        score = 0.0

        # Accuracy component (50%)
        if result.signals_blocked > 0:
            accuracy_score = min(result.accuracy, 100) * 0.5
            score += accuracy_score

        # Block rate component (30%)
        # Ideal block rate is 10-30%. Penalize if too low or too high.
        block_rate = result.block_rate
        if 10 <= block_rate <= 30:
            block_score = 30.0
        elif block_rate < 10:
            block_score = block_rate * 3  # Scale up low block rates
        else:
            # Penalize high block rates
            block_score = max(0, 30 - (block_rate - 30) * 0.5)
        score += block_score

        # PnL impact component (20%)
        if result.estimated_pnl_impact > 0:
            pnl_score = min(result.estimated_pnl_impact / 100, 1.0) * 20
            score += pnl_score
        else:
            # Negative PnL impact = losing filter
            score += max(-20, result.estimated_pnl_impact / 100 * 20)

        return max(0, min(100, score))

    def check_filter_performance(
        self,
        filter_name: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Check the live performance of a deployed filter.

        Used to decide if a filter should be rolled back.
        """
        registry = get_filter_registry()
        filter_instance = registry.get(filter_name)

        if filter_instance is None:
            return {"error": "Filter not found"}

        stats = filter_instance.get_stats()

        # Check for rollback conditions
        should_rollback = False
        rollback_reason = ""

        # Condition 1: Block rate too high (> 50%)
        if float(stats["block_rate"].rstrip("%")) > 50:
            should_rollback = True
            rollback_reason = f"Block rate too high: {stats['block_rate']}"

        # Condition 2: Low accuracy (< 40%)
        accuracy = float(stats["accuracy"].rstrip("%"))
        if stats["signals_blocked"] >= 5 and accuracy < 40:
            should_rollback = True
            rollback_reason = f"Low accuracy: {stats['accuracy']}"

        # Condition 3: Negative PnL impact
        if stats["estimated_pnl_saved"] < -50:
            should_rollback = True
            rollback_reason = f"Negative PnL impact: {stats['estimated_pnl_saved']}"

        return {
            "filter_name": filter_name,
            "stats": stats,
            "should_rollback": should_rollback,
            "rollback_reason": rollback_reason,
        }

    def rollback_filter(self, filter_name: str, reason: str = "") -> bool:
        """
        Rollback a deployed filter.

        Args:
            filter_name: Name of the filter to rollback
            reason: Reason for rollback

        Returns:
            True if rollback succeeded
        """
        registry = get_filter_registry()

        if registry.rollback_filter(filter_name):
            self._log_audit("rollback", None, True, reason)
            self._update_deployed_filter_status(filter_name, rolled_back=True)
            logger.info(f"Rolled back filter: {filter_name} (reason: {reason})")
            return True

        return False

    def _log_audit(
        self,
        action: str,
        proposal_id: Optional[str],
        success: bool,
        error_message: str = ""
    ) -> None:
        """Log to upgrade_audit_log table."""
        try:
            with db._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO upgrade_audit_log (
                        timestamp, action, proposal_id, success, error_message
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    action,
                    proposal_id,
                    1 if success else 0,
                    error_message
                ))
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")

    def _log_deployed_filter(self, filter_name: str, backtest: BacktestResult) -> None:
        """Log deployed filter to database."""
        try:
            with db._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO deployed_filters (
                        filter_name, filter_type, enabled,
                        signals_blocked, estimated_pnl_impact
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    filter_name,
                    "ai_generated",
                    1,
                    backtest.signals_blocked,
                    backtest.estimated_pnl_impact
                ))
        except Exception as e:
            logger.error(f"Failed to log deployed filter: {e}")

    def _update_deployed_filter_status(
        self,
        filter_name: str,
        enabled: bool = None,
        rolled_back: bool = None
    ) -> None:
        """Update deployed filter status in database."""
        try:
            with db._connection() as conn:
                cursor = conn.cursor()

                updates = []
                values = []

                if enabled is not None:
                    updates.append("enabled = ?")
                    values.append(1 if enabled else 0)

                if rolled_back is not None:
                    updates.append("rolled_back = ?")
                    values.append(1 if rolled_back else 0)

                if updates:
                    values.append(filter_name)
                    cursor.execute(
                        f"UPDATE deployed_filters SET {', '.join(updates)} WHERE filter_name = ?",
                        values
                    )
        except Exception as e:
            logger.error(f"Failed to update deployed filter: {e}")
