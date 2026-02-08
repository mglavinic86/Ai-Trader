"""
Walk-Forward Validation - Proper Out-of-Sample Testing.

Uses the SMC+ISI backtesting engine with rolling windows to validate
trading strategies without look-ahead bias.

Methodology:
1. Load all data once (H4/H1/M5) for the full date range + lookback buffer
2. Split into rolling train/test windows
3. Run SMCBacktestEngine on each window (train then test)
4. Aggregate out-of-sample results
5. Monte Carlo simulation on all OOS trades

Usage:
    from src.backtesting.walk_forward import WalkForwardValidator, WalkForwardConfig

    wf_config = WalkForwardConfig(
        instrument="EUR_USD",
        train_days=45,
        test_days=15,
        windows=4,
    )
    validator = WalkForwardValidator()
    result = validator.run(wf_config, h4_candles, h1_candles, m5_candles)
"""

import os
import random
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np

from src.utils.logger import logger


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward validation."""
    instrument: str
    train_days: int = 45
    test_days: int = 15
    windows: int = 4

    # Backtest parameters
    initial_capital: float = 50000.0
    min_confidence: int = 70
    min_grade: str = "B"
    target_rr: float = 2.0
    max_sl_pips: float = 15.0
    spread_pips: float = 1.2
    slippage_pips: float = 0.2
    commission_per_lot: float = 7.0
    risk_percent: float = 0.003
    check_regime: bool = True
    check_session: bool = True
    session_hours: Optional[list] = None
    signal_interval: int = 6

    # ISI toggles
    isi_sequence_tracker: bool = False
    isi_cross_asset: bool = False
    isi_calibrator: bool = False

    # Monte Carlo
    monte_carlo_iterations: int = 1000
    monte_carlo_seed: Optional[int] = 42


@dataclass
class WindowResult:
    """Result from a single train/test window."""
    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime

    # Training metrics
    train_trades: int = 0
    train_win_rate: float = 0.0
    train_sharpe: float = 0.0
    train_pnl: float = 0.0

    # Test metrics (out-of-sample)
    test_trades: int = 0
    test_win_rate: float = 0.0
    test_sharpe: float = 0.0
    test_pnl: float = 0.0

    # OOS trade objects for Monte Carlo
    test_trade_pnls: List[float] = field(default_factory=list)

    # Stability
    win_rate_decay: float = 0.0  # Test WR - Train WR (negative = overfit)
    sharpe_decay: float = 0.0

    def to_dict(self) -> dict:
        return {
            "window_id": self.window_id,
            "train_period": f"{self.train_start.date()} to {self.train_end.date()}",
            "test_period": f"{self.test_start.date()} to {self.test_end.date()}",
            "train_trades": self.train_trades,
            "train_win_rate": self.train_win_rate,
            "train_sharpe": self.train_sharpe,
            "train_pnl": self.train_pnl,
            "test_trades": self.test_trades,
            "test_win_rate": self.test_win_rate,
            "test_sharpe": self.test_sharpe,
            "test_pnl": self.test_pnl,
            "win_rate_decay": self.win_rate_decay,
            "sharpe_decay": self.sharpe_decay,
        }


@dataclass
class MonteCarloResult:
    """Result from Monte Carlo simulation."""
    iterations: int = 1000

    # Confidence intervals
    p5_return: float = 0.0
    p50_return: float = 0.0
    p95_return: float = 0.0

    p5_drawdown: float = 0.0
    p50_drawdown: float = 0.0
    p95_drawdown: float = 0.0

    # Probabilities
    prob_profit: float = 0.0
    prob_drawdown_10pct: float = 0.0
    prob_drawdown_20pct: float = 0.0

    # Distribution (sample)
    return_distribution: List[float] = field(default_factory=list)
    drawdown_distribution: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "iterations": self.iterations,
            "p5_return": self.p5_return,
            "p50_return": self.p50_return,
            "p95_return": self.p95_return,
            "p5_drawdown": self.p5_drawdown,
            "p50_drawdown": self.p50_drawdown,
            "p95_drawdown": self.p95_drawdown,
            "prob_profit": self.prob_profit,
            "prob_drawdown_10pct": self.prob_drawdown_10pct,
            "prob_drawdown_20pct": self.prob_drawdown_20pct,
        }


@dataclass
class WalkForwardResult:
    """Aggregated walk-forward validation results."""
    instrument: str
    total_windows: int
    train_days: int
    test_days: int

    # Windows
    windows: List[WindowResult] = field(default_factory=list)

    # Aggregated in-sample metrics
    avg_train_win_rate: float = 0.0
    avg_train_sharpe: float = 0.0
    total_train_pnl: float = 0.0

    # Aggregated out-of-sample metrics
    avg_test_win_rate: float = 0.0
    avg_test_sharpe: float = 0.0
    total_test_pnl: float = 0.0

    # Stability metrics
    avg_win_rate_decay: float = 0.0
    avg_sharpe_decay: float = 0.0
    consistency_score: float = 0.0  # % of windows profitable OOS

    # Robustness
    robustness_score: float = 0.0  # 0-100

    # Monte Carlo
    monte_carlo: Optional[MonteCarloResult] = None

    def to_dict(self) -> dict:
        d = {
            "instrument": self.instrument,
            "total_windows": self.total_windows,
            "train_days": self.train_days,
            "test_days": self.test_days,
            "avg_train_win_rate": self.avg_train_win_rate,
            "avg_train_sharpe": self.avg_train_sharpe,
            "total_train_pnl": self.total_train_pnl,
            "avg_test_win_rate": self.avg_test_win_rate,
            "avg_test_sharpe": self.avg_test_sharpe,
            "total_test_pnl": self.total_test_pnl,
            "avg_win_rate_decay": self.avg_win_rate_decay,
            "avg_sharpe_decay": self.avg_sharpe_decay,
            "consistency_score": self.consistency_score,
            "robustness_score": self.robustness_score,
            "windows": [w.to_dict() for w in self.windows],
        }
        if self.monte_carlo:
            d["monte_carlo"] = self.monte_carlo.to_dict()
        return d

    def format_summary(self) -> str:
        lines = [
            "",
            "WALK-FORWARD VALIDATION RESULTS",
            "================================",
            f"Instrument: {self.instrument}",
            f"Windows: {self.total_windows} (Train: {self.train_days}d, Test: {self.test_days}d)",
            "",
            "IN-SAMPLE (Training):",
            f"  Avg Win Rate: {self.avg_train_win_rate:.1f}%",
            f"  Avg Sharpe:   {self.avg_train_sharpe:.2f}",
            f"  Total P/L:    {self.total_train_pnl:.2f}",
            "",
            "OUT-OF-SAMPLE (Testing):",
            f"  Avg Win Rate: {self.avg_test_win_rate:.1f}%",
            f"  Avg Sharpe:   {self.avg_test_sharpe:.2f}",
            f"  Total P/L:    {self.total_test_pnl:.2f}",
            "",
            "STABILITY:",
            f"  Win Rate Decay: {self.avg_win_rate_decay:+.1f}%",
            f"  Sharpe Decay:   {self.avg_sharpe_decay:+.2f}",
            f"  Consistency:    {self.consistency_score:.0f}% windows profitable OOS",
            "",
            f"ROBUSTNESS SCORE: {self.robustness_score:.0f}/100",
        ]

        if self.monte_carlo:
            mc = self.monte_carlo
            lines.extend([
                "",
                f"MONTE CARLO ({mc.iterations} iterations):",
                f"  Return (5/50/95%):   {mc.p5_return:+.2f}% / {mc.p50_return:+.2f}% / {mc.p95_return:+.2f}%",
                f"  Drawdown (5/50/95%): {mc.p5_drawdown:.2f}% / {mc.p50_drawdown:.2f}% / {mc.p95_drawdown:.2f}%",
                f"  P(Profit):           {mc.prob_profit:.0%}",
                f"  P(DD>10%):           {mc.prob_drawdown_10pct:.0%}",
                f"  P(DD>20%):           {mc.prob_drawdown_20pct:.0%}",
            ])

        return "\n".join(lines)


def _slice_candles(candles: list, start_ts: float, end_ts: float) -> list:
    """Slice candles by timestamp range (inclusive)."""
    return [c for c in candles if start_ts <= c["timestamp"] <= end_ts]


class WalkForwardValidator:
    """
    Walk-forward validation using SMCBacktestEngine.

    Uses rolling windows on pre-loaded candle data.
    ISI components use temp DB files to avoid prod DB contamination.
    """

    def run(
        self,
        wf_config: WalkForwardConfig,
        h4_candles: list,
        h1_candles: list,
        m5_candles: list,
        cross_asset_data: Optional[Dict[str, list]] = None,
    ) -> WalkForwardResult:
        """
        Run walk-forward validation.

        Args:
            wf_config: Walk-forward configuration
            h4_candles: Full H4 candle array (sorted by timestamp)
            h1_candles: Full H1 candle array (sorted by timestamp)
            m5_candles: Full M5 candle array (sorted by timestamp)
            cross_asset_data: Optional {instrument: [m5_candles]} for ISI

        Returns:
            WalkForwardResult with aggregated metrics
        """
        from src.backtesting.engine import SMCBacktestEngine, BacktestConfig
        from src.backtesting.metrics import MetricsCalculator

        logger.info(
            f"Walk-Forward starting: {wf_config.instrument}, "
            f"{wf_config.windows} windows ({wf_config.train_days}d train, "
            f"{wf_config.test_days}d test)"
        )

        result = WalkForwardResult(
            instrument=wf_config.instrument,
            total_windows=wf_config.windows,
            train_days=wf_config.train_days,
            test_days=wf_config.test_days,
        )

        # Calculate window boundaries from the end of available data
        if not m5_candles:
            logger.error("No M5 candles provided")
            return result

        # Use M5 timestamps to define windows
        last_ts = m5_candles[-1]["timestamp"]
        last_dt = datetime.fromtimestamp(last_ts)

        total_days = wf_config.windows * (wf_config.train_days + wf_config.test_days)
        first_dt = last_dt - timedelta(days=total_days)

        # Create temp DB for ISI isolation
        temp_db_path = None
        if (wf_config.isi_sequence_tracker or wf_config.isi_calibrator):
            temp_db_path = tempfile.mktemp(suffix="_wf.db")

        engine = SMCBacktestEngine()
        calc = MetricsCalculator()
        all_oos_pnls = []
        window_results = []

        try:
            for i in range(wf_config.windows):
                window_offset = i * (wf_config.train_days + wf_config.test_days)
                train_start = first_dt + timedelta(days=window_offset)
                train_end = train_start + timedelta(days=wf_config.train_days)
                test_start = train_end
                test_end = test_start + timedelta(days=wf_config.test_days)

                train_start_ts = train_start.timestamp()
                train_end_ts = train_end.timestamp()
                test_start_ts = test_start.timestamp()
                test_end_ts = test_end.timestamp()

                # Add lookback buffer (15 days) for train start
                buffer_ts = (train_start - timedelta(days=15)).timestamp()

                # Slice candles for train period (with buffer for HTF context)
                train_h4 = _slice_candles(h4_candles, buffer_ts, train_end_ts)
                train_h1 = _slice_candles(h1_candles, buffer_ts, train_end_ts)
                train_m5 = _slice_candles(m5_candles, buffer_ts, train_end_ts)

                # Slice candles for test period (with buffer)
                test_buffer_ts = (test_start - timedelta(days=15)).timestamp()
                test_h4 = _slice_candles(h4_candles, test_buffer_ts, test_end_ts)
                test_h1 = _slice_candles(h1_candles, test_buffer_ts, test_end_ts)
                test_m5 = _slice_candles(m5_candles, test_buffer_ts, test_end_ts)

                # Slice cross-asset data if present
                train_xa = None
                test_xa = None
                if cross_asset_data and wf_config.isi_cross_asset:
                    train_xa = {
                        k: _slice_candles(v, buffer_ts, train_end_ts)
                        for k, v in cross_asset_data.items()
                    }
                    test_xa = {
                        k: _slice_candles(v, test_buffer_ts, test_end_ts)
                        for k, v in cross_asset_data.items()
                    }

                # Build BacktestConfig
                spread = 1.2
                if "GBP" in wf_config.instrument:
                    spread = 1.8
                if "XAU" in wf_config.instrument:
                    spread = 3.0

                base_config = BacktestConfig(
                    instrument=wf_config.instrument,
                    timeframe="M5",
                    start_date=train_start,
                    end_date=train_end,
                    initial_capital=wf_config.initial_capital,
                    min_confidence=wf_config.min_confidence,
                    min_grade=wf_config.min_grade,
                    target_rr=wf_config.target_rr,
                    max_sl_pips=wf_config.max_sl_pips,
                    max_positions=1,
                    spread_pips=spread,
                    slippage_pips=wf_config.slippage_pips,
                    commission_per_lot=wf_config.commission_per_lot,
                    risk_percent=wf_config.risk_percent,
                    check_regime=wf_config.check_regime,
                    check_session=wf_config.check_session,
                    session_hours=wf_config.session_hours or [(7, 17)],
                    signal_interval=wf_config.signal_interval,
                    htf_lookback=100,
                    ltf_lookback=100,
                    isi_sequence_tracker=wf_config.isi_sequence_tracker,
                    isi_cross_asset=wf_config.isi_cross_asset,
                    isi_calibrator=wf_config.isi_calibrator,
                )

                # Patch engine to use temp DB if ISI enabled
                if temp_db_path:
                    self._patch_engine_db(temp_db_path)

                # --- Run training period ---
                window_result = WindowResult(
                    window_id=i + 1,
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                )

                if len(train_m5) > 50:
                    try:
                        train_bt = engine.run(
                            train_h4, train_h1, train_m5, base_config,
                            cross_asset_data=train_xa,
                        )
                        if train_bt.trades:
                            train_metrics = calc.calculate(train_bt)
                            window_result.train_trades = len(train_bt.trades)
                            window_result.train_win_rate = train_metrics.win_rate
                            window_result.train_sharpe = train_metrics.sharpe_ratio or 0
                            window_result.train_pnl = train_metrics.total_return_abs
                    except Exception as e:
                        logger.warning(f"Train backtest failed window {i+1}: {e}")

                # --- Run test period ---
                test_config = BacktestConfig(
                    instrument=wf_config.instrument,
                    timeframe="M5",
                    start_date=test_start,
                    end_date=test_end,
                    initial_capital=wf_config.initial_capital,
                    min_confidence=wf_config.min_confidence,
                    min_grade=wf_config.min_grade,
                    target_rr=wf_config.target_rr,
                    max_sl_pips=wf_config.max_sl_pips,
                    max_positions=1,
                    spread_pips=spread,
                    slippage_pips=wf_config.slippage_pips,
                    commission_per_lot=wf_config.commission_per_lot,
                    risk_percent=wf_config.risk_percent,
                    check_regime=wf_config.check_regime,
                    check_session=wf_config.check_session,
                    session_hours=wf_config.session_hours or [(7, 17)],
                    signal_interval=wf_config.signal_interval,
                    htf_lookback=100,
                    ltf_lookback=100,
                    isi_sequence_tracker=wf_config.isi_sequence_tracker,
                    isi_cross_asset=wf_config.isi_cross_asset,
                    isi_calibrator=wf_config.isi_calibrator,
                )

                if len(test_m5) > 50:
                    try:
                        test_bt = engine.run(
                            test_h4, test_h1, test_m5, test_config,
                            cross_asset_data=test_xa,
                        )
                        if test_bt.trades:
                            test_metrics = calc.calculate(test_bt)
                            window_result.test_trades = len(test_bt.trades)
                            window_result.test_win_rate = test_metrics.win_rate
                            window_result.test_sharpe = test_metrics.sharpe_ratio or 0
                            window_result.test_pnl = test_metrics.total_return_abs
                            window_result.test_trade_pnls = [
                                t.pnl for t in test_bt.trades
                            ]
                            all_oos_pnls.extend(window_result.test_trade_pnls)
                    except Exception as e:
                        logger.warning(f"Test backtest failed window {i+1}: {e}")

                # Decay metrics
                window_result.win_rate_decay = (
                    window_result.test_win_rate - window_result.train_win_rate
                )
                window_result.sharpe_decay = (
                    window_result.test_sharpe - window_result.train_sharpe
                )

                window_results.append(window_result)
                logger.info(
                    f"Window {i+1}: Train {window_result.train_trades} trades "
                    f"WR={window_result.train_win_rate:.1f}%, "
                    f"Test {window_result.test_trades} trades "
                    f"WR={window_result.test_win_rate:.1f}% "
                    f"(decay: {window_result.win_rate_decay:+.1f}%)"
                )

        finally:
            # Restore prod DB path and cleanup temp DB
            if temp_db_path:
                self._restore_engine_db()
                if os.path.exists(temp_db_path):
                    try:
                        os.remove(temp_db_path)
                    except Exception:
                        pass

        result.windows = window_results
        self._aggregate_results(result)

        # Monte Carlo on all OOS trades
        if all_oos_pnls and len(all_oos_pnls) >= 3:
            mc_sim = MonteCarloSimulator(seed=wf_config.monte_carlo_seed)
            trade_dicts = [{"pnl": p} for p in all_oos_pnls]
            result.monte_carlo = mc_sim.run(
                trade_dicts,
                iterations=wf_config.monte_carlo_iterations,
                initial_balance=wf_config.initial_capital,
            )

        return result

    @staticmethod
    def _patch_engine_db(temp_db_path: str):
        """
        Monkey-patch the database module's default path so ISI components
        in the engine use a temp DB instead of production.

        The engine lazy-imports Database inside run(), and Database()
        defaults to src.utils.database._db_path.
        """
        import src.utils.database as db_module
        db_module._db_path = Path(temp_db_path)

    @staticmethod
    def _restore_engine_db():
        """Restore the default production DB path."""
        import src.utils.database as db_module
        _dev_dir = Path(__file__).parent.parent.parent
        db_module._db_path = _dev_dir / "data" / "trades.db"

    def _aggregate_results(self, result: WalkForwardResult):
        """Aggregate window results into summary metrics."""
        if not result.windows:
            return

        n = len(result.windows)

        # Training averages
        result.avg_train_win_rate = sum(w.train_win_rate for w in result.windows) / n
        result.avg_train_sharpe = sum(w.train_sharpe for w in result.windows) / n
        result.total_train_pnl = sum(w.train_pnl for w in result.windows)

        # Testing averages
        result.avg_test_win_rate = sum(w.test_win_rate for w in result.windows) / n
        result.avg_test_sharpe = sum(w.test_sharpe for w in result.windows) / n
        result.total_test_pnl = sum(w.test_pnl for w in result.windows)

        # Decay metrics
        result.avg_win_rate_decay = sum(w.win_rate_decay for w in result.windows) / n
        result.avg_sharpe_decay = sum(w.sharpe_decay for w in result.windows) / n

        # Consistency (% of windows profitable OOS)
        profitable_windows = sum(1 for w in result.windows if w.test_pnl > 0)
        result.consistency_score = (profitable_windows / n) * 100

        # Robustness score (0-100)
        result.robustness_score = self._calculate_robustness(result)

    def _calculate_robustness(self, result: WalkForwardResult) -> float:
        """Calculate robustness score from validation results."""
        score = 50.0

        # OOS win rate bonus/penalty
        if result.avg_test_win_rate >= 55:
            score += (result.avg_test_win_rate - 55) * 1.5
        elif result.avg_test_win_rate < 45:
            score -= (45 - result.avg_test_win_rate) * 2

        # OOS Sharpe bonus
        if result.avg_test_sharpe >= 1.0:
            score += min(20, (result.avg_test_sharpe - 1.0) * 10)
        elif result.avg_test_sharpe is not None and result.avg_test_sharpe < 0.5:
            score -= 15

        # Decay penalty
        if result.avg_win_rate_decay < -10:
            score -= 15  # Significant overfit
        elif result.avg_win_rate_decay < -5:
            score -= 8

        # Consistency bonus
        if result.consistency_score >= 80:
            score += 15
        elif result.consistency_score >= 60:
            score += 8
        elif result.consistency_score < 40:
            score -= 10

        return max(0, min(100, score))


class MonteCarloSimulator:
    """
    Monte Carlo simulation for robustness testing.

    Randomizes trade sequence to estimate confidence intervals
    and worst-case scenarios.
    """

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

    def run(
        self,
        trades: List[Dict[str, Any]],
        iterations: int = 1000,
        initial_balance: float = 10000.0,
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation.

        Args:
            trades: List of trade dicts with 'pnl' field
            iterations: Number of simulation runs
            initial_balance: Starting balance

        Returns:
            MonteCarloResult with distributions
        """
        if not trades:
            logger.warning("No trades provided for Monte Carlo simulation")
            return MonteCarloResult(iterations=iterations)

        pnl_values = [t.get("pnl", 0) for t in trades if t.get("pnl") is not None]

        if not pnl_values:
            return MonteCarloResult(iterations=iterations)

        returns = []
        drawdowns = []

        for _ in range(iterations):
            shuffled = pnl_values.copy()
            random.shuffle(shuffled)

            equity = initial_balance
            peak = equity
            max_dd = 0

            for pnl in shuffled:
                equity += pnl
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak * 100 if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd

            total_return = (equity - initial_balance) / initial_balance * 100
            returns.append(total_return)
            drawdowns.append(max_dd)

        returns_arr = np.array(returns)
        drawdowns_arr = np.array(drawdowns)

        result = MonteCarloResult(
            iterations=iterations,
            p5_return=float(np.percentile(returns_arr, 5)),
            p50_return=float(np.percentile(returns_arr, 50)),
            p95_return=float(np.percentile(returns_arr, 95)),
            p5_drawdown=float(np.percentile(drawdowns_arr, 5)),
            p50_drawdown=float(np.percentile(drawdowns_arr, 50)),
            p95_drawdown=float(np.percentile(drawdowns_arr, 95)),
            prob_profit=float(np.mean(returns_arr > 0)),
            prob_drawdown_10pct=float(np.mean(drawdowns_arr > 10)),
            prob_drawdown_20pct=float(np.mean(drawdowns_arr > 20)),
            return_distribution=returns[:100],
            drawdown_distribution=drawdowns[:100],
        )

        logger.info(
            f"Monte Carlo ({iterations} iterations): "
            f"Return 5/50/95%: {result.p5_return:.1f}%/{result.p50_return:.1f}%/{result.p95_return:.1f}%, "
            f"P(profit)={result.prob_profit:.0%}"
        )

        return result


def validate_strategy(
    instrument: str,
    h4_candles: list,
    h1_candles: list,
    m5_candles: list,
    train_days: int = 45,
    test_days: int = 15,
    windows: int = 4,
    cross_asset_data: Optional[Dict[str, list]] = None,
) -> WalkForwardResult:
    """Convenience function for walk-forward validation."""
    wf_config = WalkForwardConfig(
        instrument=instrument,
        train_days=train_days,
        test_days=test_days,
        windows=windows,
    )
    validator = WalkForwardValidator()
    return validator.run(wf_config, h4_candles, h1_candles, m5_candles, cross_asset_data)
