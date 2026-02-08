"""
Scalping Strategy - SMC-based quick trades with tight stops.

Uses Smart Money Concepts for entry:
- FVG entry: enter at Fair Value Gap fill
- OB entry: enter at Order Block retest
- Sweep reversal: enter after liquidity sweep with confirmation

Candlestick patterns (engulfing, hammer) used as secondary confirmation.

Usage:
    from src.strategies.scalping import ScalpingStrategy

    strategy = ScalpingStrategy(config)
    signal = strategy.analyze(candles, price, instrument)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from src.core.auto_config import ScalpingConfig
from src.market.indicators import TechnicalAnalysis
from src.utils.logger import logger


@dataclass
class ScalpingSignal:
    """Signal from scalping strategy."""
    is_valid: bool
    direction: Optional[str] = None  # LONG or SHORT
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    confidence_boost: int = 0  # Adjustment to confidence
    reason: str = ""
    patterns: List[str] = None  # Detected patterns

    def __post_init__(self):
        if self.patterns is None:
            self.patterns = []


class ScalpingStrategy:
    """
    SMC-based scalping strategy implementation.

    Entry patterns:
    - FVG_ENTRY: Price pulls back into an unfilled Fair Value Gap
    - OB_ENTRY: Price pulls back into a fresh Order Block
    - SWEEP_REVERSAL: Liquidity sweep with immediate reversal candle

    Secondary confirmation:
    - Bullish/Bearish engulfing
    - Hammer/Shooting star
    """

    def __init__(self, config: ScalpingConfig):
        self.config = config
        logger.info("ScalpingStrategy initialized [SMC MODE]")

    def analyze(
        self,
        candles: List[Dict[str, Any]],
        price: Dict[str, Any],
        instrument: str,
        technical: Optional[TechnicalAnalysis] = None,
        smc_analysis=None
    ) -> ScalpingSignal:
        """
        Analyze market for SMC scalping opportunity.

        Args:
            candles: OHLC candle data
            price: Current price data
            instrument: Instrument symbol
            technical: Pre-computed technical analysis (optional)
            smc_analysis: Pre-computed SMC analysis (optional)

        Returns:
            ScalpingSignal with entry details if valid
        """
        if len(candles) < 20:
            return ScalpingSignal(is_valid=False, reason="Not enough data")

        # Check spread
        spread = price.get("spread_pips", 999)
        if spread > self.config.max_spread_pips:
            return ScalpingSignal(
                is_valid=False,
                reason=f"Spread too high: {spread:.1f} > {self.config.max_spread_pips}"
            )

        # Check volatility
        if technical and technical.atr_pips < self.config.min_atr_pips:
            return ScalpingSignal(
                is_valid=False,
                reason=f"ATR too low: {technical.atr_pips:.1f} < {self.config.min_atr_pips}"
            )

        # Detect SMC scalping patterns
        patterns = []
        direction = None
        confidence_boost = 0

        # If we have SMC analysis, use it for pattern detection
        if smc_analysis and smc_analysis.direction:
            direction = smc_analysis.direction

            # Pattern: FVG entry
            if self._check_fvg_entry(candles, price, smc_analysis):
                patterns.append("FVG_ENTRY")
                confidence_boost += 10

            # Pattern: Order Block entry
            if self._check_ob_entry(candles, price, smc_analysis):
                patterns.append("OB_ENTRY")
                confidence_boost += 8

            # Pattern: Sweep reversal
            if smc_analysis.sweep_detected and smc_analysis.sweep_detected.reversal_confirmed:
                patterns.append("SWEEP_REVERSAL")
                confidence_boost += 12

        # Secondary confirmation: candlestick patterns
        momentum = self._check_momentum_shift(candles)
        if momentum:
            patterns.append(f"CANDLE_{momentum}")
            if direction is None:
                direction = momentum
            confidence_boost += 5

        if not patterns or direction is None:
            return ScalpingSignal(
                is_valid=False,
                reason="No SMC scalping patterns detected"
            )

        # Calculate entry, SL, TP
        pip_value = self._get_pip_value(instrument)

        if direction == "LONG":
            entry = price["ask"]
            sl_pips = min(
                technical.atr_pips * 1.2 if technical else 10,
                self.config.max_sl_pips
            )
            tp_pips = sl_pips * self.config.target_rr
            sl = entry - (sl_pips * pip_value)
            tp = entry + (tp_pips * pip_value)
        else:
            entry = price["bid"]
            sl_pips = min(
                technical.atr_pips * 1.2 if technical else 10,
                self.config.max_sl_pips
            )
            tp_pips = sl_pips * self.config.target_rr
            sl = entry + (sl_pips * pip_value)
            tp = entry - (tp_pips * pip_value)

        return ScalpingSignal(
            is_valid=True,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            confidence_boost=confidence_boost,
            reason=f"SMC scalping: {', '.join(patterns)}",
            patterns=patterns
        )

    def _check_fvg_entry(self, candles, price, smc_analysis) -> bool:
        """Check if price is pulling back into an unfilled FVG."""
        if not smc_analysis or not smc_analysis.fvgs:
            return False

        current_price = price.get("bid", 0)

        for fvg in smc_analysis.fvgs:
            if fvg.filled:
                continue

            gap_top = max(fvg.start_price, fvg.end_price)
            gap_bottom = min(fvg.start_price, fvg.end_price)

            # Price is within the FVG zone
            if gap_bottom <= current_price <= gap_top:
                if smc_analysis.direction == "LONG" and fvg.direction == "BULLISH":
                    return True
                if smc_analysis.direction == "SHORT" and fvg.direction == "BEARISH":
                    return True

        return False

    def _check_ob_entry(self, candles, price, smc_analysis) -> bool:
        """Check if price is at a fresh Order Block."""
        if not smc_analysis or not smc_analysis.order_blocks:
            return False

        current_price = price.get("bid", 0)

        for ob in smc_analysis.order_blocks:
            if ob.mitigated:
                continue

            # Price is within the OB zone
            if ob.low <= current_price <= ob.high:
                if smc_analysis.direction == "LONG" and ob.direction == "BULLISH":
                    return True
                if smc_analysis.direction == "SHORT" and ob.direction == "BEARISH":
                    return True

        return False

    def _check_momentum_shift(self, candles: List[Dict]) -> Optional[str]:
        """Check for momentum shift using candlestick patterns."""
        if len(candles) < 3:
            return None

        c2, c3 = candles[-2], candles[-1]

        if self._is_bullish_engulfing(c2, c3):
            return "LONG"
        if self._is_bearish_engulfing(c2, c3):
            return "SHORT"
        if self._is_hammer(c3):
            return "LONG"
        if self._is_shooting_star(c3):
            return "SHORT"

        return None

    def _is_bullish_engulfing(self, prev: Dict, curr: Dict) -> bool:
        prev_open = prev.get("open", 0)
        prev_close = prev.get("close", 0)
        curr_open = curr.get("open", 0)
        curr_close = curr.get("close", 0)
        prev_bearish = prev_close < prev_open
        curr_bullish = curr_close > curr_open
        engulfs = curr_open <= prev_close and curr_close >= prev_open
        return prev_bearish and curr_bullish and engulfs

    def _is_bearish_engulfing(self, prev: Dict, curr: Dict) -> bool:
        prev_open = prev.get("open", 0)
        prev_close = prev.get("close", 0)
        curr_open = curr.get("open", 0)
        curr_close = curr.get("close", 0)
        prev_bullish = prev_close > prev_open
        curr_bearish = curr_close < curr_open
        engulfs = curr_open >= prev_close and curr_close <= prev_open
        return prev_bullish and curr_bearish and engulfs

    def _is_hammer(self, candle: Dict) -> bool:
        o, h, l, c = candle.get("open", 0), candle.get("high", 0), candle.get("low", 0), candle.get("close", 0)
        body = abs(c - o)
        total_range = h - l
        lower_wick = min(o, c) - l
        if total_range == 0:
            return False
        return body / total_range < 0.3 and lower_wick / total_range > 0.6 and c >= o

    def _is_shooting_star(self, candle: Dict) -> bool:
        o, h, l, c = candle.get("open", 0), candle.get("high", 0), candle.get("low", 0), candle.get("close", 0)
        body = abs(c - o)
        total_range = h - l
        upper_wick = h - max(o, c)
        if total_range == 0:
            return False
        return body / total_range < 0.3 and upper_wick / total_range > 0.6 and c <= o

    def _get_pip_value(self, instrument: str) -> float:
        if "XAU" in instrument:
            return 0.1
        if "BTC" in instrument or "ETH" in instrument:
            return 1.0
        if "JPY" in instrument:
            return 0.01
        return 0.0001

    def validate_entry_timing(self, instrument: str) -> tuple:
        """Validate if it's a good time for scalping entry."""
        now = datetime.now(timezone.utc)
        hour = now.hour
        preferred = self.config.preferred_sessions

        in_session = False
        if "london" in preferred and 7 <= hour < 16:
            in_session = True
        if "newyork" in preferred and 12 <= hour < 21:
            in_session = True
        if "asian" in preferred and (hour >= 23 or hour < 8):
            in_session = True

        if not in_session:
            return False, "Outside preferred trading sessions"

        minute = now.minute
        if hour == 7 and minute < 30:
            return False, "First 30 min of London session"
        if hour in [12, 13] and minute < 30:
            return False, "First 30 min of NY session"

        return True, "OK"

    def get_scalping_stats(self) -> dict:
        return {
            "max_sl_pips": self.config.max_sl_pips,
            "target_rr": self.config.target_rr,
            "max_hold_minutes": self.config.max_hold_minutes,
            "max_spread_pips": self.config.max_spread_pips,
            "min_atr_pips": self.config.min_atr_pips,
            "preferred_sessions": self.config.preferred_sessions
        }
