"""
Upgrade Manager for AI Trader Self-Upgrade System.

Main orchestrator that coordinates the entire self-upgrade pipeline:
1. Performance analysis
2. Filter proposal generation
3. Code generation
4. Validation and testing
5. Deployment
6. Monitoring and rollback

Usage:
    from src.upgrade import UpgradeManager

    manager = UpgradeManager()
    await manager.run_daily_upgrade_cycle()
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from src.upgrade.performance_analyzer import PerformanceAnalyzer, FilterProposal
from src.upgrade.code_generator import CodeGenerator
from src.upgrade.code_validator import CodeValidator
from src.upgrade.upgrade_executor import UpgradeExecutor, DeploymentResult
from src.upgrade.filter_registry import get_filter_registry
from src.utils.database import db
from src.utils.logger import logger


@dataclass
class UpgradeCycleResult:
    """Result of a complete upgrade cycle."""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    patterns_found: int = 0
    proposals_generated: int = 0
    filters_deployed: int = 0
    filters_rolled_back: int = 0
    errors: List[str] = field(default_factory=list)
    deployed_filters: List[str] = field(default_factory=list)
    rolled_back_filters: List[str] = field(default_factory=list)


@dataclass
class UpgradeConfig:
    """Configuration for the upgrade system."""
    enabled: bool = True
    analysis_interval_hours: int = 24
    min_trades_for_analysis: int = 20
    max_proposals_per_cycle: int = 3
    min_robustness_score: float = 60.0
    auto_rollback_threshold: Dict[str, Any] = field(default_factory=lambda: {
        "win_rate_drop": 0.10,  # 10% drop triggers rollback
        "consecutive_losses": 5,
        "max_block_rate": 50.0
    })


class UpgradeManager:
    """
    Orchestrates the AI Trader self-upgrade system.

    The manager coordinates:
    - Daily performance analysis to identify losing patterns
    - AI-powered filter generation based on patterns
    - Safe code validation before deployment
    - Backtesting to ensure filter effectiveness
    - Monitoring deployed filters for performance
    - Automatic rollback of underperforming filters
    """

    def __init__(self, config: Optional[UpgradeConfig] = None):
        self.config = config or UpgradeConfig()
        self.analyzer = PerformanceAnalyzer()
        self.generator = CodeGenerator()
        self.validator = CodeValidator()
        self.executor = UpgradeExecutor()

        self._last_upgrade_cycle: Optional[datetime] = None
        self._cycle_results: List[UpgradeCycleResult] = []

    async def run_daily_upgrade_cycle(self) -> UpgradeCycleResult:
        """
        Run the complete daily upgrade cycle.

        This is the main entry point called by auto_trading_service.

        Returns:
            UpgradeCycleResult with cycle details
        """
        result = UpgradeCycleResult()

        if not self.config.enabled:
            result.errors.append("Upgrade system is disabled")
            result.completed_at = datetime.now()
            return result

        logger.info("Starting self-upgrade cycle...")

        try:
            # Step 1: Analyze performance
            patterns = self.analyzer.analyze_recent_performance(days=7)
            result.patterns_found = len(patterns)

            if not patterns:
                logger.info("No losing patterns identified")
                result.completed_at = datetime.now()
                return result

            # Step 2: Generate proposals
            proposals = self.analyzer.generate_filter_proposals(
                patterns,
                max_proposals=self.config.max_proposals_per_cycle
            )
            result.proposals_generated = len(proposals)

            if not proposals:
                logger.info("No filter proposals generated")
                result.completed_at = datetime.now()
                return result

            # Step 3: Generate and deploy filters
            for proposal in proposals:
                try:
                    deployment = await self._process_proposal(proposal)
                    if deployment.success:
                        result.filters_deployed += 1
                        result.deployed_filters.append(deployment.filter_name)
                except Exception as e:
                    logger.error(f"Failed to process proposal {proposal.proposal_id}: {e}")
                    result.errors.append(str(e))

            # Step 4: Check existing filters for rollback
            rolled_back = await self._check_for_rollbacks()
            result.filters_rolled_back = len(rolled_back)
            result.rolled_back_filters = rolled_back

        except Exception as e:
            logger.exception("Upgrade cycle failed")
            result.errors.append(str(e))

        result.completed_at = datetime.now()
        self._last_upgrade_cycle = result.completed_at
        self._cycle_results.append(result)

        # Log summary
        logger.info(
            f"Upgrade cycle complete: {result.patterns_found} patterns, "
            f"{result.filters_deployed} deployed, {result.filters_rolled_back} rolled back"
        )

        return result

    async def _process_proposal(self, proposal: FilterProposal) -> DeploymentResult:
        """Process a single filter proposal through the pipeline."""

        # Log proposal to database
        proposal_db_id = self._log_proposal(proposal)

        # Generate filter code
        logger.info(f"Generating code for {proposal.filter_name}...")
        gen_result = self.generator.generate_filter_code_sync(proposal)

        if not gen_result.success:
            self._update_proposal_status(proposal_db_id, "GENERATION_FAILED", gen_result.error)
            return DeploymentResult(
                success=False,
                filter_name=proposal.filter_name,
                error=f"Code generation failed: {gen_result.error}"
            )

        # Validate code
        logger.info(f"Validating code for {proposal.filter_name}...")
        validation = self.validator.validate_and_test(gen_result.code)

        if not validation.is_valid:
            self._update_proposal_status(
                proposal_db_id,
                "VALIDATION_FAILED",
                "; ".join(validation.errors)
            )
            return DeploymentResult(
                success=False,
                filter_name=proposal.filter_name,
                error=f"Validation failed: {'; '.join(validation.errors)}"
            )

        # Test and deploy
        logger.info(f"Testing and deploying {proposal.filter_name}...")
        deployment = await self.executor.test_and_deploy(
            gen_result.code,
            proposal.filter_name,
            str(proposal_db_id)
        )

        if deployment.success:
            self._update_proposal_status(proposal_db_id, "DEPLOYED")
        else:
            self._update_proposal_status(proposal_db_id, "BACKTEST_FAILED", deployment.error)

        return deployment

    async def _check_for_rollbacks(self) -> List[str]:
        """Check all AI-generated filters for rollback conditions."""
        rolled_back = []
        registry = get_filter_registry()

        for filter_instance in registry.get_all():
            if filter_instance.filter_type != "ai_generated":
                continue

            perf = self.executor.check_filter_performance(filter_instance.name)

            if perf.get("should_rollback"):
                reason = perf.get("rollback_reason", "Performance degradation")
                if self.executor.rollback_filter(filter_instance.name, reason):
                    rolled_back.append(filter_instance.name)
                    logger.warning(f"Rolled back filter {filter_instance.name}: {reason}")

        return rolled_back

    def _log_proposal(self, proposal: FilterProposal) -> int:
        """Log a proposal to the database."""
        try:
            with db._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO upgrade_proposals (
                        timestamp, proposal_type, proposal_name,
                        trigger_reason, generated_code, ast_valid,
                        backtest_result, robustness_score, deployed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    proposal.pattern.pattern_type,
                    proposal.filter_name,
                    f"{proposal.pattern.severity}: {proposal.pattern.pattern_key} (win rate: {proposal.pattern.win_rate:.1f}%)",
                    None,  # Generated code will be added later
                    0,
                    None,
                    0.0,
                    0
                ))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to log proposal: {e}")
            return 0

    def _update_proposal_status(
        self,
        proposal_id: int,
        status: str,
        error: str = ""
    ) -> None:
        """Update proposal status in database."""
        if not proposal_id:
            return

        try:
            with db._connection() as conn:
                cursor = conn.cursor()

                deployed = 1 if status == "DEPLOYED" else 0
                ast_valid = 1 if status in ["DEPLOYED", "BACKTEST_FAILED"] else 0

                cursor.execute("""
                    UPDATE upgrade_proposals
                    SET ast_valid = ?, deployed = ?, backtest_result = ?
                    WHERE id = ?
                """, (
                    ast_valid,
                    deployed,
                    f"Status: {status}. {error}" if error else f"Status: {status}",
                    proposal_id
                ))
        except Exception as e:
            logger.error(f"Failed to update proposal status: {e}")

    def should_run_upgrade_cycle(self) -> bool:
        """Check if it's time to run an upgrade cycle."""
        if not self.config.enabled:
            return False

        if self._last_upgrade_cycle is None:
            return True

        hours_since_last = (datetime.now() - self._last_upgrade_cycle).total_seconds() / 3600
        return hours_since_last >= self.config.analysis_interval_hours

    def get_upgrade_status(self) -> Dict[str, Any]:
        """Get current status of the upgrade system."""
        registry = get_filter_registry()
        filter_stats = registry.get_stats()

        last_cycle = self._cycle_results[-1] if self._cycle_results else None

        return {
            "enabled": self.config.enabled,
            "last_cycle": {
                "timestamp": last_cycle.started_at.isoformat() if last_cycle else None,
                "patterns_found": last_cycle.patterns_found if last_cycle else 0,
                "filters_deployed": last_cycle.filters_deployed if last_cycle else 0,
                "filters_rolled_back": last_cycle.filters_rolled_back if last_cycle else 0,
            } if last_cycle else None,
            "total_filters": filter_stats["total_filters"],
            "ai_generated_filters": filter_stats["ai_generated_count"],
            "enabled_filters": filter_stats["enabled_filters"],
            "config": {
                "analysis_interval_hours": self.config.analysis_interval_hours,
                "min_trades_for_analysis": self.config.min_trades_for_analysis,
                "max_proposals_per_cycle": self.config.max_proposals_per_cycle,
                "min_robustness_score": self.config.min_robustness_score,
            }
        }

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get latest analysis summary."""
        return self.analyzer.get_analysis_summary()

    def force_rollback(self, filter_name: str, reason: str = "Manual rollback") -> bool:
        """Manually force rollback of a filter."""
        return self.executor.rollback_filter(filter_name, reason)

    def enable_filter(self, filter_name: str) -> bool:
        """Enable a disabled filter."""
        registry = get_filter_registry()
        return registry.enable_filter(filter_name)

    def disable_filter(self, filter_name: str) -> bool:
        """Disable an enabled filter."""
        registry = get_filter_registry()
        return registry.disable_filter(filter_name)


# Singleton instance
_manager_instance: Optional[UpgradeManager] = None


def get_upgrade_manager() -> UpgradeManager:
    """Get or create the global upgrade manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = UpgradeManager()
    return _manager_instance
