"""
Scalping Strategy - Quick trades with tight stops.

Implements scalping-specific analysis and entry rules based on
the scalping.md skill file.

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
    Scalping strategy implementation.

    Rules (from scalping.md):
    - Timeframe: M5, M15 primary, M30/H1 confirmation
    - Entry: Bounce from S/R after pullback
    - Max SL: 15 pips
    - Max TP: 10-20 pips
    - R:R: minimum 1:1
    - Max duration: 1-2 hours
    - Max risk: 1% per scalp (absolute)

    Avoid:
    - First/last 30 min of session
    - Major news events
    - Spread > 1.5 pips
    - Low volume periods
    """

    def __init__(self, config: ScalpingConfig):
        """
        Initialize scalping strategy.

        Args:
            config: Scalping configuration
        """
        self.config = config
        logger.info("ScalpingStrategy initialized")

    def analyze(
        self,
        candles: List[Dict[str, Any]],
        price: Dict[str, Any],
        instrument: str,
        technical: Optional[TechnicalAnalysis] = None
    ) -> ScalpingSignal:
        """
        Analyze market for scalping opportunity.

        Args:
            candles: OHLC candle data
            price: Current price data
            instrument: Instrument symbol
            technical: Pre-computed technical analysis (optional)

        Returns:
            ScalpingSignal with entry details if valid
        """
        if len(candles) < 20:
            return ScalpingSignal(is_valid=False, reason="Not enough data")

        # 1. Check spread
        spread = price.get("spread_pips", 999)
        if spread > self.config.max_spread_pips:
            return ScalpingSignal(
                is_valid=False,
                reason=f"Spread too high: {spread:.1f} > {self.config.max_spread_pips}"
            )

        # 2. Check volatility (ATR)
        if technical and technical.atr_pips < self.config.min_atr_pips:
            return ScalpingSignal(
                is_valid=False,
                reason=f"ATR too low: {technical.atr_pips:.1f} < {self.config.min_atr_pips}"
            )

        # 3. Detect scalping patterns
        patterns = []
        direction = None
        confidence_boost = 0

        # Pattern: Pullback to EMA in trend
        if technical:
            if self._is_pullback_to_ema(candles, technical):
                patterns.append("PULLBACK_TO_EMA")
                direction = "LONG" if technical.trend == "BULLISH" else "SHORT"
                confidence_boost += 5

        # Pattern: RSI divergence
        rsi_div = self._check_rsi_divergence(candles)
        if rsi_div:
            patterns.append(f"RSI_DIVERGENCE_{rsi_div}")
            direction = "LONG" if rsi_div == "BULLISH" else "SHORT"
            confidence_boost += 10

        # Pattern: Support/Resistance bounce
        if technical:
            sr_bounce = self._check_sr_bounce(candles, price, technical)
            if sr_bounce:
                patterns.append(f"SR_BOUNCE_{sr_bounce}")
                direction = sr_bounce
                confidence_boost += 8

        # Pattern: Momentum shift
        momentum = self._check_momentum_shift(candles)
        if momentum:
            patterns.append(f"MOMENTUM_{momentum}")
            if direction is None:
                direction = momentum
            confidence_boost += 5

        # No patterns found
        if not patterns or direction is None:
            return ScalpingSignal(
                is_valid=False,
                reason="No scalping patterns detected"
            )

        # 4. Calculate entry, SL, TP
        pip_value = 0.0001 if "JPY" not in instrument else 0.01

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
            reason=f"Scalping opportunity: {', '.join(patterns)}",
            patterns=patterns
        )

    def _is_pullback_to_ema(
        self,
        candles: List[Dict],
        technical: TechnicalAnalysis
    ) -> bool:
        """Check if price is pulling back to EMA in a trend."""
        if technical.trend == "RANGING":
            return False

        # Get last few candles
        recent = candles[-5:]
        if not recent:
            return False

        # Current close
        current_close = recent[-1].get("close", 0)
        ema20 = technical.ema20

        # Check if close is near EMA20 (within 0.1%)
        distance_percent = abs(current_close - ema20) / ema20 * 100
        is_near_ema = distance_percent < 0.1

        # In uptrend, we want close slightly above or touching EMA
        if technical.trend == "BULLISH":
            return is_near_ema and current_close >= ema20

        # In downtrend, we want close slightly below or touching EMA
        if technical.trend == "BEARISH":
            return is_near_ema and current_close <= ema20

        return False

    def _check_rsi_divergence(self, candles: List[Dict]) -> Optional[str]:
        """
        Check for RSI divergence.

        Bullish divergence: Price makes lower low, RSI makes higher low
        Bearish divergence: Price makes higher high, RSI makes lower high

        Returns:
            "BULLISH", "BEARISH", or None
        """
        if len(candles) < 20:
            return None

        import pandas as pd
        import pandas_ta as ta

        # Create DataFrame for RSI calculation
        df = pd.DataFrame(candles[-30:])
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df['rsi'] = ta.rsi(df['close'], length=14)
        if df['rsi'].isna().all():
            return None

        closes = df['close'].values
        rsi_values = df['rsi'].values

        # Find swing lows in price (5-bar pivot)
        price_lows = []
        for i in range(2, len(closes) - 2):
            if closes[i] < closes[i-1] and closes[i] < closes[i-2] and \
               closes[i] < closes[i+1] and closes[i] < closes[i+2]:
                price_lows.append((i, closes[i], rsi_values[i]))

        # Find swing highs in price (5-bar pivot)
        price_highs = []
        for i in range(2, len(closes) - 2):
            if closes[i] > closes[i-1] and closes[i] > closes[i-2] and \
               closes[i] > closes[i+1] and closes[i] > closes[i+2]:
                price_highs.append((i, closes[i], rsi_values[i]))

        # Check for bullish divergence (need at least 2 swing lows)
        if len(price_lows) >= 2:
            # Compare last two swing lows
            prev_idx, prev_price, prev_rsi = price_lows[-2]
            curr_idx, curr_price, curr_rsi = price_lows[-1]

            # Bullish: Price lower low, RSI higher low
            if curr_price < prev_price and curr_rsi > prev_rsi:
                # RSI must not be None/NaN
                if pd.notna(curr_rsi) and pd.notna(prev_rsi):
                    return "BULLISH"

        # Check for bearish divergence (need at least 2 swing highs)
        if len(price_highs) >= 2:
            # Compare last two swing highs
            prev_idx, prev_price, prev_rsi = price_highs[-2]
            curr_idx, curr_price, curr_rsi = price_highs[-1]

            # Bearish: Price higher high, RSI lower high
            if curr_price > prev_price and curr_rsi < prev_rsi:
                if pd.notna(curr_rsi) and pd.notna(prev_rsi):
                    return "BEARISH"

        return None

    def _check_sr_bounce(
        self,
        candles: List[Dict],
        price: Dict,
        technical: TechnicalAnalysis
    ) -> Optional[str]:
        """
        Check for bounce off support/resistance.

        Returns:
            "LONG" (bounce off support), "SHORT" (bounce off resistance), or None
        """
        if not technical.nearest_support or not technical.nearest_resistance:
            return None

        current = price.get("bid", 0)

        # Check proximity to support (within 0.05%)
        support_distance = abs(current - technical.nearest_support) / current * 100
        if support_distance < 0.05:
            # Near support - potential long
            return "LONG"

        # Check proximity to resistance
        resistance_distance = abs(current - technical.nearest_resistance) / current * 100
        if resistance_distance < 0.05:
            # Near resistance - potential short
            return "SHORT"

        return None

    def _check_momentum_shift(self, candles: List[Dict]) -> Optional[str]:
        """
        Check for momentum shift using candlestick patterns.

        Returns:
            "LONG", "SHORT", or None
        """
        if len(candles) < 3:
            return None

        # Get last 3 candles
        c1, c2, c3 = candles[-3:]

        # Bullish engulfing pattern
        if self._is_bullish_engulfing(c2, c3):
            return "LONG"

        # Bearish engulfing pattern
        if self._is_bearish_engulfing(c2, c3):
            return "SHORT"

        # Hammer (bullish reversal)
        if self._is_hammer(c3):
            return "LONG"

        # Shooting star (bearish reversal)
        if self._is_shooting_star(c3):
            return "SHORT"

        return None

    def _is_bullish_engulfing(self, prev: Dict, curr: Dict) -> bool:
        """Check for bullish engulfing pattern."""
        prev_open = prev.get("open", 0)
        prev_close = prev.get("close", 0)
        curr_open = curr.get("open", 0)
        curr_close = curr.get("close", 0)

        # Previous candle is bearish
        prev_bearish = prev_close < prev_open

        # Current candle is bullish and engulfs previous
        curr_bullish = curr_close > curr_open
        engulfs = curr_open <= prev_close and curr_close >= prev_open

        return prev_bearish and curr_bullish and engulfs

    def _is_bearish_engulfing(self, prev: Dict, curr: Dict) -> bool:
        """Check for bearish engulfing pattern."""
        prev_open = prev.get("open", 0)
        prev_close = prev.get("close", 0)
        curr_open = curr.get("open", 0)
        curr_close = curr.get("close", 0)

        # Previous candle is bullish
        prev_bullish = prev_close > prev_open

        # Current candle is bearish and engulfs previous
        curr_bearish = curr_close < curr_open
        engulfs = curr_open >= prev_close and curr_close <= prev_open

        return prev_bullish and curr_bearish and engulfs

    def _is_hammer(self, candle: Dict) -> bool:
        """Check for hammer pattern (bullish reversal)."""
        o = candle.get("open", 0)
        h = candle.get("high", 0)
        l = candle.get("low", 0)
        c = candle.get("close", 0)

        body = abs(c - o)
        total_range = h - l
        lower_wick = min(o, c) - l

        if total_range == 0:
            return False

        # Hammer: small body, long lower wick
        return (
            body / total_range < 0.3 and
            lower_wick / total_range > 0.6 and
            c >= o  # Bullish close preferred
        )

    def _is_shooting_star(self, candle: Dict) -> bool:
        """Check for shooting star pattern (bearish reversal)."""
        o = candle.get("open", 0)
        h = candle.get("high", 0)
        l = candle.get("low", 0)
        c = candle.get("close", 0)

        body = abs(c - o)
        total_range = h - l
        upper_wick = h - max(o, c)

        if total_range == 0:
            return False

        # Shooting star: small body, long upper wick
        return (
            body / total_range < 0.3 and
            upper_wick / total_range > 0.6 and
            c <= o  # Bearish close preferred
        )

    def validate_entry_timing(self, instrument: str) -> tuple[bool, str]:
        """
        Validate if it's a good time for scalping entry.

        Returns:
            (is_valid, reason)
        """
        now = datetime.now(timezone.utc)

        # Check session
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

        # Avoid first/last 30 minutes of major sessions
        minute = now.minute

        # London open (7-7:30 UTC)
        if hour == 7 and minute < 30:
            return False, "First 30 min of London session"

        # NY open (12-12:30 UTC / 13-13:30 UTC)
        if hour in [12, 13] and minute < 30:
            return False, "First 30 min of NY session"

        return True, "OK"

    def get_scalping_stats(self) -> dict:
        """Get scalping configuration summary."""
        return {
            "max_sl_pips": self.config.max_sl_pips,
            "target_rr": self.config.target_rr,
            "max_hold_minutes": self.config.max_hold_minutes,
            "max_spread_pips": self.config.max_spread_pips,
            "min_atr_pips": self.config.min_atr_pips,
            "preferred_sessions": self.config.preferred_sessions
        }
