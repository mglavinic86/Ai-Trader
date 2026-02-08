"""
SMC+ISI Backtesting Engine

Walk-forward simulation using the production SMC pipeline:
1. Multi-timeframe data (H4/H1/M5)
2. SMC HTF Analysis (structure + liquidity)
3. SMC LTF Analysis (sweep + CHoCH/BOS + FVG/OB)
4. Setup Grading (A+/A/B/NO_TRADE)
5. Market Regime filter
6. Confidence scoring with ISI modifiers
7. SL/TP from SMC zones
8. R:R check

Usage:
    from src.backtesting.engine import SMCBacktestEngine, BacktestConfig
    from src.backtesting.data_loader import DataLoader

    loader = DataLoader()
    h4 = loader.load_simple("EUR_USD", "H4", start, end)
    h1 = loader.load_simple("EUR_USD", "H1", start, end)
    m5 = loader.load_simple("EUR_USD", "M5", start, end)

    engine = SMCBacktestEngine()
    result = engine.run(h4.candles, h1.candles, m5.candles, config)
"""

import time as _time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Dict, List
from enum import Enum

from src.smc import SMCAnalyzer, SMCAnalysis
from src.market.indicators import TechnicalAnalyzer
from src.utils.instrument_profiles import get_profile
from src.utils.logger import logger


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
    min_confidence: int = 68          # Min SMC grade confidence (B=68)
    min_grade: str = "B"              # Minimum setup grade
    target_rr: float = 2.5            # Minimum R:R ratio
    max_sl_pips: float = 30.0         # Max stop loss in pips
    max_positions: int = 1            # Max concurrent positions
    spread_pips: float = 1.2          # Average spread
    slippage_pips: float = 0.2        # Slippage per side
    commission_per_lot: float = 7.0   # Round-turn commission
    risk_percent: float = 0.01        # Risk per trade (1%)
    check_regime: bool = True         # Enable market regime filter
    check_session: bool = True        # Enable session filter
    session_hours: Optional[list] = None  # UTC hours for entries [(7,17)]
    signal_interval: int = 1          # Check for signals every N M5 bars
    htf_lookback: int = 100           # H4/H1 bars for HTF analysis
    ltf_lookback: int = 100           # M5 bars for LTF analysis
    # Partial TP + Trailing Stop
    partial_tp_enabled: bool = False    # Disabled - cuts winners short
    partial_tp_rr: float = 1.5         # R:R level for partial close
    trailing_stop_enabled: bool = False # Disabled - tied to partial TP
    trailing_atr_multiplier: float = 1.0  # ATR multiplier for trailing distance
    # Entry improvement: limit order at FVG/OB retest
    limit_entry_enabled: bool = True    # Wait for FVG/OB retest instead of market entry
    limit_entry_max_bars: int = 12      # Cancel pending order if not filled in N bars (12 = 1 hour on M5)
    limit_entry_midpoint: bool = True   # Enter at zone midpoint (deeper) vs edge - proven best in Session 32
    # Breakeven SL at 1.0R
    breakeven_sl_enabled: bool = True   # Move SL to entry when price reaches 1.0R profit
    breakeven_sl_trigger_rr: float = 1.0  # R:R level to trigger breakeven move
    # ISI (Institutional Sequence Intelligence) toggles
    isi_sequence_tracker: bool = False  # Enable sequence phase tracking
    isi_cross_asset: bool = False       # Enable cross-asset divergence
    isi_calibrator: bool = False        # Enable Platt Scaling calibration


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
    setup_grade: str

    entry_price_effective: Optional[float] = None
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    exit_price_effective: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: float = 0.0
    pnl_pips: float = 0.0
    commission: float = 0.0
    risk_reward_actual: float = 0.0

    # SMC metadata
    htf_bias: str = ""
    sweep_type: str = ""
    has_choch: bool = False
    has_bos: bool = False
    has_displacement: bool = False
    fvg_count: int = 0
    ob_count: int = 0

    # Partial TP + Trailing Stop metadata
    partial_tp_price: Optional[float] = None
    partial_tp_hit: bool = False
    partial_pnl: float = 0.0
    trailing_enabled: bool = False
    current_sl: Optional[float] = None
    highest_favorable: Optional[float] = None
    atr_at_entry: float = 0.0
    original_units: int = 0  # Units before partial close

    # ISI metadata
    raw_confidence: Optional[int] = None
    calibrated_confidence: Optional[int] = None
    sequence_phase: Optional[int] = None
    sequence_phase_name: Optional[str] = None
    sequence_modifier: int = 0
    divergence_modifier: int = 0

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
            "entry_price_effective": self.entry_price_effective,
            "direction": self.direction.value,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "units": self.units,
            "confidence": self.confidence,
            "setup_grade": self.setup_grade,
            "exit_time": self.exit_time,
            "exit_price": self.exit_price,
            "exit_price_effective": self.exit_price_effective,
            "exit_reason": self.exit_reason,
            "pnl": self.pnl,
            "pnl_pips": self.pnl_pips,
            "commission": self.commission,
            "risk_reward_actual": self.risk_reward_actual,
            "htf_bias": self.htf_bias,
            "sweep_type": self.sweep_type,
            "has_choch": self.has_choch,
            "has_bos": self.has_bos,
            "has_displacement": self.has_displacement,
            "fvg_count": self.fvg_count,
            "ob_count": self.ob_count,
            "partial_tp_hit": self.partial_tp_hit,
            "partial_pnl": self.partial_pnl,
            "trailing_enabled": self.trailing_enabled,
            "atr_at_entry": self.atr_at_entry,
            "raw_confidence": self.raw_confidence,
            "calibrated_confidence": self.calibrated_confidence,
            "sequence_phase": self.sequence_phase,
            "sequence_phase_name": self.sequence_phase_name,
            "sequence_modifier": self.sequence_modifier,
            "divergence_modifier": self.divergence_modifier,
        }


@dataclass
class PendingOrder:
    """A limit order waiting for FVG/OB retest fill."""
    signal: dict            # Original signal data
    entry_price: float      # Limit entry price (at FVG/OB zone)
    created_bar: int        # Bar index when created
    max_bars: int           # Expiry in bars
    entry_zone: tuple       # (low, high) of the entry zone


@dataclass
class BacktestState:
    """Current state of the backtest simulation."""
    equity: float
    cash: float
    open_position: Optional[SimulatedTrade] = None
    pending_order: Optional[PendingOrder] = None
    closed_trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)


@dataclass
class BacktestResult:
    """Complete backtest result."""
    config: BacktestConfig
    trades: list
    equity_curve: list
    initial_equity: float
    final_equity: float
    total_bars: int
    bars_analyzed: int
    signals_generated: int
    signals_skipped: int
    run_time_seconds: float
    skip_reasons: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "config": {
                "instrument": self.config.instrument,
                "timeframe": self.config.timeframe,
                "start_date": self.config.start_date.isoformat(),
                "end_date": self.config.end_date.isoformat(),
                "initial_capital": self.config.initial_capital,
                "min_confidence": self.config.min_confidence,
                "min_grade": self.config.min_grade,
                "target_rr": self.config.target_rr,
                "risk_percent": self.config.risk_percent,
                "spread_pips": self.config.spread_pips,
                "check_regime": self.config.check_regime,
                "check_session": self.config.check_session,
                "partial_tp_enabled": self.config.partial_tp_enabled,
                "trailing_stop_enabled": self.config.trailing_stop_enabled,
                "isi_sequence_tracker": self.config.isi_sequence_tracker,
                "isi_cross_asset": self.config.isi_cross_asset,
                "isi_calibrator": self.config.isi_calibrator,
            },
            "trades": [t.to_dict() for t in self.trades],
            "equity_curve": self.equity_curve,
            "initial_equity": self.initial_equity,
            "final_equity": self.final_equity,
            "total_bars": self.total_bars,
            "bars_analyzed": self.bars_analyzed,
            "signals_generated": self.signals_generated,
            "signals_skipped": self.signals_skipped,
            "run_time_seconds": self.run_time_seconds,
            "skip_reasons": self.skip_reasons,
        }


# Grade hierarchy for comparison
GRADE_ORDER = {"A+": 4, "A": 3, "B": 2, "NO_TRADE": 0}

# Known correlations (mirrored from cross_asset_detector.py)
_CORRELATION_PAIRS = {
    ("EUR_USD", "GBP_USD"): {"expected": 0.85},
    ("EUR_USD", "XAU_USD"): {"expected": 0.40},
    ("GBP_USD", "XAU_USD"): {"expected": 0.30},
}
_CORR_WINDOW = 30
_DIVERGENCE_THRESHOLD_SIGMA = 1.5
_CORR_STD = 0.15


class BacktestCrossAssetAdapter:
    """
    Lightweight cross-asset divergence for backtesting.

    Replaces the production CrossAssetDetector which depends on MT5 live data.
    Uses pre-loaded M5 candles and time-aligns them to prevent look-ahead bias.
    """

    def __init__(self, all_m5_data: Dict[str, list]):
        """
        Args:
            all_m5_data: {instrument: [candle_dicts]} - pre-loaded M5 candles
                         for all instruments available as cross-asset references.
        """
        self.all_m5_data = all_m5_data

    def get_confidence_modifier(
        self, instrument: str, direction: str, current_m5_index: int,
        m5_candles: list
    ) -> int:
        """
        Calculate cross-asset divergence modifier.

        Args:
            instrument: Target instrument (e.g. "EUR_USD")
            direction: "LONG" or "SHORT"
            current_m5_index: Current bar index in the target's M5 array
            m5_candles: Target instrument's full M5 candle array

        Returns:
            Confidence modifier: -10 to +15
        """
        total_modifier = 0
        current_ts = m5_candles[current_m5_index]["timestamp"]

        for (pair1, pair2), config in _CORRELATION_PAIRS.items():
            if instrument not in (pair1, pair2):
                continue

            other = pair2 if instrument == pair1 else pair1
            if other not in self.all_m5_data:
                continue

            # Get target candles up to current bar (no look-ahead)
            target_slice = m5_candles[max(0, current_m5_index - _CORR_WINDOW):current_m5_index + 1]

            # Get other instrument candles aligned by timestamp
            other_all = self.all_m5_data[other]
            other_slice = [c for c in other_all if c["timestamp"] <= current_ts]
            other_slice = other_slice[-_CORR_WINDOW:]

            if len(target_slice) < 10 or len(other_slice) < 10:
                continue

            # Calculate rolling correlation on returns
            current_corr = self._rolling_correlation(target_slice, other_slice)
            if current_corr is None:
                continue

            expected_corr = config["expected"]
            diff = abs(current_corr - expected_corr)
            divergence_sigma = diff / _CORR_STD if _CORR_STD > 0 else 0

            if divergence_sigma < _DIVERGENCE_THRESHOLD_SIGMA:
                continue

            # Interpret divergence (same logic as production)
            modifier = self._interpret(
                expected_corr, current_corr, direction, divergence_sigma
            )
            total_modifier += modifier

        return max(-10, min(15, total_modifier))

    @staticmethod
    def _rolling_correlation(candles1: list, candles2: list) -> Optional[float]:
        """Pearson correlation on close-price returns."""
        import math as _math

        n = min(len(candles1), len(candles2))
        if n < 10:
            return None

        closes1 = [c["close"] for c in candles1[-n:]]
        closes2 = [c["close"] for c in candles2[-n:]]

        returns1 = [(closes1[i] - closes1[i-1]) / closes1[i-1]
                     for i in range(1, len(closes1)) if closes1[i-1] != 0]
        returns2 = [(closes2[i] - closes2[i-1]) / closes2[i-1]
                     for i in range(1, len(closes2)) if closes2[i-1] != 0]

        n_r = min(len(returns1), len(returns2))
        if n_r < 5:
            return None

        returns1 = returns1[-n_r:]
        returns2 = returns2[-n_r:]

        mean1 = sum(returns1) / n_r
        mean2 = sum(returns2) / n_r

        cov = sum((r1 - mean1) * (r2 - mean2) for r1, r2 in zip(returns1, returns2)) / n_r
        std1 = _math.sqrt(sum((r - mean1) ** 2 for r in returns1) / n_r)
        std2 = _math.sqrt(sum((r - mean2) ** 2 for r in returns2) / n_r)

        if std1 == 0 or std2 == 0:
            return None

        return cov / (std1 * std2)

    @staticmethod
    def _interpret(
        expected_corr: float, current_corr: float,
        direction: str, divergence_sigma: float
    ) -> int:
        """Interpret divergence into a confidence modifier."""
        corr_drop = expected_corr - current_corr

        if corr_drop > 0:
            # Correlation dropped = divergence favors specific instrument flow
            return min(15, int(divergence_sigma * 5))
        else:
            if abs(current_corr) > abs(expected_corr):
                # Stronger-than-expected correlation = general move, no edge
                return 0
            else:
                # Unusual reversal
                return min(10, int(divergence_sigma * 3))



class SMCBacktestEngine:
    """
    SMC+ISI backtesting engine.

    Uses the same SMC pipeline as the production auto_scanner
    to generate signals and simulates trade execution.
    """

    def __init__(self):
        self.smc_analyzer = SMCAnalyzer()
        self.technical_analyzer = TechnicalAnalyzer()

    def _get_pip_value(self, instrument: str) -> float:
        if "XAU" in instrument:
            return 0.1
        if "BTC" in instrument or "ETH" in instrument:
            return 1.0
        if "JPY" in instrument:
            return 0.01
        return 0.0001

    def _get_contract_size(self, instrument: str) -> float:
        if "BTC" in instrument or "ETH" in instrument:
            return 1.0
        if "XAU" in instrument:
            return 100.0
        return 100000.0

    def _pip_to_price(self, pips: float, instrument: str) -> float:
        return pips * self._get_pip_value(instrument)

    def _apply_costs(
        self, price: float, direction: TradeDirection,
        instrument: str, spread_pips: float,
        slippage_pips: float, side: str
    ) -> float:
        """Apply spread and slippage to a price."""
        half_spread = self._pip_to_price(spread_pips / 2, instrument)
        slip = self._pip_to_price(slippage_pips, instrument)

        if direction == TradeDirection.LONG:
            if side == "entry":
                return price + half_spread + slip
            return price - half_spread - slip
        else:
            if side == "entry":
                return price - half_spread - slip
            return price + half_spread + slip

    def _is_trade_time(self, candle_time: str, config: BacktestConfig) -> bool:
        """Check if candle time is within allowed session."""
        if not config.check_session:
            return True

        try:
            dt = datetime.fromisoformat(candle_time.replace("Z", "+00:00"))
        except Exception:
            return True

        # Skip weekends
        if dt.weekday() >= 5:
            return False

        if not config.session_hours:
            return True

        hour = dt.hour
        for start, end in config.session_hours:
            if start <= end:
                if start <= hour < end:
                    return True
            else:
                if hour >= start or hour < end:
                    return True

        return False

    def _check_market_regime(self, technical, config: BacktestConfig) -> tuple:
        """Check market regime filter."""
        if not config.check_regime:
            return True, ""

        regime = getattr(technical, 'market_regime', 'UNKNOWN')

        if regime == "LOW_VOLATILITY":
            return False, "LOW_VOLATILITY regime"
        if regime == "VOLATILE":
            return False, "VOLATILE regime"

        return True, ""

    def _get_htf_candles_at(self, all_htf: list, m5_timestamp: int, lookback: int) -> list:
        """Get HTF candles that existed at the time of a given M5 bar."""
        result = [c for c in all_htf if c["timestamp"] <= m5_timestamp]
        return result[-lookback:] if len(result) > lookback else result

    def _calculate_pnl(
        self, entry_price: float, exit_price: float,
        direction: TradeDirection, units: int, instrument: str
    ) -> tuple:
        pip_value = self._get_pip_value(instrument)
        if direction == TradeDirection.LONG:
            price_diff = exit_price - entry_price
        else:
            price_diff = entry_price - exit_price
        pnl_pips = price_diff / pip_value
        pnl = price_diff * units
        return pnl, pnl_pips

    def _get_position_size(
        self, equity: float, config: BacktestConfig,
        entry_price: float, stop_loss: float, instrument: str
    ) -> int:
        """Calculate position size based on fixed risk percent."""
        risk_amount = equity * config.risk_percent
        pip_value = self._get_pip_value(instrument)
        pip_distance = abs(entry_price - stop_loss) / pip_value

        if pip_distance <= 0:
            return 0

        units = int(risk_amount / (pip_distance * pip_value))
        return max(1, units)

    def _check_sl_tp(self, trade: SimulatedTrade, candle: dict, config: Optional[BacktestConfig] = None) -> Optional[tuple]:
        """
        Check if stop loss, breakeven, partial TP, or full TP is hit.

        Handles:
        1. SL check (uses current_sl if breakeven/trailing is active)
        2. Breakeven SL move at 1.0R (no close, just moves SL)
        3. Partial TP (close 50% at partial_tp_price, move SL to breakeven)
        4. Full TP check
        5. Trailing stop update
        """
        high = candle["high"]
        low = candle["low"]
        effective_sl = trade.current_sl if trade.current_sl is not None else trade.stop_loss
        entry_eff = trade.entry_price_effective or trade.entry_price

        if trade.direction == TradeDirection.LONG:
            # Check SL first (highest priority)
            if low <= effective_sl:
                reason = "SL"
                if trade.partial_tp_hit:
                    reason = "TRAILING_SL"
                elif trade.current_sl is not None and trade.current_sl >= entry_eff:
                    reason = "BREAKEVEN"
                return effective_sl, reason

            # Breakeven SL at 1.0R (if enabled, before partial TP)
            if (config and config.breakeven_sl_enabled
                    and trade.current_sl is None
                    and not trade.partial_tp_hit):
                sl_dist = abs(entry_eff - trade.stop_loss)
                be_trigger = entry_eff + sl_dist * config.breakeven_sl_trigger_rr
                if high >= be_trigger:
                    trade.current_sl = entry_eff  # Move SL to breakeven

            # Check partial TP (if enabled and not yet hit)
            if trade.partial_tp_price and not trade.partial_tp_hit:
                if high >= trade.partial_tp_price:
                    pip_value = self._get_pip_value(config.instrument) if config else 0.0001
                    partial_units = trade.original_units // 2
                    price_diff = trade.partial_tp_price - entry_eff
                    trade.partial_pnl = price_diff * partial_units
                    trade.partial_tp_hit = True
                    trade.units = trade.original_units - partial_units
                    trade.current_sl = entry_eff  # Move SL to breakeven
                    trade.highest_favorable = trade.partial_tp_price
                    trade.trailing_enabled = True
                    return None

            # Check full TP
            if high >= trade.take_profit:
                return trade.take_profit, "TP"

            # Update trailing stop (after partial TP hit)
            if trade.trailing_enabled and trade.atr_at_entry > 0:
                if trade.highest_favorable is None or high > trade.highest_favorable:
                    trade.highest_favorable = high
                trailing_dist = trade.atr_at_entry
                new_sl = trade.highest_favorable - trailing_dist
                if trade.current_sl is not None and new_sl > trade.current_sl:
                    trade.current_sl = new_sl
        else:
            # SHORT direction
            if high >= effective_sl:
                reason = "SL"
                if trade.partial_tp_hit:
                    reason = "TRAILING_SL"
                elif trade.current_sl is not None and trade.current_sl <= entry_eff:
                    reason = "BREAKEVEN"
                return effective_sl, reason

            # Breakeven SL at 1.0R
            if (config and config.breakeven_sl_enabled
                    and trade.current_sl is None
                    and not trade.partial_tp_hit):
                sl_dist = abs(trade.stop_loss - entry_eff)
                be_trigger = entry_eff - sl_dist * config.breakeven_sl_trigger_rr
                if low <= be_trigger:
                    trade.current_sl = entry_eff  # Move SL to breakeven

            # Check partial TP
            if trade.partial_tp_price and not trade.partial_tp_hit:
                if low <= trade.partial_tp_price:
                    pip_value = self._get_pip_value(config.instrument) if config else 0.0001
                    partial_units = trade.original_units // 2
                    price_diff = entry_eff - trade.partial_tp_price
                    trade.partial_pnl = price_diff * partial_units
                    trade.partial_tp_hit = True
                    trade.units = trade.original_units - partial_units
                    trade.current_sl = entry_eff
                    trade.highest_favorable = trade.partial_tp_price
                    trade.trailing_enabled = True
                    return None

            # Check full TP
            if low <= trade.take_profit:
                return trade.take_profit, "TP"

            # Update trailing stop
            if trade.trailing_enabled and trade.atr_at_entry > 0:
                if trade.highest_favorable is None or low < trade.highest_favorable:
                    trade.highest_favorable = low
                trailing_dist = trade.atr_at_entry
                new_sl = trade.highest_favorable + trailing_dist
                if trade.current_sl is not None and new_sl < trade.current_sl:
                    trade.current_sl = new_sl

        return None

    def _create_trade(
        self, candle: dict, signal: dict, entry_eff: float,
        equity: float, config: BacktestConfig
    ) -> Optional[SimulatedTrade]:
        """Create a SimulatedTrade from a signal. Returns None if position size is 0."""
        units = self._get_position_size(
            equity, config, entry_eff, signal["stop_loss"], config.instrument
        )
        if units <= 0:
            return None

        partial_tp_price = None
        atr_at_entry = 0.0
        if config.partial_tp_enabled:
            sl_dist = abs(entry_eff - signal["stop_loss"])
            if signal["direction"] == TradeDirection.LONG:
                partial_tp_price = entry_eff + sl_dist * config.partial_tp_rr
            else:
                partial_tp_price = entry_eff - sl_dist * config.partial_tp_rr
        if config.trailing_stop_enabled:
            atr_val = signal.get("atr", 0.0)
            atr_at_entry = atr_val * config.trailing_atr_multiplier if atr_val else 0.0

        return SimulatedTrade(
            entry_time=candle["time"],
            entry_price=signal["entry_price"],
            entry_price_effective=entry_eff,
            direction=signal["direction"],
            stop_loss=signal["stop_loss"],
            take_profit=signal["take_profit"],
            units=units,
            confidence=signal["confidence"],
            setup_grade=signal["setup_grade"],
            htf_bias=signal["htf_bias"],
            sweep_type=signal["sweep_type"],
            has_choch=signal["has_choch"],
            has_bos=signal["has_bos"],
            has_displacement=signal["has_displacement"],
            fvg_count=signal["fvg_count"],
            ob_count=signal["ob_count"],
            partial_tp_price=partial_tp_price,
            atr_at_entry=atr_at_entry,
            original_units=units,
            raw_confidence=signal.get("raw_confidence"),
            calibrated_confidence=signal.get("calibrated_confidence"),
            sequence_phase=signal.get("sequence_phase"),
            sequence_phase_name=signal.get("sequence_phase_name"),
            sequence_modifier=signal.get("sequence_modifier", 0),
            divergence_modifier=signal.get("divergence_modifier", 0),
        )

    def _generate_smc_signal(
        self, h4_window: list, h1_window: list, m5_window: list,
        config: BacktestConfig,
        sequence_tracker=None, cross_asset_adapter=None, calibrator=None,
        current_m5_index: int = 0, m5_candles: list = None, technical=None,
    ) -> Optional[dict]:
        """
        Generate trading signal using SMC pipeline.

        Mirrors the auto_scanner logic:
        1. HTF analysis (H4/H1) -> bias + liquidity
        2. LTF analysis (M5) -> sweep + CHoCH/BOS + grade
        3. Hard gates check
        4. ISI: Sequence tracking (always updates, even on skipped bars)
        5. Confidence from grade + ISI modifiers
        6. SL/TP from SMC zones
        7. R:R check
        """
        instrument = config.instrument

        # Need minimum data
        if len(h4_window) < 20 or len(h1_window) < 20 or len(m5_window) < 30:
            return None

        # Step 1: HTF Analysis
        htf_result = self.smc_analyzer.analyze_htf(h4_window, h1_window, instrument)

        # Step 2: LTF Analysis
        smc_analysis = self.smc_analyzer.analyze_ltf(m5_window, htf_result, instrument)

        # Step 4.5: ISI Sequence Tracking (before hard gates - always update)
        seq_modifier = 0
        seq_phase = None
        seq_phase_name = None
        if sequence_tracker and technical:
            seq_state = sequence_tracker.update(instrument, smc_analysis, technical)
            seq_modifier = seq_state.confidence_modifier()
            seq_phase = seq_state.current_phase
            seq_phase_name = seq_state.phase_name

        # HARD GATE: HTF must not be neutral
        if htf_result["htf_bias"] == "NEUTRAL":
            return {"skip": "HTF_NEUTRAL"}

        # HARD GATE: Must have sweep
        if not smc_analysis.sweep_detected:
            return {"skip": "NO_SWEEP"}

        # HARD GATE: Must have CHoCH or BOS
        if not smc_analysis.ltf_choch and not smc_analysis.ltf_bos:
            return {"skip": "NO_CHOCH_BOS"}

        # HARD GATE: Must have direction
        if not smc_analysis.direction:
            return {"skip": "NO_DIRECTION"}

        # HARD GATE: Setup grade
        if smc_analysis.setup_grade == "NO_TRADE":
            return {"skip": "GRADE_NO_TRADE"}

        # Check minimum grade
        min_grade_val = GRADE_ORDER.get(config.min_grade, 2)
        actual_grade_val = GRADE_ORDER.get(smc_analysis.setup_grade, 0)
        if actual_grade_val < min_grade_val:
            return {"skip": f"GRADE_{smc_analysis.setup_grade}_BELOW_{config.min_grade}"}

        direction = smc_analysis.direction

        # Step 6.5: ISI Cross-Asset Divergence
        div_modifier = 0
        if cross_asset_adapter and m5_candles:
            div_modifier = cross_asset_adapter.get_confidence_modifier(
                instrument, direction, current_m5_index, m5_candles
            )

        # Step 7: Confidence = SMC grade + ISI modifiers
        smc_confidence = smc_analysis.confidence
        raw_confidence = max(0, min(100, smc_confidence + seq_modifier + div_modifier))

        # ISI: Bayesian calibration (passthrough if unfitted)
        calibrated_confidence = raw_confidence
        if calibrator:
            calibrated_confidence = calibrator.calibrate(raw_confidence)

        confidence = calibrated_confidence

        if confidence < config.min_confidence:
            return {"skip": f"CONFIDENCE_{confidence}_BELOW_{config.min_confidence}"}

        # SL/TP from SMC
        if not smc_analysis.stop_loss or not smc_analysis.take_profit:
            return {"skip": "NO_SL_TP"}

        entry_price = m5_window[-1]["close"]
        sl = smc_analysis.stop_loss
        tp = smc_analysis.take_profit

        # Validate SL/TP makes sense
        if direction == "LONG":
            if sl >= entry_price or tp <= entry_price:
                return {"skip": "INVALID_SL_TP"}
        else:
            if sl <= entry_price or tp >= entry_price:
                return {"skip": "INVALID_SL_TP"}

        # R:R check
        risk = abs(entry_price - sl)
        reward = abs(tp - entry_price)
        risk_reward = reward / risk if risk > 0 else 0

        if risk_reward < config.target_rr - 0.01:
            return {"skip": f"RR_{risk_reward:.1f}_BELOW_{config.target_rr}"}

        # SL distance check
        pip_value = self._get_pip_value(instrument)
        sl_pips = abs(entry_price - sl) / pip_value
        if sl_pips > config.max_sl_pips:
            return {"skip": f"SL_{sl_pips:.1f}_PIPS_EXCEEDS_{config.max_sl_pips}"}

        # Get ATR for trailing stop
        atr_value = 0.0
        if technical and hasattr(technical, 'atr'):
            atr_value = technical.atr or 0.0

        return {
            "direction": TradeDirection.LONG if direction == "LONG" else TradeDirection.SHORT,
            "entry_price": entry_price,
            "stop_loss": sl,
            "take_profit": tp,
            "confidence": confidence,
            "setup_grade": smc_analysis.setup_grade,
            "risk_reward": risk_reward,
            "htf_bias": htf_result["htf_bias"],
            "sweep_type": (smc_analysis.sweep_detected.sweep_direction
                           if smc_analysis.sweep_detected else ""),
            "has_choch": smc_analysis.ltf_choch is not None,
            "has_bos": smc_analysis.ltf_bos is not None,
            "has_displacement": smc_analysis.ltf_displacement is not None,
            "fvg_count": len(smc_analysis.fvgs),
            "ob_count": len(smc_analysis.order_blocks),
            "atr": atr_value,
            # Entry zone for limit orders
            "entry_zone": smc_analysis.entry_zone,
            # ISI metadata
            "raw_confidence": raw_confidence,
            "calibrated_confidence": calibrated_confidence,
            "sequence_phase": seq_phase,
            "sequence_phase_name": seq_phase_name,
            "sequence_modifier": seq_modifier,
            "divergence_modifier": div_modifier,
        }

    def run(
        self,
        h4_candles: list,
        h1_candles: list,
        m5_candles: list,
        config: BacktestConfig,
        progress_callback: Optional[Callable] = None,
        cross_asset_data: Optional[Dict[str, list]] = None,
    ) -> BacktestResult:
        """
        Run SMC backtest on multi-timeframe historical data.

        Args:
            h4_candles: H4 OHLCV candles with 'timestamp' field
            h1_candles: H1 OHLCV candles with 'timestamp' field
            m5_candles: M5 OHLCV candles with 'timestamp' field
            config: Backtest configuration
            progress_callback: Optional callback(current, total, message)
            cross_asset_data: Optional {instrument: [m5_candles]} for ISI cross-asset

        Returns:
            BacktestResult with all trades and equity curve
        """
        start_time = _time.time()

        state = BacktestState(
            equity=config.initial_capital,
            cash=config.initial_capital
        )

        total_bars = len(m5_candles)
        skip_reasons = {}
        signals_generated = 0
        signals_skipped = 0

        min_start_bar = max(config.ltf_lookback, 30)
        if total_bars < min_start_bar + 10:
            raise ValueError(
                f"Not enough M5 data: {total_bars} bars, "
                f"need at least {min_start_bar + 10}"
            )

        # Initialize ISI components (only if enabled in config)
        sequence_tracker = None
        cross_asset_adapter = None
        calibrator = None

        if config.isi_sequence_tracker or config.isi_calibrator:
            from src.utils.database import Database
            db = Database()

        if config.isi_sequence_tracker:
            from src.smc.sequence_tracker import SequenceTracker
            sequence_tracker = SequenceTracker(db)

        if config.isi_cross_asset and cross_asset_data:
            cross_asset_adapter = BacktestCrossAssetAdapter(cross_asset_data)

        if config.isi_calibrator:
            from src.analysis.confidence_calibrator import ConfidenceCalibrator
            calibrator = ConfidenceCalibrator(db)

        isi_label = ""
        if config.isi_sequence_tracker or config.isi_cross_asset or config.isi_calibrator:
            parts = []
            if config.isi_sequence_tracker:
                parts.append("Seq")
            if config.isi_cross_asset:
                parts.append("XA")
            if config.isi_calibrator:
                parts.append("Cal")
            isi_label = f" [ISI: {'+'.join(parts)}]"

        logger.info(
            f"SMC Backtest starting: {config.instrument}, "
            f"{total_bars} M5 bars, {len(h4_candles)} H4, {len(h1_candles)} H1"
            f"{isi_label}"
        )

        for i in range(min_start_bar, total_bars):
            current_candle = m5_candles[i]
            current_ts = current_candle["timestamp"]

            # Progress
            if progress_callback and i % 500 == 0:
                progress_callback(
                    i - min_start_bar + 1,
                    total_bars - min_start_bar,
                    f"Bar {i + 1}/{total_bars}"
                )

            # === Check existing position for SL/TP ===
            if state.open_position:
                sl_tp = self._check_sl_tp(state.open_position, current_candle, config)

                if sl_tp:
                    exit_price, exit_reason = sl_tp
                    trade = state.open_position

                    exit_eff = self._apply_costs(
                        exit_price, trade.direction,
                        config.instrument, config.spread_pips,
                        config.slippage_pips, "exit"
                    )

                    # PnL on remaining units
                    pnl_remaining, pnl_pips = self._calculate_pnl(
                        trade.entry_price_effective or trade.entry_price,
                        exit_eff, trade.direction,
                        trade.units, config.instrument
                    )

                    # Total PnL = partial close PnL + remaining PnL
                    total_pnl = trade.partial_pnl + pnl_remaining

                    contract_size = self._get_contract_size(config.instrument)
                    total_units = trade.original_units if trade.original_units > 0 else trade.units
                    lots = abs(total_units) / contract_size
                    commission = config.commission_per_lot * lots

                    trade.exit_time = current_candle["time"]
                    trade.exit_price = exit_price
                    trade.exit_price_effective = exit_eff
                    trade.exit_reason = exit_reason
                    trade.pnl = total_pnl - commission
                    trade.pnl_pips = pnl_pips
                    trade.commission = commission

                    # Actual R:R
                    entry_eff = trade.entry_price_effective or trade.entry_price
                    risk_dist = abs(entry_eff - trade.stop_loss)
                    reward_dist = abs(exit_eff - entry_eff)
                    trade.risk_reward_actual = (
                        reward_dist / risk_dist if risk_dist > 0 else 0
                    )

                    state.cash += trade.pnl
                    state.equity = state.cash
                    state.closed_trades.append(trade)
                    state.open_position = None

            # === Check pending limit order for fill ===
            if state.pending_order and state.open_position is None:
                po = state.pending_order
                bars_elapsed = i - po.created_bar
                c_high = current_candle["high"]
                c_low = current_candle["low"]

                # Expire pending order
                if bars_elapsed > po.max_bars:
                    skip_reasons["LIMIT_EXPIRED"] = skip_reasons.get("LIMIT_EXPIRED", 0) + 1
                    state.pending_order = None
                else:
                    # Check if price entered the entry zone
                    filled = False
                    if po.signal["direction"] == TradeDirection.LONG:
                        # LONG: price must dip DOWN into the zone
                        if c_low <= po.entry_price:
                            filled = True
                    else:
                        # SHORT: price must rise UP into the zone
                        if c_high >= po.entry_price:
                            filled = True

                    if filled:
                        signal = po.signal
                        entry_price = po.entry_price
                        state.pending_order = None

                        # Recalculate R:R with the better entry price
                        sl = signal["stop_loss"]
                        tp = signal["take_profit"]
                        risk = abs(entry_price - sl)
                        reward = abs(tp - entry_price)
                        new_rr = reward / risk if risk > 0 else 0

                        if new_rr >= config.target_rr - 0.01:
                            entry_eff = self._apply_costs(
                                entry_price, signal["direction"],
                                config.instrument, config.spread_pips,
                                config.slippage_pips, "entry"
                            )
                            trade = self._create_trade(
                                current_candle, signal, entry_eff,
                                state.equity, config
                            )
                            if trade:
                                state.open_position = trade

            # === Generate signal if no position and no pending (at signal_interval) ===
            if (state.open_position is None
                    and state.pending_order is None
                    and (i % config.signal_interval == 0)):
                # Session filter
                if not self._is_trade_time(current_candle["time"], config):
                    pass
                else:
                    # Get timeframe windows at current point in time
                    m5_window = m5_candles[max(0, i - config.ltf_lookback):i + 1]
                    h4_window = self._get_htf_candles_at(
                        h4_candles, current_ts, config.htf_lookback
                    )
                    h1_window = self._get_htf_candles_at(
                        h1_candles, current_ts, config.htf_lookback
                    )

                    # Market regime check (also used by sequence tracker)
                    technical = None
                    regime_ok = True
                    if (config.check_regime or sequence_tracker) and len(m5_window) >= 30:
                        technical = self.technical_analyzer.analyze(
                            m5_window, config.instrument
                        )
                        if config.check_regime:
                            regime_ok, regime_reason = self._check_market_regime(
                                technical, config
                            )
                            if not regime_ok:
                                reason_key = f"REGIME_{regime_reason}"
                                skip_reasons[reason_key] = (
                                    skip_reasons.get(reason_key, 0) + 1
                                )

                    if regime_ok:
                        signal = self._generate_smc_signal(
                            h4_window, h1_window, m5_window, config,
                            sequence_tracker=sequence_tracker,
                            cross_asset_adapter=cross_asset_adapter,
                            calibrator=calibrator,
                            current_m5_index=i,
                            m5_candles=m5_candles,
                            technical=technical,
                        )

                        if signal and "skip" in signal:
                            signals_skipped += 1
                            reason = signal["skip"]
                            skip_reasons[reason] = (
                                skip_reasons.get(reason, 0) + 1
                            )

                        elif signal:
                            signals_generated += 1

                            # Limit entry: create pending order at FVG/OB zone
                            if config.limit_entry_enabled and signal.get("entry_zone"):
                                zone_low, zone_high = signal["entry_zone"]
                                if config.limit_entry_midpoint:
                                    # Enter at zone midpoint (deeper = better price, fewer fills)
                                    limit_price = (zone_low + zone_high) / 2
                                elif signal["direction"] == TradeDirection.LONG:
                                    # Buy at top of bullish zone (first touch on retracement)
                                    limit_price = zone_high
                                else:
                                    # Sell at bottom of bearish zone
                                    limit_price = zone_low

                                state.pending_order = PendingOrder(
                                    signal=signal,
                                    entry_price=limit_price,
                                    created_bar=i,
                                    max_bars=config.limit_entry_max_bars,
                                    entry_zone=(zone_low, zone_high),
                                )
                            else:
                                # Market entry (no entry zone or limit disabled)
                                entry_eff = self._apply_costs(
                                    signal["entry_price"], signal["direction"],
                                    config.instrument, config.spread_pips,
                                    config.slippage_pips, "entry"
                                )
                                trade = self._create_trade(
                                    current_candle, signal, entry_eff,
                                    state.equity, config
                                )
                                if trade:
                                    state.open_position = trade

            # === Record equity ===
            current_equity = state.cash
            if state.open_position:
                mid = current_candle["close"]
                mark_price = self._apply_costs(
                    mid, state.open_position.direction,
                    config.instrument, config.spread_pips,
                    0.0, "exit"
                )
                unrealized, _ = self._calculate_pnl(
                    state.open_position.entry_price_effective
                    or state.open_position.entry_price,
                    mark_price, state.open_position.direction,
                    state.open_position.units, config.instrument
                )
                current_equity += unrealized

            # Record every 12th bar to keep equity curve manageable
            if i % 12 == 0 or state.open_position is not None:
                state.equity_curve.append({
                    "time": current_candle["time"],
                    "equity": current_equity,
                    "cash": state.cash,
                    "has_position": state.open_position is not None,
                })

        # Close remaining position at last price
        if state.open_position:
            last = m5_candles[-1]
            trade = state.open_position

            exit_eff = self._apply_costs(
                last["close"], trade.direction,
                config.instrument, config.spread_pips,
                config.slippage_pips, "exit"
            )
            pnl_remaining, pnl_pips = self._calculate_pnl(
                trade.entry_price_effective or trade.entry_price,
                exit_eff, trade.direction,
                trade.units, config.instrument
            )

            total_pnl = trade.partial_pnl + pnl_remaining

            contract_size = self._get_contract_size(config.instrument)
            total_units = trade.original_units if trade.original_units > 0 else trade.units
            lots = abs(total_units) / contract_size
            commission = config.commission_per_lot * lots

            trade.exit_time = last["time"]
            trade.exit_price = last["close"]
            trade.exit_price_effective = exit_eff
            trade.exit_reason = "END"
            trade.pnl = total_pnl - commission
            trade.pnl_pips = pnl_pips
            trade.commission = commission

            state.cash += trade.pnl
            state.closed_trades.append(trade)

        run_time = _time.time() - start_time

        logger.info(
            f"SMC Backtest complete: {len(state.closed_trades)} trades, "
            f"{signals_generated} signals, {signals_skipped} skipped, "
            f"{run_time:.1f}s"
        )

        return BacktestResult(
            config=config,
            trades=state.closed_trades,
            equity_curve=state.equity_curve,
            initial_equity=config.initial_capital,
            final_equity=state.cash,
            total_bars=total_bars,
            bars_analyzed=total_bars - min_start_bar,
            signals_generated=signals_generated,
            signals_skipped=signals_skipped,
            run_time_seconds=run_time,
            skip_reasons=skip_reasons,
        )


# Keep backward compatibility alias
BacktestEngine = SMCBacktestEngine
