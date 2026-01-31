"""
MetaTrader 5 Python Client.

Handles all communication with MT5 terminal.
Drop-in replacement for OandaClient with identical interface.

Usage:
    from src.trading.mt5_client import MT5Client

    client = MT5Client()
    price = client.get_price("EUR_USD")
    account = client.get_account()
    candles = client.get_candles("EUR_USD", "H1", 100)
"""

from typing import Optional
from datetime import datetime, timezone
import MetaTrader5 as mt5

from src.utils.config import config
from src.utils.logger import logger


class MT5Error(Exception):
    """Custom exception for MT5 API errors."""
    pass


class MT5Client:
    """
    MetaTrader 5 API wrapper.

    Provides methods for:
    - Account info
    - Price fetching
    - Candle data (OHLC)
    - Position management

    Interface matches OandaClient for drop-in replacement.
    """

    # Symbol mapping: OANDA format -> MT5 TMS format
    SYMBOL_MAP = {
        "EUR_USD": "EURUSD.pro",
        "GBP_USD": "GBPUSD.pro",
        "USD_JPY": "USDJPY.pro",
        "AUD_USD": "AUDUSD.pro",
        "USD_CHF": "USDCHF.pro",
        "NZD_USD": "NZDUSD.pro",
        "USD_CAD": "USDCAD.pro",
        "EUR_GBP": "EURGBP.pro",
        "EUR_JPY": "EURJPY.pro",
        "GBP_JPY": "GBPJPY.pro",
        # Crypto (no .pro suffix)
        "BTC_USD": "BTCUSD",
    }

    # Reverse mapping: MT5 -> OANDA format
    SYMBOL_MAP_REVERSE = {v: k for k, v in SYMBOL_MAP.items()}

    # Timeframe mapping: OANDA format -> MT5 constant
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
        "MN": mt5.TIMEFRAME_MN1,
        "MN1": mt5.TIMEFRAME_MN1,
    }

    def __init__(self):
        """Initialize client and connect to MT5."""
        self._connected = False
        self._connect()

    def _connect(self) -> bool:
        """
        Initialize MT5 connection.

        Returns:
            True if connected successfully
        """
        # Validate configuration
        is_valid, error_msg = config.validate_mt5()
        if not is_valid:
            logger.warning(f"MT5 client initialized without valid credentials: {error_msg}")
            return False

        # Initialize MT5
        if not mt5.initialize():
            error = mt5.last_error()
            logger.error(f"MT5 initialize failed: {error}")
            return False

        # Check if already logged in to correct account
        account_info = mt5.account_info()
        if account_info and account_info.login == config.MT5_LOGIN:
            self._connected = True
            logger.info(f"MT5 already connected to account {account_info.login}")
            return True

        # Not logged in or wrong account - try to login
        login = config.MT5_LOGIN
        password = config.MT5_PASSWORD
        server = config.MT5_SERVER

        if not mt5.login(login, password=password, server=server):
            error = mt5.last_error()
            logger.error(f"MT5 login failed: {error}")
            # Check if we're connected anyway (MT5 might already be logged in)
            account_info = mt5.account_info()
            if account_info:
                self._connected = True
                logger.info(f"MT5 connected to account {account_info.login} (already logged in)")
                return True
            mt5.shutdown()
            return False

        self._connected = True
        logger.info(f"MT5 connected to account {login} on {server}")
        return True

    def _convert_symbol(self, instrument: str) -> str:
        """
        Convert OANDA instrument format to MT5 symbol.

        Args:
            instrument: OANDA format (e.g., "EUR_USD")

        Returns:
            MT5 format (e.g., "EURUSD.pro")
        """
        # If already in MT5 format, return as-is
        if ".pro" in instrument:
            return instrument

        # Convert from OANDA format
        if instrument in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[instrument]

        # Try automatic conversion: EUR_USD -> EURUSD.pro
        base_symbol = instrument.replace("_", "")
        return f"{base_symbol}.pro"

    def _convert_symbol_reverse(self, symbol: str) -> str:
        """
        Convert MT5 symbol to OANDA instrument format.

        Args:
            symbol: MT5 format (e.g., "EURUSD.pro")

        Returns:
            OANDA format (e.g., "EUR_USD")
        """
        if symbol in self.SYMBOL_MAP_REVERSE:
            return self.SYMBOL_MAP_REVERSE[symbol]

        # Try automatic conversion: EURUSD.pro -> EUR_USD
        base = symbol.replace(".pro", "")
        if len(base) == 6:
            return f"{base[:3]}_{base[3:]}"
        return symbol

    def _convert_timeframe(self, granularity: str) -> int:
        """
        Convert OANDA granularity to MT5 timeframe.

        Args:
            granularity: OANDA format (e.g., "H1", "D")

        Returns:
            MT5 timeframe constant
        """
        tf = self.TIMEFRAME_MAP.get(granularity.upper())
        if tf is None:
            logger.warning(f"Unknown timeframe {granularity}, defaulting to H1")
            return mt5.TIMEFRAME_H1
        return tf

    # ===================
    # Account Methods
    # ===================

    def get_account(self) -> dict:
        """
        Get account information.

        Returns:
            Dict with account details:
            - id: Account ID
            - balance: Current balance
            - currency: Account currency
            - margin_available: Available margin
            - margin_used: Used margin
            - open_position_count: Number of open positions
            - unrealized_pl: Unrealized P/L
            - nav: Equity (NAV)
        """
        if not self._connected:
            raise MT5Error("Not connected to MT5")

        account_info = mt5.account_info()
        if account_info is None:
            error = mt5.last_error()
            raise MT5Error(f"Failed to get account info: {error}")

        # Count open positions
        positions = mt5.positions_get()
        position_count = len(positions) if positions else 0

        return {
            "id": str(account_info.login),
            "balance": account_info.balance,
            "currency": account_info.currency,
            "margin_available": account_info.margin_free,
            "margin_used": account_info.margin,
            "open_position_count": position_count,
            "open_trade_count": position_count,
            "unrealized_pl": account_info.profit,
            "nav": account_info.equity
        }

    def get_account_summary(self) -> dict:
        """Get account summary (same as get_account for MT5)."""
        return self.get_account()

    # ===================
    # Price Methods
    # ===================

    def get_price(self, instrument: str) -> dict:
        """
        Get current price for an instrument.

        Args:
            instrument: Currency pair (e.g., "EUR_USD" or "EURUSD.pro")

        Returns:
            Dict with price info:
            - instrument: Pair name (OANDA format)
            - bid: Bid price
            - ask: Ask price
            - spread: Spread in price units
            - spread_pips: Spread in pips
            - tradeable: Whether pair is tradeable
            - time: Price timestamp
        """
        if not self._connected:
            raise MT5Error("Not connected to MT5")

        symbol = self._convert_symbol(instrument)

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            error = mt5.last_error()
            raise MT5Error(f"No price data for {symbol}: {error}")

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            raise MT5Error(f"Symbol info not found for {symbol}")

        bid = tick.bid
        ask = tick.ask
        spread = ask - bid

        # Calculate spread in pips
        oanda_instrument = self._convert_symbol_reverse(symbol)
        # Crypto uses direct dollar value, JPY has 2 decimals, standard forex has 4
        if "BTC" in oanda_instrument or "ETH" in oanda_instrument:
            pip_multiplier = 1  # Spread already in USD
        elif "JPY" in oanda_instrument:
            pip_multiplier = 100
        else:
            pip_multiplier = 10000
        spread_pips = spread * pip_multiplier

        # Convert timestamp
        time_str = datetime.fromtimestamp(tick.time, tz=timezone.utc).isoformat()

        return {
            "instrument": oanda_instrument,
            "bid": bid,
            "ask": ask,
            "spread": spread,
            "spread_pips": round(spread_pips, 1),
            "tradeable": symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL,
            "time": time_str
        }

    def get_prices(self, instruments: list[str]) -> list[dict]:
        """
        Get prices for multiple instruments.

        Args:
            instruments: List of currency pairs

        Returns:
            List of price dicts
        """
        results = []
        for instrument in instruments:
            try:
                price = self.get_price(instrument)
                results.append(price)
            except MT5Error as e:
                logger.warning(f"Failed to get price for {instrument}: {e}")
        return results

    # ===================
    # Candle Methods
    # ===================

    def get_candles(
        self,
        instrument: str,
        granularity: str = "H1",
        count: int = 100,
        price: str = "M"
    ) -> list[dict]:
        """
        Get OHLC candle data.

        Args:
            instrument: Currency pair (e.g., "EUR_USD")
            granularity: Timeframe (M1, M5, M15, M30, H1, H4, D, W, M)
            count: Number of candles (max 5000)
            price: Price type - M (mid), B (bid), A (ask) - MT5 uses bid by default

        Returns:
            List of candle dicts with:
            - time: Candle timestamp
            - open: Open price
            - high: High price
            - low: Low price
            - close: Close price
            - volume: Tick volume
            - complete: Whether candle is complete
        """
        if not self._connected:
            raise MT5Error("Not connected to MT5")

        symbol = self._convert_symbol(instrument)
        timeframe = self._convert_timeframe(granularity)

        # Get candles from MT5
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, min(count, 5000))

        if rates is None or len(rates) == 0:
            error = mt5.last_error()
            raise MT5Error(f"Failed to get candles for {symbol}: {error}")

        candles = []
        for i, rate in enumerate(rates):
            # Convert timestamp to ISO format
            time_str = datetime.fromtimestamp(rate['time'], tz=timezone.utc).isoformat()

            # Last candle is incomplete
            is_complete = i < len(rates) - 1

            candles.append({
                "time": time_str,
                "open": float(rate['open']),
                "high": float(rate['high']),
                "low": float(rate['low']),
                "close": float(rate['close']),
                "volume": int(rate['tick_volume']),
                "complete": is_complete
            })

        return candles

    # ===================
    # Position Methods
    # ===================

    def get_positions(self) -> list[dict]:
        """
        Get all open positions.

        Returns:
            List of position dicts
        """
        if not self._connected:
            raise MT5Error("Not connected to MT5")

        positions = mt5.positions_get()

        if positions is None:
            return []

        result = []
        for pos in positions:
            instrument = self._convert_symbol_reverse(pos.symbol)
            is_long = pos.type == mt5.ORDER_TYPE_BUY

            result.append({
                "instrument": instrument,
                "long_units": int(pos.volume * 100000) if is_long else 0,
                "short_units": int(pos.volume * 100000) if not is_long else 0,
                "unrealized_pl": pos.profit,
                "direction": "LONG" if is_long else "SHORT",
                "ticket": pos.ticket,
                "price_open": pos.price_open,
                "price_current": pos.price_current,
                "sl": pos.sl,
                "tp": pos.tp,
                "volume": pos.volume
            })

        return result

    # ===================
    # Utility Methods
    # ===================

    def is_connected(self) -> bool:
        """
        Check if MT5 connection is working.

        Returns:
            True if connected, False otherwise
        """
        if not self._connected:
            return False

        try:
            account = mt5.account_info()
            return account is not None
        except Exception:
            return False

    def validate_instrument(self, instrument: str) -> bool:
        """
        Check if instrument is valid and tradeable.

        Args:
            instrument: Currency pair

        Returns:
            True if valid and tradeable
        """
        if not self._connected:
            return False

        try:
            symbol = self._convert_symbol(instrument)
            info = mt5.symbol_info(symbol)

            if info is None:
                return False

            # Enable symbol in Market Watch if not visible
            if not info.visible:
                mt5.symbol_select(symbol, True)

            return info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL
        except Exception:
            return False

    def shutdown(self):
        """Disconnect from MT5."""
        if self._connected:
            mt5.shutdown()
            self._connected = False
            logger.info("MT5 connection closed")

    def __del__(self):
        """Cleanup on destruction."""
        self.shutdown()
