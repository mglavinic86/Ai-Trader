"""
Backtesting Engine

Walk-forward simulation using existing analysis modules:
- TechnicalAnalyzer
- SentimentAnalyzer
- AdversarialEngine
- ConfidenceCalculator
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable
from enum import Enum

# Import existing analyzers
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.market.indicators import TechnicalAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.analysis.adversarial import AdversarialEngine
from src.analysis.confidence import ConfidenceCalculator


class TradeDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    instrument: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    min_confidence: int = 50  # Minimum confidence to trade
    use_adversarial: bool = True
    lookback_bars: int = 50  # Bars needed for analysis
    atr_sl_multiplier: float = 2.0  # SL = ATR * multiplier
    atr_tp_multiplier: float = 4.0  # TP = ATR * multiplier (2:1 R:R)
    max_positions: int = 1  # Max concurrent positions


@dataclass
class SimulatedTrade:
    """Represents a simulated trade."""
    entry_time: str
    entry_price: float
    direction: TradeDirection
    stop_loss: float
    take_profit: float
    units: int
    confidence: int
    risk_tier: str

    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # SL, TP, SIGNAL
    pnl: float = 0.0
    pnl_pips: float = 0.0

    @property
    def is_open(self) -> bool:
        return self.exit_time is None

    @property
    def is_winner(self) -> bool:
        return self.pnl > 0

    def to_dict(self) -> dict:
        return {
            "entry_time": self.entry_time,
            "entry_price": self.entry_price,
            "direction": self.direction.value,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "units": self.units,
            "confidence": self.confidence,
            "risk_tier": self.risk_tier,
            "exit_time": self.exit_time,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "pnl": self.pnl,
            "pnl_pips": self.pnl_pips,
        }


@dataclass
class BacktestState:
    """Current state of the backtest simulation."""
    equity: float
    cash: float
    open_position: Optional[SimulatedTrade] = None
    closed_trades: list[SimulatedTrade] = field(default_factory=list)
    equity_curve: list[dict] = field(default_factory=list)


@dataclass
class BacktestResult:
    """Complete backtest result."""
    config: BacktestConfig
    trades: list[SimulatedTrade]
    equity_curve: list[dict]
    initial_equity: float
    final_equity: float
    total_bars: int
    bars_analyzed: int
    run_time_seconds: float

    def to_dict(self) -> dict:
        return {
            "config": {
                "instrument": self.config.instrument,
                "timeframe": self.config.timeframe,
                "start_date": self.config.start_date.isoformat(),
                "end_date": self.config.end_date.isoformat(),
                "initial_capital": self.config.initial_capital,
                "min_confidence": self.config.min_confidence,
                "use_adversarial": self.config.use_adversarial,
            },
            "trades": [t.to_dict() for t in self.trades],
            "equity_curve": self.equity_curve,
            "initial_equity": self.initial_equity,
            "final_equity": self.final_equity,
            "total_bars": self.total_bars,
            "bars_analyzed": self.bars_analyzed,
            "run_time_seconds": self.run_time_seconds,
        }


class BacktestEngine:
    """
    Walk-forward backtesting engine.

    Uses existing analysis modules to generate signals
    and simulates trade execution on historical data.
    """

    def __init__(self):
        self.technical = TechnicalAnalyzer()
        self.sentiment = SentimentAnalyzer()
        self.adversarial = AdversarialEngine()
        self.confidence = ConfidenceCalculator()

    def _get_pip_value(self, instrument: str) -> float:
        """Get pip value for instrument."""
        if "BTC" in instrument or "ETH" in instrument:
            return 1.0
        if "JPY" in instrument:
            return 0.01
        return 0.0001

    def _calculate_pnl(
        self,
        entry_price: float,
        exit_price: float,
        direction: TradeDirection,
        units: int,
        instrument: str
    ) -> tuple[float, float]:
        """Calculate PnL in currency and pips."""
        pip_value = self._get_pip_value(instrument)

        if direction == TradeDirection.LONG:
            price_diff = exit_price - entry_price
        else:
            price_diff = entry_price - exit_price

        pnl_pips = price_diff / pip_value
        # Approximate PnL (simplified - assumes 1 pip = $10 for standard lot on majors)
        pnl = pnl_pips * units * pip_value * 10000

        return pnl, pnl_pips

    def _get_position_size(
        self,
        equity: float,
        confidence: int,
        entry_price: float,
        stop_loss: float,
        instrument: str
    ) -> tuple[int, str, float]:
        """
        Calculate position size based on confidence tier.

        Returns: (units, risk_tier, risk_percent)
        """
        # Risk tiers from position_sizer
        if confidence >= 90:
            risk_percent = 0.03
            tier = "TIER 3"
        elif confidence >= 70:
            risk_percent = 0.02
            tier = "TIER 2"
        elif confidence >= 50:
            risk_percent = 0.01
            tier = "TIER 1"
        else:
            return 0, "NO TRADE", 0.0

        risk_amount = equity * risk_percent
        pip_value = self._get_pip_value(instrument)
        pip_distance = abs(entry_price - stop_loss) / pip_value

        if pip_distance <= 0:
            return 0, "NO TRADE", 0.0

        # Calculate units (simplified)
        # Value per pip per unit = pip_value * lot_size
        # For micro lots (0.01), 1 pip ~ $0.10 on EUR/USD
        value_per_pip = pip_value * 100000 * 0.01  # Micro lot
        units = int(risk_amount / (pip_distance * value_per_pip))

        # Minimum 1 unit, maximum reasonable size
        units = max(1, min(units, 100000))

        return units, tier, risk_percent

    def _check_sl_tp(
        self,
        trade: SimulatedTrade,
        candle: dict
    ) -> Optional[tuple[float, str]]:
        """
        Check if stop loss or take profit is hit.

        Returns: (exit_price, reason) or None
        """
        high = candle["high"]
        low = candle["low"]

        if trade.direction == TradeDirection.LONG:
            # Check SL first (worst case)
            if low <= trade.stop_loss:
                return trade.stop_loss, "SL"
            # Check TP
            if high >= trade.take_profit:
                return trade.take_profit, "TP"
        else:  # SHORT
            # Check SL first
            if high >= trade.stop_loss:
                return trade.stop_loss, "SL"
            # Check TP
            if low <= trade.take_profit:
                return trade.take_profit, "TP"

        return None

    def _generate_signal(
        self,
        candles: list[dict],
        instrument: str,
        config: BacktestConfig
    ) -> Optional[dict]:
        """
        Generate trading signal using analysis pipeline.

        Returns signal dict or None if no trade.
        """
        # Technical analysis
        technical_result = self.technical.analyze(candles, instrument)

        # Sentiment analysis
        sentiment_result = self.sentiment.analyze(candles, technical_result)

        # Adversarial analysis (optional)
        adversarial_result = None
        if config.use_adversarial:
            # Determine direction based on technical trend
            direction = "LONG" if technical_result.trend == "BULLISH" else "SHORT"
            current_price = candles[-1]["close"]

            adversarial_result = self.adversarial.analyze(
                technical=technical_result,
                sentiment=sentiment_result,
                instrument=instrument,
                direction=direction,
                current_price=current_price
            )

        # Calculate confidence
        confidence_result = self.confidence.calculate(
            technical=technical_result,
            sentiment=sentiment_result,
            adversarial=adversarial_result
        )

        # Check if we should trade
        if not confidence_result.can_trade:
            return None

        if confidence_result.confidence_score < config.min_confidence:
            return None

        # Determine direction from verdict
        if adversarial_result:
            verdict = adversarial_result.verdict
            if verdict in ["STRONG_BUY", "BUY"]:
                direction = TradeDirection.LONG
            elif verdict in ["STRONG_SELL", "SELL"]:
                direction = TradeDirection.SHORT
            else:
                return None  # NEUTRAL - no trade
        else:
            # Use technical trend
            if technical_result.trend == "BULLISH":
                direction = TradeDirection.LONG
            elif technical_result.trend == "BEARISH":
                direction = TradeDirection.SHORT
            else:
                return None  # RANGING - no trade

        # Calculate SL/TP using ATR
        current_price = candles[-1]["close"]
        atr = technical_result.atr

        if direction == TradeDirection.LONG:
            stop_loss = current_price - (atr * config.atr_sl_multiplier)
            take_profit = current_price + (atr * config.atr_tp_multiplier)
        else:
            stop_loss = current_price + (atr * config.atr_sl_multiplier)
            take_profit = current_price - (atr * config.atr_tp_multiplier)

        return {
            "direction": direction,
            "entry_price": current_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence_result.confidence_score,
            "risk_tier": confidence_result.risk_tier,
            "technical_score": technical_result.technical_score,
            "sentiment_label": sentiment_result.sentiment_label,
            "verdict": adversarial_result.verdict if adversarial_result else None,
        }

    def run(
        self,
        candles: list[dict],
        config: BacktestConfig,
        progress_callback: Optional[Callable] = None
    ) -> BacktestResult:
        """
        Run backtest on historical candles.

        Args:
            candles: List of OHLCV candles
            config: Backtest configuration
            progress_callback: Optional callback(current, total, message)

        Returns:
            BacktestResult with all trades and equity curve
        """
        import time
        start_time = time.time()

        state = BacktestState(
            equity=config.initial_capital,
            cash=config.initial_capital
        )

        total_bars = len(candles)
        lookback = config.lookback_bars

        if total_bars < lookback + 10:
            raise ValueError(f"Not enough data: {total_bars} bars, need at least {lookback + 10}")

        # Walk-forward simulation
        for i in range(lookback, total_bars):
            current_candle = candles[i]
            analysis_candles = candles[i - lookback:i + 1]

            # Update progress
            if progress_callback:
                progress_callback(
                    i - lookback + 1,
                    total_bars - lookback,
                    f"Processing bar {i + 1}/{total_bars}"
                )

            # Check existing position for SL/TP
            if state.open_position:
                sl_tp_result = self._check_sl_tp(state.open_position, current_candle)

                if sl_tp_result:
                    exit_price, exit_reason = sl_tp_result
                    trade = state.open_position

                    # Calculate PnL
                    pnl, pnl_pips = self._calculate_pnl(
                        trade.entry_price,
                        exit_price,
                        trade.direction,
                        trade.units,
                        config.instrument
                    )

                    # Close trade
                    trade.exit_time = current_candle["time"]
                    trade.exit_price = exit_price
                    trade.exit_reason = exit_reason
                    trade.pnl = pnl
                    trade.pnl_pips = pnl_pips

                    # Update state
                    state.cash += pnl
                    state.equity = state.cash
                    state.closed_trades.append(trade)
                    state.open_position = None

            # Generate signal if no open position
            if state.open_position is None:
                signal = self._generate_signal(analysis_candles, config.instrument, config)

                if signal:
                    # Calculate position size
                    units, tier, risk_pct = self._get_position_size(
                        state.equity,
                        signal["confidence"],
                        signal["entry_price"],
                        signal["stop_loss"],
                        config.instrument
                    )

                    if units > 0:
                        # Open new position
                        trade = SimulatedTrade(
                            entry_time=current_candle["time"],
                            entry_price=signal["entry_price"],
                            direction=signal["direction"],
                            stop_loss=signal["stop_loss"],
                            take_profit=signal["take_profit"],
                            units=units,
                            confidence=signal["confidence"],
                            risk_tier=tier
                        )
                        state.open_position = trade

            # Record equity
            current_equity = state.cash
            if state.open_position:
                # Mark-to-market for open position
                unrealized_pnl, _ = self._calculate_pnl(
                    state.open_position.entry_price,
                    current_candle["close"],
                    state.open_position.direction,
                    state.open_position.units,
                    config.instrument
                )
                current_equity += unrealized_pnl

            state.equity_curve.append({
                "time": current_candle["time"],
                "equity": current_equity,
                "cash": state.cash,
                "has_position": state.open_position is not None
            })

        # Close any remaining position at last price
        if state.open_position:
            last_candle = candles[-1]
            trade = state.open_position

            pnl, pnl_pips = self._calculate_pnl(
                trade.entry_price,
                last_candle["close"],
                trade.direction,
                trade.units,
                config.instrument
            )

            trade.exit_time = last_candle["time"]
            trade.exit_price = last_candle["close"]
            trade.exit_reason = "END"
            trade.pnl = pnl
            trade.pnl_pips = pnl_pips

            state.cash += pnl
            state.closed_trades.append(trade)

        run_time = time.time() - start_time

        return BacktestResult(
            config=config,
            trades=state.closed_trades,
            equity_curve=state.equity_curve,
            initial_equity=config.initial_capital,
            final_equity=state.cash,
            total_bars=total_bars,
            bars_analyzed=total_bars - lookback,
            run_time_seconds=run_time
        )
