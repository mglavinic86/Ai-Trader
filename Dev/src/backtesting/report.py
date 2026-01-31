"""
Backtesting Report Generator

Prepares data for visualization and saves/loads reports.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .engine import BacktestResult
from .metrics import BacktestMetrics, MetricsCalculator


@dataclass
class BacktestReport:
    """Complete backtest report with metrics and chart data."""
    # Metadata
    report_id: str
    created_at: str
    instrument: str
    timeframe: str
    date_range: str

    # Results
    result: BacktestResult
    metrics: BacktestMetrics

    # Chart data (pre-processed for Plotly)
    equity_chart: dict = field(default_factory=dict)
    drawdown_chart: dict = field(default_factory=dict)
    trade_distribution: dict = field(default_factory=dict)
    monthly_returns: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize report to dictionary."""
        return {
            "report_id": self.report_id,
            "created_at": self.created_at,
            "instrument": self.instrument,
            "timeframe": self.timeframe,
            "date_range": self.date_range,
            "result": self.result.to_dict(),
            "metrics": self.metrics.to_dict(),
            "equity_chart": self.equity_chart,
            "drawdown_chart": self.drawdown_chart,
            "trade_distribution": self.trade_distribution,
            "monthly_returns": self.monthly_returns,
        }

    def save(self, directory: str = "data/backtests") -> str:
        """
        Save report to JSON file.

        Returns: Path to saved file
        """
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)

        filename = f"{self.report_id}.json"
        filepath = path / filename

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

        return str(filepath)

    @classmethod
    def load(cls, filepath: str) -> "BacktestReport":
        """Load report from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)

        # Reconstruct result and metrics (simplified - would need full reconstruction)
        # For now, return with raw dicts
        return cls(
            report_id=data["report_id"],
            created_at=data["created_at"],
            instrument=data["instrument"],
            timeframe=data["timeframe"],
            date_range=data["date_range"],
            result=data["result"],  # Raw dict
            metrics=data["metrics"],  # Raw dict
            equity_chart=data.get("equity_chart", {}),
            drawdown_chart=data.get("drawdown_chart", {}),
            trade_distribution=data.get("trade_distribution", {}),
            monthly_returns=data.get("monthly_returns", {}),
        )


class ReportGenerator:
    """Generates visualization-ready reports from backtest results."""

    def __init__(self):
        self.metrics_calculator = MetricsCalculator()

    def generate(self, result: BacktestResult) -> BacktestReport:
        """
        Generate complete report from backtest result.

        Args:
            result: BacktestResult from BacktestEngine

        Returns:
            BacktestReport with metrics and chart data
        """
        # Calculate metrics
        metrics = self.metrics_calculator.calculate(result)

        # Generate unique report ID
        report_id = f"{result.config.instrument}_{result.config.timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Prepare chart data
        equity_chart = self._prepare_equity_chart(result)
        drawdown_chart = self._prepare_drawdown_chart(result)
        trade_distribution = self._prepare_trade_distribution(result)
        monthly_returns = self._prepare_monthly_returns(result)

        return BacktestReport(
            report_id=report_id,
            created_at=datetime.now().isoformat(),
            instrument=result.config.instrument,
            timeframe=result.config.timeframe,
            date_range=f"{result.config.start_date.strftime('%Y-%m-%d')} to {result.config.end_date.strftime('%Y-%m-%d')}",
            result=result,
            metrics=metrics,
            equity_chart=equity_chart,
            drawdown_chart=drawdown_chart,
            trade_distribution=trade_distribution,
            monthly_returns=monthly_returns,
        )

    def _prepare_equity_chart(self, result: BacktestResult) -> dict:
        """Prepare equity curve data for Plotly line chart."""
        equity_curve = result.equity_curve

        if not equity_curve:
            return {"x": [], "y": [], "initial": result.initial_equity}

        times = [e["time"] for e in equity_curve]
        equities = [e["equity"] for e in equity_curve]

        # Also prepare trade markers
        trade_times = []
        trade_equities = []
        trade_types = []
        trade_colors = []

        # Map trades to equity curve
        trade_time_set = {t.entry_time: ("entry", t.direction.value) for t in result.trades}
        trade_time_set.update({t.exit_time: ("exit", t.pnl > 0) for t in result.trades if t.exit_time})

        for e in equity_curve:
            if e["time"] in trade_time_set:
                trade_times.append(e["time"])
                trade_equities.append(e["equity"])
                marker_type, marker_info = trade_time_set[e["time"]]
                trade_types.append(marker_type)
                if marker_type == "entry":
                    trade_colors.append("blue" if marker_info == "LONG" else "red")
                else:
                    trade_colors.append("green" if marker_info else "red")

        return {
            "x": times,
            "y": equities,
            "initial": result.initial_equity,
            "trades": {
                "x": trade_times,
                "y": trade_equities,
                "types": trade_types,
                "colors": trade_colors,
            }
        }

    def _prepare_drawdown_chart(self, result: BacktestResult) -> dict:
        """Prepare drawdown data for Plotly area chart."""
        equity_curve = result.equity_curve

        if not equity_curve:
            return {"x": [], "y": []}

        times = []
        drawdowns = []
        running_max = equity_curve[0]["equity"]

        for e in equity_curve:
            equity = e["equity"]
            if equity > running_max:
                running_max = equity
            dd_pct = ((running_max - equity) / running_max) * 100 if running_max > 0 else 0
            times.append(e["time"])
            drawdowns.append(-dd_pct)  # Negative for display below zero

        return {
            "x": times,
            "y": drawdowns,
        }

    def _prepare_trade_distribution(self, result: BacktestResult) -> dict:
        """Prepare trade P&L distribution for histogram."""
        trades = result.trades

        if not trades:
            return {"pnls": [], "pips": [], "bins": 20}

        pnls = [t.pnl for t in trades]
        pips = [t.pnl_pips for t in trades]

        # Categorize trades
        by_exit_reason = {}
        for t in trades:
            reason = t.exit_reason or "UNKNOWN"
            if reason not in by_exit_reason:
                by_exit_reason[reason] = []
            by_exit_reason[reason].append(t.pnl)

        return {
            "pnls": pnls,
            "pips": pips,
            "bins": min(20, len(trades)),
            "by_exit_reason": by_exit_reason,
            "winning": [p for p in pnls if p > 0],
            "losing": [p for p in pnls if p <= 0],
        }

    def _prepare_monthly_returns(self, result: BacktestResult) -> dict:
        """Prepare monthly returns data for heatmap."""
        equity_curve = result.equity_curve

        if not equity_curve:
            return {"months": [], "returns": []}

        # Parse timestamps and group by month
        monthly_data = {}

        for i, e in enumerate(equity_curve):
            try:
                # Parse ISO timestamp
                if isinstance(e["time"], str):
                    dt = datetime.fromisoformat(e["time"].replace("Z", "+00:00"))
                else:
                    dt = e["time"]

                month_key = dt.strftime("%Y-%m")

                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        "start_equity": e["equity"],
                        "end_equity": e["equity"],
                        "year": dt.year,
                        "month": dt.month
                    }
                else:
                    monthly_data[month_key]["end_equity"] = e["equity"]
            except Exception:
                continue

        # Calculate monthly returns
        months = []
        returns = []
        years = set()

        for month_key in sorted(monthly_data.keys()):
            data = monthly_data[month_key]
            start = data["start_equity"]
            end = data["end_equity"]
            ret = ((end - start) / start) * 100 if start > 0 else 0

            months.append(month_key)
            returns.append(ret)
            years.add(data["year"])

        # Prepare heatmap data
        heatmap_data = []
        for month_key, data in monthly_data.items():
            start = data["start_equity"]
            end = data["end_equity"]
            ret = ((end - start) / start) * 100 if start > 0 else 0

            heatmap_data.append({
                "year": data["year"],
                "month": data["month"],
                "return": ret,
                "month_key": month_key
            })

        return {
            "months": months,
            "returns": returns,
            "years": sorted(years),
            "heatmap_data": heatmap_data,
        }

    def list_saved_reports(self, directory: str = "data/backtests") -> list[dict]:
        """List all saved reports in directory."""
        path = Path(directory)
        if not path.exists():
            return []

        reports = []
        for filepath in path.glob("*.json"):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    reports.append({
                        "filename": filepath.name,
                        "report_id": data.get("report_id", ""),
                        "instrument": data.get("instrument", ""),
                        "timeframe": data.get("timeframe", ""),
                        "date_range": data.get("date_range", ""),
                        "created_at": data.get("created_at", ""),
                    })
            except Exception:
                continue

        # Sort by created_at descending
        reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return reports
