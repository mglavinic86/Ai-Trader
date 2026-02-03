"""
Backtesting Module for AI Trader

Provides walk-forward simulation using existing analysis modules.
Phase 3 Enhancement: Walk-Forward Validation and Monte Carlo.
"""

from .data_loader import DataLoader, HistoricalData, HistoricalDataRequest
from .engine import BacktestEngine, BacktestConfig, BacktestResult, SimulatedTrade
from .metrics import MetricsCalculator, BacktestMetrics
from .report import ReportGenerator, BacktestReport
from .walk_forward import (
    WalkForwardValidator,
    WalkForwardResult,
    WindowResult,
    MonteCarloSimulator,
    MonteCarloResult,
    validate_strategy,
)

__all__ = [
    # Data Loading
    "DataLoader",
    "HistoricalData",
    "HistoricalDataRequest",
    # Engine
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResult",
    "SimulatedTrade",
    # Metrics
    "MetricsCalculator",
    "BacktestMetrics",
    # Reporting
    "ReportGenerator",
    "BacktestReport",
    # Walk-Forward (Phase 3)
    "WalkForwardValidator",
    "WalkForwardResult",
    "WindowResult",
    "MonteCarloSimulator",
    "MonteCarloResult",
    "validate_strategy",
]
