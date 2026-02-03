"""
Post-Trade Analyzer - Deep analysis of closed trades.

Analyzes what ACTUALLY happened in the market during a trade,
not just generic categorization.

Usage:
    from src.analysis.post_trade_analyzer import PostTradeAnalyzer

    analyzer = PostTradeAnalyzer()
    result = analyzer.analyze_trade({
        "instrument": "EUR_USD",
        "direction": "LONG",
        "entry_price": 1.18712,
        "exit_price": 1.18138,
        "opened_at": "2026-01-30T20:22:46+00:00",
        "closed_at": "2026-02-02T15:30:47+00:00"
    })
    print(result.summary)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from enum import Enum
import pandas as pd
import numpy as np

from src.utils.logger import logger


class TradingSession(Enum):
    """Trading sessions."""
    ASIAN = "ASIAN"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    LONDON_NY_OVERLAP = "LONDON_NY_OVERLAP"
    OFF_HOURS = "OFF_HOURS"


class EntryQuality(Enum):
    """Quality of trade entry."""
    EXCELLENT = "EXCELLENT"  # Multiple confluences
    GOOD = "GOOD"           # Some confluence
    FAIR = "FAIR"           # Minimal confluence
    POOR = "POOR"           # Against structure/no confluence
    CHASING = "CHASING"     # Entered late, chased price


class TradeOutcome(Enum):
    """Trade outcome classification."""
    GOOD_TRADE_WIN = "GOOD_TRADE_WIN"       # Good setup, won
    GOOD_TRADE_LOSS = "GOOD_TRADE_LOSS"     # Good setup, lost (happens)
    BAD_TRADE_WIN = "BAD_TRADE_WIN"         # Bad setup, got lucky
    BAD_TRADE_LOSS = "BAD_TRADE_LOSS"       # Bad setup, lost (expected)
    UNLUCKY = "UNLUCKY"                      # Stop hunted then reversed
    PREMATURE_EXIT = "PREMATURE_EXIT"        # Exited too early


@dataclass
class MarketContext:
    """Market context at time of trade."""
    # Trend
    htf_trend: str          # D1/H4 trend
    ltf_trend: str          # H1/M15 trend
    trend_aligned: bool     # HTF and LTF same direction?

    # Price position
    price_vs_ema20: str     # ABOVE/BELOW
    price_vs_ema50: str
    price_vs_daily_open: str

    # Indicators
    rsi_at_entry: float
    atr_pips: float

    # Structure
    near_support: bool
    near_resistance: bool
    in_range: bool

    def to_dict(self) -> dict:
        return {
            "htf_trend": self.htf_trend,
            "ltf_trend": self.ltf_trend,
            "trend_aligned": self.trend_aligned,
            "price_vs_ema20": self.price_vs_ema20,
            "price_vs_ema50": self.price_vs_ema50,
            "rsi_at_entry": self.rsi_at_entry,
            "atr_pips": self.atr_pips,
            "near_support": self.near_support,
            "near_resistance": self.near_resistance,
            "in_range": self.in_range
        }


@dataclass
class EntryAnalysis:
    """Analysis of trade entry."""
    quality: EntryQuality
    session: TradingSession
    was_killzone: bool
    day_of_week: str

    # Entry location
    at_support_resistance: bool
    at_fvg: bool
    at_order_block: bool
    with_trend: bool

    # Distance metrics
    distance_from_swing_high_pips: float
    distance_from_swing_low_pips: float
    distance_from_daily_open_pips: float

    # Issues
    issues: List[str] = field(default_factory=list)
    positives: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "quality": self.quality.value,
            "session": self.session.value,
            "was_killzone": self.was_killzone,
            "day_of_week": self.day_of_week,
            "at_support_resistance": self.at_support_resistance,
            "at_fvg": self.at_fvg,
            "at_order_block": self.at_order_block,
            "with_trend": self.with_trend,
            "issues": self.issues,
            "positives": self.positives
        }


@dataclass
class ExcursionAnalysis:
    """Maximum Favorable/Adverse Excursion analysis."""
    # MFE - how much profit was available?
    mfe_pips: float
    mfe_price: float
    mfe_time: Optional[str]
    mfe_as_multiple_of_risk: float

    # MAE - how much did it go against?
    mae_pips: float
    mae_price: float
    mae_time: Optional[str]
    mae_as_multiple_of_risk: float

    # Timing
    time_to_mfe_hours: float
    time_to_mae_hours: float

    # Analysis
    reached_1r_profit: bool
    reached_2r_profit: bool
    stop_hunt_detected: bool

    def to_dict(self) -> dict:
        return {
            "mfe_pips": self.mfe_pips,
            "mfe_price": self.mfe_price,
            "mfe_as_multiple_of_risk": self.mfe_as_multiple_of_risk,
            "mae_pips": self.mae_pips,
            "mae_price": self.mae_price,
            "mae_as_multiple_of_risk": self.mae_as_multiple_of_risk,
            "time_to_mfe_hours": self.time_to_mfe_hours,
            "time_to_mae_hours": self.time_to_mae_hours,
            "reached_1r_profit": self.reached_1r_profit,
            "reached_2r_profit": self.reached_2r_profit,
            "stop_hunt_detected": self.stop_hunt_detected
        }


@dataclass
class ExitAnalysis:
    """Analysis of trade exit."""
    exit_type: str          # SL, TP, MANUAL, TIME
    was_optimal: bool
    better_exit_existed: bool
    better_exit_price: Optional[float]
    better_exit_pnl_pips: Optional[float]

    # Post-exit movement
    price_after_exit_5min: Optional[float]
    price_after_exit_1h: Optional[float]
    reversed_after_exit: bool
    reversal_pips: Optional[float]

    def to_dict(self) -> dict:
        return {
            "exit_type": self.exit_type,
            "was_optimal": self.was_optimal,
            "better_exit_existed": self.better_exit_existed,
            "better_exit_price": self.better_exit_price,
            "better_exit_pnl_pips": self.better_exit_pnl_pips,
            "reversed_after_exit": self.reversed_after_exit,
            "reversal_pips": self.reversal_pips
        }


@dataclass
class PostTradeAnalysis:
    """Complete post-trade analysis result."""
    # Basic info
    trade_id: str
    instrument: str
    direction: str
    pnl_pips: float
    pnl_amount: float
    duration_hours: float

    # Sub-analyses
    market_context: MarketContext
    entry_analysis: EntryAnalysis
    excursion: ExcursionAnalysis
    exit_analysis: ExitAnalysis

    # Overall assessment
    outcome: TradeOutcome
    was_good_trade: bool

    # Specific findings
    findings: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    what_to_do_differently: List[str] = field(default_factory=list)

    # Summary
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "instrument": self.instrument,
            "direction": self.direction,
            "pnl_pips": self.pnl_pips,
            "pnl_amount": self.pnl_amount,
            "duration_hours": self.duration_hours,
            "market_context": self.market_context.to_dict(),
            "entry_analysis": self.entry_analysis.to_dict(),
            "excursion": self.excursion.to_dict(),
            "exit_analysis": self.exit_analysis.to_dict(),
            "outcome": self.outcome.value,
            "was_good_trade": self.was_good_trade,
            "findings": self.findings,
            "lessons": self.lessons,
            "what_to_do_differently": self.what_to_do_differently,
            "summary": self.summary
        }


class PostTradeAnalyzer:
    """
    Comprehensive post-trade analyzer.

    Fetches market data and performs deep analysis of what happened.
    """

    # Session times (UTC)
    SESSIONS = {
        TradingSession.ASIAN: (0, 8),           # 00:00-08:00 UTC
        TradingSession.LONDON: (7, 16),          # 07:00-16:00 UTC
        TradingSession.NEW_YORK: (13, 22),       # 13:00-22:00 UTC
        TradingSession.LONDON_NY_OVERLAP: (13, 16)  # 13:00-16:00 UTC
    }

    # Killzones (high volatility periods, UTC)
    KILLZONES = {
        "LONDON_OPEN": (7, 10),      # 07:00-10:00 UTC
        "NY_OPEN": (13, 16),         # 13:00-16:00 UTC
        "LONDON_CLOSE": (15, 17),    # 15:00-17:00 UTC
    }

    def __init__(self, mt5_client=None):
        """
        Initialize analyzer.

        Args:
            mt5_client: Optional MT5Client instance
        """
        self._client = mt5_client

    def _get_client(self):
        """Lazy load MT5 client."""
        if self._client is None:
            from src.trading.mt5_client import MT5Client
            self._client = MT5Client()
        return self._client

    def _get_pip_value(self, instrument: str) -> float:
        """Get pip value for instrument."""
        if "BTC" in instrument or "ETH" in instrument:
            return 1.0
        elif "JPY" in instrument:
            return 0.01
        return 0.0001

    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime string to timezone-aware datetime."""
        if isinstance(dt_str, datetime):
            if dt_str.tzinfo is None:
                return dt_str.replace(tzinfo=timezone.utc)
            return dt_str

        # Handle various formats
        dt_str = dt_str.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(dt_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            return datetime.now(timezone.utc)

    def analyze_trade(self, trade_data: dict) -> PostTradeAnalysis:
        """
        Perform comprehensive post-trade analysis.

        Args:
            trade_data: Dict with trade details:
                - trade_id: Unique identifier
                - instrument: Currency pair (e.g., "EUR_USD")
                - direction: "LONG" or "SHORT"
                - entry_price: Entry price
                - exit_price: Exit price
                - opened_at: Entry timestamp
                - closed_at: Exit timestamp
                - stop_loss: SL price (optional)
                - take_profit: TP price (optional)
                - pnl: P/L amount (optional)

        Returns:
            PostTradeAnalysis with all findings
        """
        # Extract basic info
        trade_id = trade_data.get("trade_id", "UNKNOWN")
        instrument = trade_data.get("instrument", "EUR_USD")
        direction = trade_data.get("direction", "LONG")
        entry_price = float(trade_data.get("entry_price", 0))
        exit_price = float(trade_data.get("exit_price", 0))
        stop_loss = trade_data.get("stop_loss")
        take_profit = trade_data.get("take_profit")

        opened_at = self._parse_datetime(trade_data.get("opened_at", ""))
        closed_at = self._parse_datetime(trade_data.get("closed_at", ""))

        pip_value = self._get_pip_value(instrument)

        # Calculate basic metrics
        if direction == "LONG":
            pnl_pips = (exit_price - entry_price) / pip_value
        else:
            pnl_pips = (entry_price - exit_price) / pip_value

        pnl_amount = trade_data.get("pnl", 0) or 0
        duration_hours = (closed_at - opened_at).total_seconds() / 3600

        # Calculate risk (SL distance)
        if stop_loss:
            risk_pips = abs(entry_price - float(stop_loss)) / pip_value
        else:
            risk_pips = 30  # Default assumption

        logger.info(f"Analyzing trade {trade_id}: {instrument} {direction} {pnl_pips:.1f} pips")

        # Fetch market data
        try:
            candles_h1, candles_h4, candles_m15 = self._fetch_market_data(
                instrument, opened_at, closed_at
            )
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            candles_h1, candles_h4, candles_m15 = [], [], []

        # Perform analyses
        market_context = self._analyze_market_context(
            candles_h1, candles_h4, entry_price, instrument, pip_value
        )

        entry_analysis = self._analyze_entry(
            candles_h1, candles_m15, entry_price, direction,
            opened_at, instrument, pip_value, market_context
        )

        excursion = self._analyze_excursion(
            candles_m15, entry_price, direction, opened_at,
            closed_at, risk_pips, pip_value
        )

        exit_analysis = self._analyze_exit(
            candles_m15, entry_price, exit_price, direction,
            stop_loss, take_profit, closed_at, pip_value, excursion
        )

        # Determine outcome and generate insights
        outcome, was_good_trade = self._determine_outcome(
            pnl_pips, entry_analysis, excursion, exit_analysis
        )

        findings = self._generate_findings(
            market_context, entry_analysis, excursion, exit_analysis,
            direction, pnl_pips
        )

        lessons = self._generate_lessons(
            outcome, entry_analysis, excursion, exit_analysis, findings
        )

        what_to_do = self._generate_recommendations(
            outcome, entry_analysis, excursion, exit_analysis
        )

        summary = self._generate_summary(
            instrument, direction, pnl_pips, pnl_amount, duration_hours,
            outcome, findings, lessons
        )

        return PostTradeAnalysis(
            trade_id=trade_id,
            instrument=instrument,
            direction=direction,
            pnl_pips=round(pnl_pips, 1),
            pnl_amount=round(pnl_amount, 2),
            duration_hours=round(duration_hours, 1),
            market_context=market_context,
            entry_analysis=entry_analysis,
            excursion=excursion,
            exit_analysis=exit_analysis,
            outcome=outcome,
            was_good_trade=was_good_trade,
            findings=findings,
            lessons=lessons,
            what_to_do_differently=what_to_do,
            summary=summary
        )

    def _fetch_market_data(
        self,
        instrument: str,
        opened_at: datetime,
        closed_at: datetime
    ) -> tuple:
        """Fetch candles for multiple timeframes around the trade."""
        client = self._get_client()

        # Fetch H1 data - 48 hours before to 24 hours after
        # We need historical data at the time of trade, so we use copy_rates_range
        import MetaTrader5 as mt5

        symbol = client._convert_symbol(instrument)

        # Ensure symbol is selected
        if not mt5.symbol_select(symbol, True):
            logger.warning(f"Could not select symbol {symbol}")

        # Calculate time ranges
        start_time = opened_at - timedelta(hours=48)
        end_time = closed_at + timedelta(hours=24)

        # Fetch H1 candles
        rates_h1 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start_time, end_time)
        candles_h1 = self._rates_to_candles(rates_h1) if rates_h1 is not None else []

        # Fetch H4 candles
        rates_h4 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H4, start_time, end_time)
        candles_h4 = self._rates_to_candles(rates_h4) if rates_h4 is not None else []

        # Fetch M15 candles for precise entry/exit analysis
        rates_m15 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15,
                                          opened_at - timedelta(hours=6),
                                          closed_at + timedelta(hours=6))
        candles_m15 = self._rates_to_candles(rates_m15) if rates_m15 is not None else []

        logger.info(f"Fetched candles: H1={len(candles_h1)}, H4={len(candles_h4)}, M15={len(candles_m15)}")

        return candles_h1, candles_h4, candles_m15

    def _rates_to_candles(self, rates) -> list:
        """Convert MT5 rates to candle list."""
        if rates is None or len(rates) == 0:
            return []

        candles = []
        for rate in rates:
            candles.append({
                "time": datetime.fromtimestamp(rate['time'], tz=timezone.utc).isoformat(),
                "open": float(rate['open']),
                "high": float(rate['high']),
                "low": float(rate['low']),
                "close": float(rate['close']),
                "volume": int(rate['tick_volume'])
            })
        return candles

    def _analyze_market_context(
        self,
        candles_h1: list,
        candles_h4: list,
        entry_price: float,
        instrument: str,
        pip_value: float
    ) -> MarketContext:
        """Analyze market context at time of entry."""

        # Defaults if no data
        htf_trend = "UNKNOWN"
        ltf_trend = "UNKNOWN"
        rsi = 50.0
        atr_pips = 20.0
        ema20 = entry_price
        ema50 = entry_price

        if candles_h4:
            try:
                df_h4 = pd.DataFrame(candles_h4)
                df_h4['close'] = pd.to_numeric(df_h4['close'])
                df_h4['high'] = pd.to_numeric(df_h4['high'])
                df_h4['low'] = pd.to_numeric(df_h4['low'])

                # Calculate EMAs
                df_h4['ema20'] = df_h4['close'].ewm(span=20, adjust=False).mean()
                df_h4['ema50'] = df_h4['close'].ewm(span=50, adjust=False).mean()

                # Determine HTF trend
                last_close = df_h4['close'].iloc[-1]
                last_ema20 = df_h4['ema20'].iloc[-1]
                last_ema50 = df_h4['ema50'].iloc[-1]

                if last_close > last_ema20 > last_ema50:
                    htf_trend = "BULLISH"
                elif last_close < last_ema20 < last_ema50:
                    htf_trend = "BEARISH"
                else:
                    htf_trend = "RANGING"

                ema20 = last_ema20
                ema50 = last_ema50

            except Exception as e:
                logger.warning(f"Error analyzing H4 data: {e}")

        if candles_h1:
            try:
                df_h1 = pd.DataFrame(candles_h1)
                df_h1['close'] = pd.to_numeric(df_h1['close'])
                df_h1['high'] = pd.to_numeric(df_h1['high'])
                df_h1['low'] = pd.to_numeric(df_h1['low'])

                # Calculate indicators
                df_h1['ema20'] = df_h1['close'].ewm(span=20, adjust=False).mean()
                df_h1['ema50'] = df_h1['close'].ewm(span=50, adjust=False).mean()

                # RSI
                delta = df_h1['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df_h1['rsi'] = 100 - (100 / (1 + rs))

                # ATR
                df_h1['tr'] = np.maximum(
                    df_h1['high'] - df_h1['low'],
                    np.maximum(
                        abs(df_h1['high'] - df_h1['close'].shift()),
                        abs(df_h1['low'] - df_h1['close'].shift())
                    )
                )
                df_h1['atr'] = df_h1['tr'].rolling(window=14).mean()

                # Get values at entry time
                last_close = df_h1['close'].iloc[-1]
                last_ema20_h1 = df_h1['ema20'].iloc[-1]
                last_ema50_h1 = df_h1['ema50'].iloc[-1]
                rsi = df_h1['rsi'].iloc[-1] if not pd.isna(df_h1['rsi'].iloc[-1]) else 50
                atr = df_h1['atr'].iloc[-1] if not pd.isna(df_h1['atr'].iloc[-1]) else 0.002
                atr_pips = atr / pip_value

                # Determine LTF trend
                if last_close > last_ema20_h1 > last_ema50_h1:
                    ltf_trend = "BULLISH"
                elif last_close < last_ema20_h1 < last_ema50_h1:
                    ltf_trend = "BEARISH"
                else:
                    ltf_trend = "RANGING"

            except Exception as e:
                logger.warning(f"Error analyzing H1 data: {e}")

        # Check structure
        near_support = False
        near_resistance = False
        in_range = htf_trend == "RANGING" or ltf_trend == "RANGING"

        if candles_h1:
            try:
                df = pd.DataFrame(candles_h1)
                recent_high = df['high'].max()
                recent_low = df['low'].min()
                range_size = (recent_high - recent_low) / pip_value

                dist_from_high = (recent_high - entry_price) / pip_value
                dist_from_low = (entry_price - recent_low) / pip_value

                near_resistance = dist_from_high < range_size * 0.2
                near_support = dist_from_low < range_size * 0.2
            except:
                pass

        return MarketContext(
            htf_trend=htf_trend,
            ltf_trend=ltf_trend,
            trend_aligned=(htf_trend == ltf_trend and htf_trend != "RANGING"),
            price_vs_ema20="ABOVE" if entry_price > ema20 else "BELOW",
            price_vs_ema50="ABOVE" if entry_price > ema50 else "BELOW",
            price_vs_daily_open="UNKNOWN",
            rsi_at_entry=round(rsi, 1),
            atr_pips=round(atr_pips, 1),
            near_support=near_support,
            near_resistance=near_resistance,
            in_range=in_range
        )

    def _analyze_entry(
        self,
        candles_h1: list,
        candles_m15: list,
        entry_price: float,
        direction: str,
        opened_at: datetime,
        instrument: str,
        pip_value: float,
        market_context: MarketContext
    ) -> EntryAnalysis:
        """Analyze entry quality."""

        # Determine session
        hour = opened_at.hour
        session = self._get_session(hour)
        was_killzone = self._is_killzone(hour)
        day_of_week = opened_at.strftime("%A")

        # Check if with trend
        if direction == "LONG":
            with_trend = market_context.htf_trend == "BULLISH"
        else:
            with_trend = market_context.htf_trend == "BEARISH"

        # Initialize
        issues = []
        positives = []
        at_sr = False
        at_fvg = False
        at_ob = False
        dist_from_high = 0
        dist_from_low = 0
        dist_from_daily = 0

        if candles_h1:
            try:
                df = pd.DataFrame(candles_h1)
                df['high'] = pd.to_numeric(df['high'])
                df['low'] = pd.to_numeric(df['low'])

                recent_high = df['high'].max()
                recent_low = df['low'].min()

                dist_from_high = (recent_high - entry_price) / pip_value
                dist_from_low = (entry_price - recent_low) / pip_value

                # Check S/R
                if dist_from_low < 20 and direction == "LONG":
                    at_sr = True
                    positives.append("Entry near support level")
                elif dist_from_high < 20 and direction == "SHORT":
                    at_sr = True
                    positives.append("Entry near resistance level")

            except:
                pass

        # Check for FVG (simplified - look for imbalance in recent candles)
        if candles_m15 and len(candles_m15) >= 10:
            try:
                at_fvg = self._detect_fvg_at_entry(candles_m15, entry_price, direction, pip_value)
                if at_fvg:
                    positives.append("Entry at Fair Value Gap")
            except:
                pass

        # Check for Order Block (simplified)
        if candles_h1 and len(candles_h1) >= 5:
            try:
                at_ob = self._detect_order_block(candles_h1, entry_price, direction, pip_value)
                if at_ob:
                    positives.append("Entry at Order Block")
            except:
                pass

        # Generate issues
        if not with_trend:
            issues.append(f"Counter-trend trade (HTF was {market_context.htf_trend})")

        if not market_context.trend_aligned:
            issues.append("HTF/LTF trend not aligned")

        if session == TradingSession.ASIAN and instrument in ["EUR_USD", "GBP_USD"]:
            issues.append("EUR/GBP pair traded during Asian session (low liquidity)")

        if session == TradingSession.OFF_HOURS:
            issues.append("Trade during off-hours (low liquidity)")

        if not was_killzone:
            issues.append("Entry outside killzone hours")

        if day_of_week in ["Monday", "Friday"]:
            issues.append(f"Trade on {day_of_week} (higher risk day)")

        if market_context.rsi_at_entry > 70 and direction == "LONG":
            issues.append(f"RSI overbought ({market_context.rsi_at_entry}) for LONG entry")
        elif market_context.rsi_at_entry < 30 and direction == "SHORT":
            issues.append(f"RSI oversold ({market_context.rsi_at_entry}) for SHORT entry")

        if direction == "LONG" and market_context.near_resistance:
            issues.append("LONG entry near resistance")
        elif direction == "SHORT" and market_context.near_support:
            issues.append("SHORT entry near support")

        # Additional positives
        if with_trend:
            positives.append(f"With-trend trade ({market_context.htf_trend})")
        if was_killzone:
            positives.append(f"Entry during killzone")
        if market_context.trend_aligned:
            positives.append("HTF/LTF trends aligned")

        # Determine quality
        quality = self._calculate_entry_quality(
            with_trend, at_sr, at_fvg, at_ob, was_killzone,
            len(issues), len(positives)
        )

        return EntryAnalysis(
            quality=quality,
            session=session,
            was_killzone=was_killzone,
            day_of_week=day_of_week,
            at_support_resistance=at_sr,
            at_fvg=at_fvg,
            at_order_block=at_ob,
            with_trend=with_trend,
            distance_from_swing_high_pips=round(dist_from_high, 1),
            distance_from_swing_low_pips=round(dist_from_low, 1),
            distance_from_daily_open_pips=round(dist_from_daily, 1),
            issues=issues,
            positives=positives
        )

    def _detect_fvg_at_entry(
        self,
        candles: list,
        entry_price: float,
        direction: str,
        pip_value: float
    ) -> bool:
        """Detect if entry was at a Fair Value Gap."""
        # FVG: Gap between candle 1 high/low and candle 3 high/low
        # with candle 2 not filling the gap

        for i in range(2, min(len(candles) - 1, 20)):  # Check last 20 candles
            c1 = candles[i - 2]
            c2 = candles[i - 1]
            c3 = candles[i]

            # Bullish FVG: c1_high < c3_low (gap up)
            if direction == "LONG":
                if float(c1['high']) < float(c3['low']):
                    gap_low = float(c1['high'])
                    gap_high = float(c3['low'])
                    if gap_low <= entry_price <= gap_high:
                        return True

            # Bearish FVG: c1_low > c3_high (gap down)
            else:
                if float(c1['low']) > float(c3['high']):
                    gap_low = float(c3['high'])
                    gap_high = float(c1['low'])
                    if gap_low <= entry_price <= gap_high:
                        return True

        return False

    def _detect_order_block(
        self,
        candles: list,
        entry_price: float,
        direction: str,
        pip_value: float
    ) -> bool:
        """Detect if entry was at an Order Block."""
        # OB: Last opposite candle before strong move

        for i in range(1, min(len(candles) - 2, 15)):
            c = candles[i]
            c_next = candles[i + 1]

            is_bullish = float(c['close']) > float(c['open'])
            next_is_bullish = float(c_next['close']) > float(c_next['open'])

            # Bullish OB: bearish candle followed by strong bullish move
            if direction == "LONG" and not is_bullish and next_is_bullish:
                ob_low = float(c['low'])
                ob_high = float(c['high'])
                move_size = abs(float(c_next['close']) - float(c_next['open'])) / pip_value

                if move_size > 10 and ob_low <= entry_price <= ob_high:
                    return True

            # Bearish OB: bullish candle followed by strong bearish move
            elif direction == "SHORT" and is_bullish and not next_is_bullish:
                ob_low = float(c['low'])
                ob_high = float(c['high'])
                move_size = abs(float(c_next['close']) - float(c_next['open'])) / pip_value

                if move_size > 10 and ob_low <= entry_price <= ob_high:
                    return True

        return False

    def _calculate_entry_quality(
        self,
        with_trend: bool,
        at_sr: bool,
        at_fvg: bool,
        at_ob: bool,
        was_killzone: bool,
        num_issues: int,
        num_positives: int
    ) -> EntryQuality:
        """Calculate overall entry quality."""
        score = 0

        if with_trend:
            score += 2
        if at_sr:
            score += 1
        if at_fvg:
            score += 2
        if at_ob:
            score += 2
        if was_killzone:
            score += 1

        score -= num_issues * 0.5

        if score >= 5:
            return EntryQuality.EXCELLENT
        elif score >= 3:
            return EntryQuality.GOOD
        elif score >= 1:
            return EntryQuality.FAIR
        else:
            return EntryQuality.POOR

    def _get_session(self, hour: int) -> TradingSession:
        """Get trading session for UTC hour."""
        if 13 <= hour < 16:
            return TradingSession.LONDON_NY_OVERLAP
        elif 7 <= hour < 16:
            return TradingSession.LONDON
        elif 13 <= hour < 22:
            return TradingSession.NEW_YORK
        elif 0 <= hour < 8:
            return TradingSession.ASIAN
        else:
            return TradingSession.OFF_HOURS

    def _is_killzone(self, hour: int) -> bool:
        """Check if hour is in a killzone."""
        for kz_name, (start, end) in self.KILLZONES.items():
            if start <= hour < end:
                return True
        return False

    def _analyze_excursion(
        self,
        candles_m15: list,
        entry_price: float,
        direction: str,
        opened_at: datetime,
        closed_at: datetime,
        risk_pips: float,
        pip_value: float
    ) -> ExcursionAnalysis:
        """Analyze Maximum Favorable/Adverse Excursion."""

        mfe_pips = 0.0
        mfe_price = entry_price
        mfe_time = None
        mae_pips = 0.0
        mae_price = entry_price
        mae_time = None

        if candles_m15:
            try:
                df = pd.DataFrame(candles_m15)
                df['time'] = pd.to_datetime(df['time'])
                df['high'] = pd.to_numeric(df['high'])
                df['low'] = pd.to_numeric(df['low'])

                # Filter to trade duration
                df = df[(df['time'] >= opened_at) & (df['time'] <= closed_at)]

                if len(df) > 0:
                    if direction == "LONG":
                        # MFE: highest high - entry
                        max_high_idx = df['high'].idxmax()
                        mfe_price = df.loc[max_high_idx, 'high']
                        mfe_pips = (mfe_price - entry_price) / pip_value
                        mfe_time = str(df.loc[max_high_idx, 'time'])

                        # MAE: entry - lowest low
                        min_low_idx = df['low'].idxmin()
                        mae_price = df.loc[min_low_idx, 'low']
                        mae_pips = (entry_price - mae_price) / pip_value
                        mae_time = str(df.loc[min_low_idx, 'time'])
                    else:  # SHORT
                        # MFE: entry - lowest low
                        min_low_idx = df['low'].idxmin()
                        mfe_price = df.loc[min_low_idx, 'low']
                        mfe_pips = (entry_price - mfe_price) / pip_value
                        mfe_time = str(df.loc[min_low_idx, 'time'])

                        # MAE: highest high - entry
                        max_high_idx = df['high'].idxmax()
                        mae_price = df.loc[max_high_idx, 'high']
                        mae_pips = (mae_price - entry_price) / pip_value
                        mae_time = str(df.loc[max_high_idx, 'time'])

            except Exception as e:
                logger.warning(f"Error calculating MFE/MAE: {e}")

        # Calculate time to MFE/MAE
        time_to_mfe = 0
        time_to_mae = 0
        if mfe_time:
            try:
                mfe_dt = pd.to_datetime(mfe_time)
                if mfe_dt.tzinfo is None:
                    mfe_dt = mfe_dt.replace(tzinfo=timezone.utc)
                time_to_mfe = (mfe_dt - opened_at).total_seconds() / 3600
            except:
                pass
        if mae_time:
            try:
                mae_dt = pd.to_datetime(mae_time)
                if mae_dt.tzinfo is None:
                    mae_dt = mae_dt.replace(tzinfo=timezone.utc)
                time_to_mae = (mae_dt - opened_at).total_seconds() / 3600
            except:
                pass

        # Calculate multiples of risk
        mfe_r = mfe_pips / risk_pips if risk_pips > 0 else 0
        mae_r = mae_pips / risk_pips if risk_pips > 0 else 0

        # Check for stop hunt
        stop_hunt = mae_r > 1.0 and mfe_r > 1.0  # Hit SL area then went to profit

        return ExcursionAnalysis(
            mfe_pips=round(max(0, mfe_pips), 1),
            mfe_price=round(mfe_price, 5),
            mfe_time=mfe_time,
            mfe_as_multiple_of_risk=round(mfe_r, 2),
            mae_pips=round(max(0, mae_pips), 1),
            mae_price=round(mae_price, 5),
            mae_time=mae_time,
            mae_as_multiple_of_risk=round(mae_r, 2),
            time_to_mfe_hours=round(time_to_mfe, 1),
            time_to_mae_hours=round(time_to_mae, 1),
            reached_1r_profit=mfe_r >= 1.0,
            reached_2r_profit=mfe_r >= 2.0,
            stop_hunt_detected=stop_hunt
        )

    def _analyze_exit(
        self,
        candles_m15: list,
        entry_price: float,
        exit_price: float,
        direction: str,
        stop_loss: float,
        take_profit: float,
        closed_at: datetime,
        pip_value: float,
        excursion: ExcursionAnalysis
    ) -> ExitAnalysis:
        """Analyze trade exit."""

        # Determine exit type
        exit_type = "MANUAL"
        if stop_loss and abs(exit_price - float(stop_loss)) < pip_value * 5:
            exit_type = "SL"
        elif take_profit and abs(exit_price - float(take_profit)) < pip_value * 5:
            exit_type = "TP"

        # Check if there was a better exit
        better_exit = False
        better_price = None
        better_pnl = None

        if direction == "LONG":
            if excursion.mfe_price > exit_price:
                better_exit = True
                better_price = excursion.mfe_price
                better_pnl = (excursion.mfe_price - entry_price) / pip_value
        else:
            if excursion.mfe_price < exit_price:
                better_exit = True
                better_price = excursion.mfe_price
                better_pnl = (entry_price - excursion.mfe_price) / pip_value

        # Check post-exit price movement
        reversed_after = False
        reversal_pips = None
        price_after_5min = None
        price_after_1h = None

        if candles_m15:
            try:
                df = pd.DataFrame(candles_m15)
                df['time'] = pd.to_datetime(df['time'])
                df['close'] = pd.to_numeric(df['close'])

                # Get candles after exit
                after_exit = df[df['time'] > closed_at]

                if len(after_exit) > 0:
                    price_after_5min = after_exit.iloc[0]['close'] if len(after_exit) > 0 else None
                    price_after_1h = after_exit.iloc[min(4, len(after_exit)-1)]['close']

                    # Check if reversed
                    if direction == "LONG":
                        # Price went up after we exited
                        max_after = after_exit['close'].max()
                        if max_after > exit_price:
                            reversed_after = True
                            reversal_pips = (max_after - exit_price) / pip_value
                    else:
                        # Price went down after we exited
                        min_after = after_exit['close'].min()
                        if min_after < exit_price:
                            reversed_after = True
                            reversal_pips = (exit_price - min_after) / pip_value

            except Exception as e:
                logger.warning(f"Error analyzing post-exit: {e}")

        # Determine if exit was optimal
        was_optimal = not better_exit or (better_pnl and better_pnl < 10)

        return ExitAnalysis(
            exit_type=exit_type,
            was_optimal=was_optimal,
            better_exit_existed=better_exit,
            better_exit_price=round(better_price, 5) if better_price else None,
            better_exit_pnl_pips=round(better_pnl, 1) if better_pnl else None,
            price_after_exit_5min=price_after_5min,
            price_after_exit_1h=price_after_1h,
            reversed_after_exit=reversed_after,
            reversal_pips=round(reversal_pips, 1) if reversal_pips else None
        )

    def _determine_outcome(
        self,
        pnl_pips: float,
        entry: EntryAnalysis,
        excursion: ExcursionAnalysis,
        exit: ExitAnalysis
    ) -> tuple[TradeOutcome, bool]:
        """Determine overall trade outcome."""

        won = pnl_pips > 0
        good_entry = entry.quality in [EntryQuality.EXCELLENT, EntryQuality.GOOD]

        if won:
            if good_entry:
                return TradeOutcome.GOOD_TRADE_WIN, True
            else:
                return TradeOutcome.BAD_TRADE_WIN, False
        else:
            # Lost
            if good_entry:
                # Good setup but lost
                if excursion.stop_hunt_detected:
                    return TradeOutcome.UNLUCKY, True  # Still a good trade
                elif excursion.reached_1r_profit and not exit.was_optimal:
                    return TradeOutcome.PREMATURE_EXIT, False  # Management issue
                else:
                    return TradeOutcome.GOOD_TRADE_LOSS, True  # Acceptable loss
            else:
                return TradeOutcome.BAD_TRADE_LOSS, False

    def _generate_findings(
        self,
        market: MarketContext,
        entry: EntryAnalysis,
        excursion: ExcursionAnalysis,
        exit: ExitAnalysis,
        direction: str,
        pnl_pips: float
    ) -> List[str]:
        """Generate specific findings about the trade."""
        findings = []

        # Market context findings
        if not market.trend_aligned:
            findings.append(f"HTF trend ({market.htf_trend}) and LTF trend ({market.ltf_trend}) were not aligned")

        if direction == "LONG" and market.htf_trend == "BEARISH":
            findings.append("LONG trade against bearish HTF trend")
        elif direction == "SHORT" and market.htf_trend == "BULLISH":
            findings.append("SHORT trade against bullish HTF trend")

        # Entry findings
        if entry.quality == EntryQuality.POOR:
            findings.append(f"Entry quality was POOR - no confluence detected")

        if not entry.was_killzone:
            findings.append(f"Entry at {entry.session.value} session, outside killzone")

        if entry.issues:
            findings.extend(entry.issues[:3])  # Top 3 issues

        # Excursion findings
        if excursion.reached_2r_profit:
            findings.append(f"Price reached 2R profit ({excursion.mfe_pips:.0f} pips MFE) but wasn't captured")
        elif excursion.reached_1r_profit:
            findings.append(f"Price reached 1R profit ({excursion.mfe_pips:.0f} pips MFE)")

        if excursion.stop_hunt_detected:
            findings.append("Stop hunt pattern detected - SL area was hit then price reversed")

        if excursion.mae_as_multiple_of_risk > 0.8 and pnl_pips < 0:
            findings.append(f"MAE was {excursion.mae_pips:.0f} pips - SL was likely hit")

        # Exit findings
        if exit.reversed_after_exit and exit.reversal_pips and exit.reversal_pips > 20:
            findings.append(f"Price reversed {exit.reversal_pips:.0f} pips after exit")

        if exit.better_exit_existed and exit.better_exit_pnl_pips:
            findings.append(f"Better exit existed at MFE: could have made {exit.better_exit_pnl_pips:.0f} pips")

        return findings

    def _generate_lessons(
        self,
        outcome: TradeOutcome,
        entry: EntryAnalysis,
        excursion: ExcursionAnalysis,
        exit: ExitAnalysis,
        findings: List[str]
    ) -> List[str]:
        """Generate actionable lessons."""
        lessons = []

        if outcome == TradeOutcome.BAD_TRADE_LOSS:
            if not entry.with_trend:
                lessons.append("Wait for HTF trend alignment before entering")
            if not entry.was_killzone:
                lessons.append("Focus entries during London/NY killzones")
            if entry.quality == EntryQuality.POOR:
                lessons.append("Require at least one confluence factor (FVG, OB, or S/R)")

        elif outcome == TradeOutcome.PREMATURE_EXIT:
            lessons.append("Consider trailing stop instead of fixed exit")
            if excursion.reached_2r_profit:
                lessons.append("Take partial profits at 1R, let rest run to 2R")

        elif outcome == TradeOutcome.UNLUCKY:
            lessons.append("This was a valid setup - don't change strategy based on this loss")
            lessons.append("Consider wider SL placement (1.5x ATR minimum)")

        elif outcome == TradeOutcome.GOOD_TRADE_LOSS:
            lessons.append("Good trade that didn't work out - this is part of trading")

        # General lessons from issues
        for issue in entry.issues:
            if "counter-trend" in issue.lower():
                lessons.append("Avoid counter-trend trades unless at major reversal levels")
            if "asian" in issue.lower():
                lessons.append("Trade EUR/GBP pairs only during London/NY sessions")

        return list(set(lessons))[:5]  # Unique, max 5

    def _generate_recommendations(
        self,
        outcome: TradeOutcome,
        entry: EntryAnalysis,
        excursion: ExcursionAnalysis,
        exit: ExitAnalysis
    ) -> List[str]:
        """Generate specific recommendations for future trades."""
        recs = []

        if not entry.with_trend:
            recs.append("CHECK HTF trend on H4/D1 before every entry")

        if not entry.was_killzone:
            recs.append("SET ALERTS for killzone times (7-10 UTC, 13-16 UTC)")

        if entry.quality in [EntryQuality.POOR, EntryQuality.FAIR]:
            recs.append("USE entry checklist: FVG or OB + S/R + Killzone")

        if excursion.reached_1r_profit and not exit.was_optimal:
            recs.append("IMPLEMENT: Move SL to breakeven at 1R profit")

        if excursion.reached_2r_profit:
            recs.append("IMPLEMENT: Take 50% at 1R, trail rest to 2R+")

        if excursion.stop_hunt_detected:
            recs.append("WIDEN SL: Use 1.5x ATR or place SL behind structure")

        return recs[:4]  # Max 4 recommendations

    def _generate_summary(
        self,
        instrument: str,
        direction: str,
        pnl_pips: float,
        pnl_amount: float,
        duration: float,
        outcome: TradeOutcome,
        findings: List[str],
        lessons: List[str]
    ) -> str:
        """Generate human-readable summary."""

        outcome_emoji = {
            TradeOutcome.GOOD_TRADE_WIN: "Good trade that worked",
            TradeOutcome.GOOD_TRADE_LOSS: "Valid setup, acceptable loss",
            TradeOutcome.BAD_TRADE_WIN: "Got lucky on a poor setup",
            TradeOutcome.BAD_TRADE_LOSS: "Poor setup, expected loss",
            TradeOutcome.UNLUCKY: "Good trade, got stopped out unfairly",
            TradeOutcome.PREMATURE_EXIT: "Good entry, poor exit management"
        }

        summary = f"""
## Post-Trade Analysis: {instrument} {direction}

**Result:** {pnl_pips:+.1f} pips ({pnl_amount:+.2f} EUR) in {duration:.1f} hours

**Verdict:** {outcome_emoji.get(outcome, "Unknown")}

### Key Findings:
"""
        for f in findings[:5]:
            summary += f"- {f}\n"

        summary += "\n### Lessons:\n"
        for l in lessons[:3]:
            summary += f"- {l}\n"

        return summary


# Convenience function
def analyze_closed_trade(trade_data: dict) -> PostTradeAnalysis:
    """
    Analyze a closed trade.

    Args:
        trade_data: Trade details dict

    Returns:
        PostTradeAnalysis
    """
    analyzer = PostTradeAnalyzer()
    return analyzer.analyze_trade(trade_data)
