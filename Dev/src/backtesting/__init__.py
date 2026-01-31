"""
Backtesting Module for AI Trader

Provides walk-forward simulation using existing analysis modules.
"""

from .data_loader import DataLoader, HistoricalData, HistoricalDataRequest
from .engine import BacktestEngine, BacktestConfig, BacktestResult, SimulatedTrade
from .metrics import MetricsCalculator, BacktestMetrics
from .report import ReportGenerator, BacktestReport

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
]
