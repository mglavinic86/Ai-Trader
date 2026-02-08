"""
Historical Data Loader with Chunking Support

MT5 has a limit of ~5000 candles per request.
DataLoader automatically splits large date ranges into chunks.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import MetaTrader5 as mt5


@dataclass
class HistoricalDataRequest:
    """Request parameters for historical data."""
    instrument: str  # OANDA format: EUR_USD
    timeframe: str  # M1, M5, M15, M30, H1, H4, D
    start_date: datetime
    end_date: datetime

    def __post_init__(self):
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")


@dataclass
class HistoricalData:
    """Container for historical candle data."""
    instrument: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    candles: list[dict] = field(default_factory=list)

    @property
    def total_bars(self) -> int:
        return len(self.candles)

    @property
    def date_range_str(self) -> str:
        return f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"


class DataLoader:
    """
    Loads historical data from MT5 with automatic chunking.

    MT5 limits requests to ~5000 bars, so large date ranges
    are automatically split into multiple requests.
    """

    MAX_BARS_PER_REQUEST = 5000

    SYMBOL_MAP = {
        "EUR_USD": "EURUSD.pro",
        "GBP_USD": "GBPUSD.pro",
        "USD_JPY": "USDJPY.pro",
        "USD_CHF": "USDCHF.pro",
        "AUD_USD": "AUDUSD.pro",
        "USD_CAD": "USDCAD.pro",
        "NZD_USD": "NZDUSD.pro",
        "EUR_GBP": "EURGBP.pro",
        "EUR_JPY": "EURJPY.pro",
        "GBP_JPY": "GBPJPY.pro",
        # Commodities
        "XAU_USD": "GOLD.pro",
        # Crypto (no .pro suffix)
        "BTC_USD": "BTCUSD",
    }

    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D": mt5.TIMEFRAME_D1,
        "D1": mt5.TIMEFRAME_D1,
        "W": mt5.TIMEFRAME_W1,
        "W1": mt5.TIMEFRAME_W1,
    }

    # Approximate bars per day for each timeframe
    BARS_PER_DAY = {
        "M1": 1440,
        "M5": 288,
        "M15": 96,
        "M30": 48,
        "H1": 24,
        "H4": 6,
        "D": 1,
        "D1": 1,
        "W": 0.2,
        "W1": 0.2,
    }

    def __init__(self):
        self._ensure_mt5_connected()

    def _ensure_mt5_connected(self) -> None:
        """Ensure MT5 is initialized."""
        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")

    def _get_mt5_symbol(self, instrument: str) -> str:
        """Convert OANDA symbol to MT5 symbol."""
        if instrument in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[instrument]
        # Try direct mapping
        return instrument.replace("_", "") + ".pro"

    def _get_mt5_timeframe(self, timeframe: str) -> int:
        """Convert timeframe string to MT5 constant."""
        tf = timeframe.upper()
        if tf not in self.TIMEFRAME_MAP:
            raise ValueError(f"Unknown timeframe: {timeframe}")
        return self.TIMEFRAME_MAP[tf]

    def _estimate_bars(self, start: datetime, end: datetime, timeframe: str) -> int:
        """Estimate number of bars in date range."""
        days = (end - start).days
        bars_per_day = self.BARS_PER_DAY.get(timeframe.upper(), 24)
        # Account for weekends (forex market closed)
        trading_days = days * 5 / 7
        return int(trading_days * bars_per_day)

    def _calculate_chunks(
        self,
        start: datetime,
        end: datetime,
        timeframe: str
    ) -> list[tuple[datetime, datetime]]:
        """
        Split date range into chunks that stay under MT5 limit.

        Returns list of (start, end) tuples for each chunk.
        """
        estimated_bars = self._estimate_bars(start, end, timeframe)

        if estimated_bars <= self.MAX_BARS_PER_REQUEST:
            return [(start, end)]

        # Calculate chunk size in days
        bars_per_day = self.BARS_PER_DAY.get(timeframe.upper(), 24)
        days_per_chunk = int((self.MAX_BARS_PER_REQUEST / bars_per_day) * 7 / 5)  # Account for weekends
        days_per_chunk = max(1, days_per_chunk)

        chunks = []
        chunk_start = start

        while chunk_start < end:
            chunk_end = min(chunk_start + timedelta(days=days_per_chunk), end)
            chunks.append((chunk_start, chunk_end))
            chunk_start = chunk_end

        return chunks

    def _fetch_chunk(
        self,
        symbol: str,
        timeframe: int,
        start: datetime,
        end: datetime
    ) -> list[dict]:
        """Fetch a single chunk of data from MT5."""
        rates = mt5.copy_rates_range(symbol, timeframe, start, end)

        if rates is None or len(rates) == 0:
            return []

        candles = []
        for rate in rates:
            candles.append({
                "time": datetime.fromtimestamp(rate["time"]).isoformat(),
                "timestamp": rate["time"],
                "open": float(rate["open"]),
                "high": float(rate["high"]),
                "low": float(rate["low"]),
                "close": float(rate["close"]),
                "volume": int(rate["tick_volume"]),
                "complete": True,
            })

        return candles

    def load(
        self,
        request: HistoricalDataRequest,
        progress_callback: Optional[callable] = None
    ) -> HistoricalData:
        """
        Load historical data with automatic chunking.

        Args:
            request: HistoricalDataRequest with parameters
            progress_callback: Optional callback(current, total) for progress

        Returns:
            HistoricalData with all candles
        """
        symbol = self._get_mt5_symbol(request.instrument)
        timeframe = self._get_mt5_timeframe(request.timeframe)

        # Calculate chunks
        chunks = self._calculate_chunks(
            request.start_date,
            request.end_date,
            request.timeframe
        )

        all_candles = []

        for i, (chunk_start, chunk_end) in enumerate(chunks):
            chunk_candles = self._fetch_chunk(symbol, timeframe, chunk_start, chunk_end)
            all_candles.extend(chunk_candles)

            if progress_callback:
                progress_callback(i + 1, len(chunks))

        # Remove duplicates (overlapping chunk boundaries)
        seen_times = set()
        unique_candles = []
        for candle in all_candles:
            if candle["timestamp"] not in seen_times:
                seen_times.add(candle["timestamp"])
                unique_candles.append(candle)

        # Sort by time
        unique_candles.sort(key=lambda x: x["timestamp"])

        return HistoricalData(
            instrument=request.instrument,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
            candles=unique_candles
        )

    def load_simple(
        self,
        instrument: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        progress_callback: Optional[callable] = None
    ) -> HistoricalData:
        """
        Simplified load method with direct parameters.
        """
        request = HistoricalDataRequest(
            instrument=instrument,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        return self.load(request, progress_callback)

    def get_available_symbols(self) -> list[str]:
        """Get list of available symbols in OANDA format."""
        return list(self.SYMBOL_MAP.keys())

    def get_available_timeframes(self) -> list[str]:
        """Get list of available timeframes."""
        return ["M1", "M5", "M15", "M30", "H1", "H4", "D"]
