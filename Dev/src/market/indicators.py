"""
Technical Indicators using pandas-ta.

Usage:
    from src.market.indicators import TechnicalAnalyzer

    analyzer = TechnicalAnalyzer()
    result = analyzer.analyze(candles)
"""

import pandas as pd
import pandas_ta as ta
from typing import Optional
from dataclasses import dataclass

from src.utils.logger import logger


@dataclass
class TechnicalAnalysis:
    """Result of technical analysis."""
    # Trend
    trend: str  # BULLISH, BEARISH, RANGING
    trend_strength: float  # 0-100

    # Moving Averages
    ema20: float
    ema50: float
    price_vs_ema20: str  # ABOVE, BELOW

    # RSI
    rsi: float
    rsi_signal: str  # OVERBOUGHT, OVERSOLD, NEUTRAL

    # MACD
    macd: float
    macd_signal: float
    macd_histogram: float
    macd_trend: str  # BULLISH, BEARISH

    # ATR (Volatility)
    atr: float
    atr_pips: float

    # Support/Resistance
    nearest_support: Optional[float]
    nearest_resistance: Optional[float]
    distance_to_support_pips: Optional[float]
    distance_to_resistance_pips: Optional[float]

    # Overall Score
    technical_score: int  # 0-100

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "trend": self.trend,
            "trend_strength": self.trend_strength,
            "ema20": self.ema20,
            "ema50": self.ema50,
            "price_vs_ema20": self.price_vs_ema20,
            "rsi": self.rsi,
            "rsi_signal": self.rsi_signal,
            "macd": self.macd,
            "macd_signal": self.macd_signal,
            "macd_histogram": self.macd_histogram,
            "macd_trend": self.macd_trend,
            "atr": self.atr,
            "atr_pips": self.atr_pips,
            "nearest_support": self.nearest_support,
            "nearest_resistance": self.nearest_resistance,
            "distance_to_support_pips": self.distance_to_support_pips,
            "distance_to_resistance_pips": self.distance_to_resistance_pips,
            "technical_score": self.technical_score
        }

    def format_summary(self) -> str:
        """Format as readable summary."""
        return f"""
📈 TECHNICAL ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━
Trend: {self.trend} (strength: {self.trend_strength:.0f}%)
EMA20: {self.ema20:.5f} | EMA50: {self.ema50:.5f}
Price vs EMA20: {self.price_vs_ema20}

RSI(14): {self.rsi:.1f} - {self.rsi_signal}
MACD: {self.macd_trend} (histogram: {self.macd_histogram:.5f})

ATR(14): {self.atr_pips:.1f} pips

Support: {self.nearest_support:.5f if self.nearest_support else 'N/A'} ({self.distance_to_support_pips:.1f} pips away)
Resistance: {self.nearest_resistance:.5f if self.nearest_resistance else 'N/A'} ({self.distance_to_resistance_pips:.1f} pips away)

Technical Score: {self.technical_score}/100
"""


class TechnicalAnalyzer:
    """Technical analysis using pandas-ta."""

    def __init__(self):
        """Initialize analyzer."""
        pass

    def analyze(self, candles: list[dict], instrument: str = "EUR_USD") -> TechnicalAnalysis:
        """
        Perform technical analysis on candle data.

        Args:
            candles: List of OHLCV dicts from OANDA
            instrument: Currency pair for pip calculation

        Returns:
            TechnicalAnalysis result
        """
        # Convert to DataFrame
        df = pd.DataFrame(candles)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)

        # Ensure numeric types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])

        current_price = df['close'].iloc[-1]
        # Crypto pairs use whole dollar, JPY has 2 decimals, standard forex has 4
        if "BTC" in instrument or "ETH" in instrument:
            pip_value = 1.0
        elif "JPY" in instrument:
            pip_value = 0.01
        else:
            pip_value = 0.0001

        # Calculate indicators
        df['ema20'] = ta.ema(df['close'], length=20)
        df['ema50'] = ta.ema(df['close'], length=50)
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        macd = ta.macd(df['close'])
        if macd is not None:
            df = pd.concat([df, macd], axis=1)

        # Get latest values
        ema20 = df['ema20'].iloc[-1]
        ema50 = df['ema50'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        atr = df['atr'].iloc[-1]

        # MACD values
        macd_val = df['MACD_12_26_9'].iloc[-1] if 'MACD_12_26_9' in df.columns else 0
        macd_signal = df['MACDs_12_26_9'].iloc[-1] if 'MACDs_12_26_9' in df.columns else 0
        macd_hist = df['MACDh_12_26_9'].iloc[-1] if 'MACDh_12_26_9' in df.columns else 0

        # Trend determination
        trend, trend_strength = self._determine_trend(df, ema20, ema50, current_price)

        # RSI signal
        rsi_signal = self._rsi_signal(rsi)

        # MACD trend
        macd_trend = "BULLISH" if macd_hist > 0 else "BEARISH"

        # Price vs EMA20
        price_vs_ema20 = "ABOVE" if current_price > ema20 else "BELOW"

        # ATR in pips
        atr_pips = atr / pip_value

        # Support/Resistance
        support, resistance = self._find_sr_levels(df, current_price)
        dist_support = (current_price - support) / pip_value if support else None
        dist_resistance = (resistance - current_price) / pip_value if resistance else None

        # Calculate overall technical score
        technical_score = self._calculate_score(
            trend, trend_strength, rsi, macd_hist,
            price_vs_ema20, dist_support, dist_resistance
        )

        return TechnicalAnalysis(
            trend=trend,
            trend_strength=trend_strength,
            ema20=ema20,
            ema50=ema50,
            price_vs_ema20=price_vs_ema20,
            rsi=rsi,
            rsi_signal=rsi_signal,
            macd=macd_val,
            macd_signal=macd_signal,
            macd_histogram=macd_hist,
            macd_trend=macd_trend,
            atr=atr,
            atr_pips=atr_pips,
            nearest_support=support,
            nearest_resistance=resistance,
            distance_to_support_pips=dist_support,
            distance_to_resistance_pips=dist_resistance,
            technical_score=technical_score
        )

    def _determine_trend(self, df: pd.DataFrame, ema20: float, ema50: float, price: float) -> tuple[str, float]:
        """Determine trend direction and strength."""
        # Basic trend from EMAs
        if price > ema20 > ema50:
            base_trend = "BULLISH"
            base_strength = 70
        elif price < ema20 < ema50:
            base_trend = "BEARISH"
            base_strength = 70
        elif abs(ema20 - ema50) / ema50 < 0.001:  # EMAs very close
            base_trend = "RANGING"
            base_strength = 30
        else:
            base_trend = "RANGING"
            base_strength = 40

        # Adjust strength based on EMA separation
        ema_separation = abs(ema20 - ema50) / ema50 * 100
        strength_adj = min(ema_separation * 10, 30)

        final_strength = min(base_strength + strength_adj, 100)

        return base_trend, final_strength

    def _rsi_signal(self, rsi: float) -> str:
        """Get RSI signal."""
        if rsi >= 70:
            return "OVERBOUGHT"
        elif rsi <= 30:
            return "OVERSOLD"
        elif rsi >= 60:
            return "BULLISH"
        elif rsi <= 40:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def _find_sr_levels(self, df: pd.DataFrame, current_price: float) -> tuple[Optional[float], Optional[float]]:
        """Find nearest support and resistance levels."""
        # Use recent highs/lows as S/R
        lookback = min(50, len(df))
        recent = df.iloc[-lookback:]

        highs = recent['high'].values
        lows = recent['low'].values

        # Find swing highs (resistance)
        resistances = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                if highs[i] > current_price:
                    resistances.append(highs[i])

        # Find swing lows (support)
        supports = []
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                if lows[i] < current_price:
                    supports.append(lows[i])

        nearest_support = max(supports) if supports else None
        nearest_resistance = min(resistances) if resistances else None

        return nearest_support, nearest_resistance

    def _calculate_score(
        self,
        trend: str,
        trend_strength: float,
        rsi: float,
        macd_hist: float,
        price_vs_ema: str,
        dist_support: Optional[float],
        dist_resistance: Optional[float]
    ) -> int:
        """Calculate overall technical score (0-100)."""
        score = 50  # Start neutral

        # Trend contribution (+/- 20)
        if trend == "BULLISH":
            score += int(trend_strength * 0.2)
        elif trend == "BEARISH":
            score -= int(trend_strength * 0.2)

        # RSI contribution (+/- 15)
        if 40 <= rsi <= 60:
            score += 5  # Neutral is good
        elif 30 <= rsi <= 70:
            score += 10  # Healthy range
        else:
            score -= 10  # Extreme

        # MACD contribution (+/- 10)
        if macd_hist > 0:
            score += 10
        else:
            score -= 5

        # EMA position (+/- 5)
        if price_vs_ema == "ABOVE":
            score += 5
        else:
            score -= 5

        # S/R distance
        if dist_support and dist_support < 20:
            score += 5  # Near support (good for long)
        if dist_resistance and dist_resistance < 20:
            score -= 5  # Near resistance (caution)

        return max(0, min(100, score))


def analyze_candles(candles: list[dict], instrument: str = "EUR_USD") -> TechnicalAnalysis:
    """
    Convenience function for quick analysis.

    Args:
        candles: OHLCV candle data
        instrument: Currency pair

    Returns:
        TechnicalAnalysis result
    """
    analyzer = TechnicalAnalyzer()
    return analyzer.analyze(candles, instrument)
