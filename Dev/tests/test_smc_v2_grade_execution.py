"""Tests for SMC v2 grade-based execution gating in AutoExecutor."""

import sys
from pathlib import Path
from types import SimpleNamespace

# Add Dev to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.auto_config import AutoTradingConfig
from src.trading.auto_executor import AutoExecutor


def _make_executor_with_config(config: AutoTradingConfig) -> AutoExecutor:
    """Create AutoExecutor instance without full runtime initialization."""
    executor = AutoExecutor.__new__(AutoExecutor)
    executor.config = config
    return executor


def _make_signal(grade: str, confidence: int):
    """Create minimal signal object for grade validation."""
    return SimpleNamespace(
        confidence=confidence,
        smc_analysis=SimpleNamespace(setup_grade=grade),
    )


def test_grade_execution_disabled_allows_signal():
    cfg = AutoTradingConfig()
    cfg.smc_v2.enabled = False
    cfg.smc_v2.grade_execution.enabled = False
    ex = _make_executor_with_config(cfg)

    ok, reason = ex._validate_grade_execution(_make_signal("B", 55))
    assert ok is True
    assert "disabled" in reason.lower()


def test_blocks_b_grade_when_enabled():
    cfg = AutoTradingConfig()
    cfg.smc_v2.enabled = True
    cfg.smc_v2.grade_execution.enabled = True
    ex = _make_executor_with_config(cfg)

    ok, reason = ex._validate_grade_execution(_make_signal("B", 90))
    assert ok is False
    assert "shadow-only" in reason


def test_blocks_a_when_confidence_below_threshold():
    cfg = AutoTradingConfig()
    cfg.smc_v2.enabled = True
    cfg.smc_v2.grade_execution.enabled = True
    cfg.smc_v2.grade_execution.min_confidence_a = 60
    ex = _make_executor_with_config(cfg)

    ok, reason = ex._validate_grade_execution(_make_signal("A", 58))
    assert ok is False
    assert "A confidence" in reason


def test_allows_a_plus_when_confidence_sufficient():
    cfg = AutoTradingConfig()
    cfg.smc_v2.enabled = True
    cfg.smc_v2.grade_execution.enabled = True
    cfg.smc_v2.grade_execution.min_confidence_a_plus = 45
    ex = _make_executor_with_config(cfg)

    ok, reason = ex._validate_grade_execution(_make_signal("A+", 52))
    assert ok is True
    assert "allowed" in reason.lower()


def test_a_plus_only_mode_blocks_a_grade():
    cfg = AutoTradingConfig()
    cfg.smc_v2.enabled = True
    cfg.smc_v2.grade_execution.enabled = True
    cfg.smc_v2.grade_execution.a_plus_only_live = True
    ex = _make_executor_with_config(cfg)

    ok, reason = ex._validate_grade_execution(_make_signal("A", 90))
    assert ok is False
    assert "A+ only" in reason
