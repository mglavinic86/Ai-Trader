"""
Backtesting Metrics Calculator

Calculates standard trading performance metrics:
- Total Return
- Max Drawdown
- Sharpe Ratio
- Sortino Ratio
- Win Rate
- Profit Factor
- Expectancy
"""

from dataclasses import dataclass, field
from typing import Optional
import math

from .engine import BacktestResult, SimulatedTrade


@dataclass
class BacktestMetrics:
    """Complete metrics for a backtest."""
    # Returns
    total_return_pct: float
    total_return_abs: float

    # Drawdown
    max_drawdown_pct: float
    max_drawdown_abs: float
    max_drawdown_duration_bars: int

    # Risk-adjusted returns
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]

    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    # Profit metrics
    gross_profit: float
    gross_loss: float
    profit_factor: Optional[float]
    expectancy: float
    expectancy_ratio: Optional[float]

    # Average trade
    avg_win: float
    avg_loss: float
    avg_trade: float
    largest_win: float
    largest_loss: float

    # Streaks
    max_consecutive_wins: int
    max_consecutive_losses: int

    # Time metrics
    avg_trade_duration_bars: float
    avg_bars_in_market: float

    def to_dict(self) -> dict:
        return {
            "total_return_pct": self.total_return_pct,
            "total_return_abs": self.total_return_abs,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_drawdown_abs": self.max_drawdown_abs,
            "max_drawdown_duration_bars": self.max_drawdown_duration_bars,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
            "expectancy_ratio": self.expectancy_ratio,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "avg_trade": self.avg_trade,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "avg_trade_duration_bars": self.avg_trade_duration_bars,
            "avg_bars_in_market": self.avg_bars_in_market,
        }

    def format_summary(self) -> str:
        """Format metrics as readable summary."""
        lines = [
            "=== BACKTEST METRICS ===",
            "",
            "--- RETURNS ---",
            f"Total Return: {self.total_return_pct:+.2f}% (${self.total_return_abs:+,.2f})",
            f"Max Drawdown: {self.max_drawdown_pct:.2f}% (${self.max_drawdown_abs:,.2f})",
            "",
            "--- RISK-ADJUSTED ---",
            f"Sharpe Ratio: {self.sharpe_ratio:.2f}" if self.sharpe_ratio else "Sharpe Ratio: N/A",
            f"Sortino Ratio: {self.sortino_ratio:.2f}" if self.sortino_ratio else "Sortino Ratio: N/A",
            "",
            "--- TRADE STATISTICS ---",
            f"Total Trades: {self.total_trades}",
            f"Win Rate: {self.win_rate:.1f}% ({self.winning_trades}W / {self.losing_trades}L)",
            f"Profit Factor: {self.profit_factor:.2f}" if self.profit_factor else "Profit Factor: N/A",
            f"Expectancy: ${self.expectancy:+.2f}",
            "",
            "--- AVERAGES ---",
            f"Avg Win: ${self.avg_win:,.2f}",
            f"Avg Loss: ${self.avg_loss:,.2f}",
            f"Avg Trade: ${self.avg_trade:+,.2f}",
            "",
            "--- EXTREMES ---",
            f"Largest Win: ${self.largest_win:,.2f}",
            f"Largest Loss: ${self.largest_loss:,.2f}",
            "",
            "--- STREAKS ---",
            f"Max Consecutive Wins: {self.max_consecutive_wins}",
            f"Max Consecutive Losses: {self.max_consecutive_losses}",
        ]
        return "\n".join(lines)


class MetricsCalculator:
    """Calculates backtesting performance metrics."""

    RISK_FREE_RATE = 0.04  # 4% annual risk-free rate
    TRADING_DAYS_PER_YEAR = 252

    def calculate(self, result: BacktestResult) -> BacktestMetrics:
        """
        Calculate all metrics from backtest result.

        Args:
            result: BacktestResult from BacktestEngine

        Returns:
            BacktestMetrics with all calculated values
        """
        trades = result.trades
        equity_curve = result.equity_curve

        # Returns
        total_return_abs = result.final_equity - result.initial_equity
        total_return_pct = (total_return_abs / result.initial_equity) * 100

        # Drawdown
        dd_result = self._calculate_drawdown(equity_curve)

        # Risk-adjusted returns
        sharpe, sortino = self._calculate_risk_adjusted(equity_curve)

        # Trade statistics
        trade_stats = self._calculate_trade_stats(trades)

        # Time metrics
        time_stats = self._calculate_time_stats(trades, equity_curve)

        return BacktestMetrics(
            # Returns
            total_return_pct=total_return_pct,
            total_return_abs=total_return_abs,
            # Drawdown
            max_drawdown_pct=dd_result["max_dd_pct"],
            max_drawdown_abs=dd_result["max_dd_abs"],
            max_drawdown_duration_bars=dd_result["max_dd_duration"],
            # Risk-adjusted
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            # Trade stats
            **trade_stats,
            # Time stats
            **time_stats
        )

    def _calculate_drawdown(self, equity_curve: list[dict]) -> dict:
        """Calculate maximum drawdown metrics."""
        if not equity_curve:
            return {
                "max_dd_pct": 0.0,
                "max_dd_abs": 0.0,
                "max_dd_duration": 0
            }

        equities = [e["equity"] for e in equity_curve]
        running_max = equities[0]
        max_dd_pct = 0.0
        max_dd_abs = 0.0
        max_dd_duration = 0
        current_dd_duration = 0

        for equity in equities:
            if equity > running_max:
                running_max = equity
                current_dd_duration = 0
            else:
                current_dd_duration += 1
                dd_abs = running_max - equity
                dd_pct = (dd_abs / running_max) * 100 if running_max > 0 else 0

                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct
                    max_dd_abs = dd_abs

                if current_dd_duration > max_dd_duration:
                    max_dd_duration = current_dd_duration

        return {
            "max_dd_pct": max_dd_pct,
            "max_dd_abs": max_dd_abs,
            "max_dd_duration": max_dd_duration
        }

    def _calculate_risk_adjusted(
        self,
        equity_curve: list[dict]
    ) -> tuple[Optional[float], Optional[float]]:
        """Calculate Sharpe and Sortino ratios."""
        if len(equity_curve) < 2:
            return None, None

        # Calculate returns
        equities = [e["equity"] for e in equity_curve]
        returns = []
        for i in range(1, len(equities)):
            if equities[i - 1] > 0:
                ret = (equities[i] - equities[i - 1]) / equities[i - 1]
                returns.append(ret)

        if len(returns) < 2:
            return None, None

        # Mean and std of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_return = math.sqrt(variance) if variance > 0 else 0

        # Daily risk-free rate
        daily_rf = self.RISK_FREE_RATE / self.TRADING_DAYS_PER_YEAR

        # Sharpe Ratio
        if std_return > 0:
            sharpe = (mean_return - daily_rf) / std_return * math.sqrt(self.TRADING_DAYS_PER_YEAR)
        else:
            sharpe = None

        # Sortino Ratio (downside deviation)
        negative_returns = [r for r in returns if r < 0]
        if negative_returns:
            downside_variance = sum(r ** 2 for r in negative_returns) / len(returns)
            downside_std = math.sqrt(downside_variance)
            if downside_std > 0:
                sortino = (mean_return - daily_rf) / downside_std * math.sqrt(self.TRADING_DAYS_PER_YEAR)
            else:
                sortino = None
        else:
            sortino = None  # No negative returns

        return sharpe, sortino

    def _calculate_trade_stats(self, trades: list[SimulatedTrade]) -> dict:
        """Calculate trade-based statistics."""
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "profit_factor": None,
                "expectancy": 0.0,
                "expectancy_ratio": None,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "avg_trade": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
            }

        total_trades = len(trades)
        pnls = [t.pnl for t in trades]

        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]

        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0

        # Averages
        avg_win = gross_profit / win_count if win_count > 0 else 0
        avg_loss = gross_loss / loss_count if loss_count > 0 else 0
        avg_trade = sum(pnls) / total_trades if total_trades > 0 else 0

        # Profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None

        # Expectancy
        expectancy = avg_trade

        # Expectancy ratio (avg win / avg loss)
        expectancy_ratio = avg_win / avg_loss if avg_loss > 0 else None

        # Extremes
        largest_win = max(pnls) if pnls else 0
        largest_loss = min(pnls) if pnls else 0

        # Streaks
        max_wins, max_losses = self._calculate_streaks(trades)

        return {
            "total_trades": total_trades,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate": win_rate,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "expectancy_ratio": expectancy_ratio,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "avg_trade": avg_trade,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "max_consecutive_wins": max_wins,
            "max_consecutive_losses": max_losses,
        }

    def _calculate_streaks(self, trades: list[SimulatedTrade]) -> tuple[int, int]:
        """Calculate maximum consecutive wins and losses."""
        if not trades:
            return 0, 0

        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in trades:
            if trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return max_wins, max_losses

    def _calculate_time_stats(
        self,
        trades: list[SimulatedTrade],
        equity_curve: list[dict]
    ) -> dict:
        """Calculate time-based statistics."""
        if not trades or not equity_curve:
            return {
                "avg_trade_duration_bars": 0.0,
                "avg_bars_in_market": 0.0
            }

        # Count bars with positions
        bars_with_position = sum(1 for e in equity_curve if e.get("has_position", False))
        avg_bars_in_market = (bars_with_position / len(equity_curve)) * 100 if equity_curve else 0

        # Average trade duration (simplified - would need bar timestamps)
        avg_trade_duration = bars_with_position / len(trades) if trades else 0

        return {
            "avg_trade_duration_bars": avg_trade_duration,
            "avg_bars_in_market": avg_bars_in_market
        }
