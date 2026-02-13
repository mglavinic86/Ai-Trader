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
from datetime import datetime, timezone, timedelta
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
        # Gold
        "XAU_USD": "XAUUSD.pro",
        "XAUUSD": "XAUUSD.pro",
        # Crypto (no .pro suffix)
        "BTC_USD": "BTCUSD",
        "BTCUSD": "BTCUSD",
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
        self._symbol_cache = {}
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
        instrument_upper = instrument.upper()

        # If already in MT5 format, return as-is
        if "." in instrument_upper and "_" not in instrument_upper:
            return instrument

        # Return cached resolved symbol
        cached = self._symbol_cache.get(instrument_upper)
        if cached:
            return cached

        # Candidate symbols (priority order)
        candidates = []
        mapped = self.SYMBOL_MAP.get(instrument_upper)
        if mapped:
            candidates.append(mapped)

        base_symbol = instrument_upper.replace("_", "")
        candidates.extend(
            [
                base_symbol,
                f"{base_symbol}.pro",
                f"{base_symbol}m",
                f"{base_symbol}.m",
                f"{base_symbol}-pro",
                f"{base_symbol}.r",
            ]
        )

        # Special handling for gold symbols across brokers
        if "XAU" in instrument_upper or "GOLD" in instrument_upper:
            candidates.extend(
                [
                    "XAUUSD",
                    "XAUUSD.pro",
                    "XAUUSDm",
                    "XAUUSD.m",
                    "GOLD",
                    "GOLD.pro",
                    "GOLDm",
                    "GOLD.m",
                ]
            )

        # Try explicit candidates first
        for symbol in dict.fromkeys(candidates):
            try:
                info = mt5.symbol_info(symbol)
                if info is not None:
                    if not info.visible:
                        mt5.symbol_select(symbol, True)
                    self._symbol_cache[instrument_upper] = symbol
                    return symbol
            except Exception:
                continue

        # As final fallback, scan Market Watch for close matches (XAU/GOLD)
        if "XAU" in instrument_upper or "GOLD" in instrument_upper:
            try:
                symbols = mt5.symbols_get()
                if symbols:
                    for s in symbols:
                        name = getattr(s, "name", "")
                        upper = name.upper()
                        if "XAUUSD" in upper or "GOLD" in upper:
                            mt5.symbol_select(name, True)
                            self._symbol_cache[instrument_upper] = name
                            logger.info(f"Resolved {instrument_upper} -> {name}")
                            return name
            except Exception:
                pass

        # Last resort to keep legacy behavior
        fallback = mapped if mapped else f"{base_symbol}.pro"
        self._symbol_cache[instrument_upper] = fallback
        return fallback

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

        symbol_upper = symbol.upper()
        if "XAUUSD" in symbol_upper or "GOLD" in symbol_upper:
            return "XAU_USD"

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
        if not self._ensure_connected():
            raise MT5Error("Not connected to MT5 and reconnect failed")

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
        if not self._ensure_connected():
            raise MT5Error("Not connected to MT5 and reconnect failed")

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
        # Crypto uses direct dollar value, metals use 0.01 pip, JPY has 2 decimals, standard forex has 4
        if "BTC" in oanda_instrument or "ETH" in oanda_instrument:
            pip_multiplier = 1  # Spread already in USD
        elif "XAU" in oanda_instrument or "XAG" in oanda_instrument:
            pip_multiplier = 100
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
        if not self._ensure_connected():
            raise MT5Error("Not connected to MT5 and reconnect failed")

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
        if not self._ensure_connected():
            raise MT5Error("Not connected to MT5 and reconnect failed")

        positions = mt5.positions_get()

        if positions is None:
            return []

        result = []
        for pos in positions:
            instrument = self._convert_symbol_reverse(pos.symbol)
            is_long = pos.type == mt5.ORDER_TYPE_BUY
            symbol_info = mt5.symbol_info(pos.symbol)
            contract_size = getattr(symbol_info, "trade_contract_size", 100000.0) if symbol_info else 100000.0

            result.append({
                "instrument": instrument,
                "long_units": int(pos.volume * contract_size) if is_long else 0,
                "short_units": int(pos.volume * contract_size) if not is_long else 0,
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

    def reconnect(self) -> bool:
        """
        Force reconnection to MT5.

        Use this when MT5 terminal was restarted.

        Returns:
            True if reconnected successfully
        """
        logger.info("Forcing MT5 reconnection...")
        mt5.shutdown()
        self._connected = False
        self._symbol_cache = {}
        return self._connect()

    def _ensure_connected(self) -> bool:
        """
        Ensure MT5 is connected, reconnect if needed.

        Returns:
            True if connected
        """
        if self._connected:
            # Verify connection is still valid
            try:
                account = mt5.account_info()
                if account is not None:
                    return True
            except Exception:
                pass

        # Connection lost, try to reconnect
        logger.warning("MT5 connection lost, attempting reconnect...")
        return self.reconnect()

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

    # ===================
    # History Methods
    # ===================

    def get_history(
        self,
        days: int = 30,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> list[dict]:
        """
        Get closed trade history from MT5.

        Fetches deals from MT5 history and groups them into complete trades
        (entry + exit). Each returned trade represents a fully closed position.

        Args:
            days: Number of days to fetch (default 30)
            from_date: Start date (overrides days if provided)
            to_date: End date (defaults to now)

        Returns:
            List of closed trade dicts with:
            - trade_id: MT5 position ticket (string)
            - instrument: Currency pair (OANDA format)
            - direction: LONG or SHORT
            - entry_price: Entry price
            - exit_price: Exit price
            - units: Position size
            - volume: Lot size
            - pnl: Realized P/L
            - pnl_percent: P/L as percentage of entry value
            - opened_at: Entry timestamp (ISO format)
            - closed_at: Exit timestamp (ISO format)
            - stop_loss: SL price if set
            - take_profit: TP price if set
            - commission: Total commission
            - swap: Swap charges
            - comment: Trade comment
        """
        if not self._ensure_connected():
            raise MT5Error("Not connected to MT5 and reconnect failed")

        # Set date range
        explicit_from_date = from_date is not None
        if to_date is None:
            # MT5 server timestamps can be slightly ahead of local UTC clock.
            # Add a forward buffer so freshly closed deals are not missed.
            to_date = datetime.now(timezone.utc) + timedelta(hours=6)
        if from_date is None:
            from_date = to_date - timedelta(days=days)

        # Ensure timezone aware
        if from_date.tzinfo is None:
            from_date = from_date.replace(tzinfo=timezone.utc)
        if to_date.tzinfo is None:
            to_date = to_date.replace(tzinfo=timezone.utc)

        # Fetch deals from MT5 (with widening lookback fallback for short windows).
        def _fetch_deals(_from: datetime, _to: datetime):
            try:
                return mt5.history_deals_get(_from, _to)
            except Exception:
                return None

        deals = _fetch_deals(from_date, to_date)
        if (deals is None or len(deals) == 0) and not explicit_from_date:
            # When caller asks for short history windows, MT5 can lag in recent-deal visibility.
            # Widen the range progressively so we still reconcile recently closed trades.
            fallback_days = []
            for d in (3, 7, 30):
                if d > int(days):
                    fallback_days.append(d)
            for fb_days in fallback_days:
                fb_from = to_date - timedelta(days=fb_days)
                deals = _fetch_deals(fb_from, to_date)
                if deals and len(deals) > 0:
                    logger.info(f"MT5 history fallback succeeded with {fb_days}d window")
                    break

        if deals is None or len(deals) == 0:
            logger.info("No trade history found in MT5")
            return []

        # Group deals by position_id
        # Each position has entry deal(s) and exit deal(s)
        positions = {}

        for deal in deals:
            pos_id = deal.position_id
            if pos_id == 0:
                # Skip balance operations, deposits, etc.
                continue

            if pos_id not in positions:
                positions[pos_id] = {
                    "entries": [],
                    "exits": [],
                    "symbol": deal.symbol,
                    "commission": 0.0,
                    "swap": 0.0,
                    "comment": deal.comment or ""
                }

            # DEAL_ENTRY_IN = 0 (entry), DEAL_ENTRY_OUT = 1 (exit)
            if deal.entry == 0:  # Entry
                positions[pos_id]["entries"].append(deal)
            elif deal.entry == 1:  # Exit
                positions[pos_id]["exits"].append(deal)

            positions[pos_id]["commission"] += deal.commission
            positions[pos_id]["swap"] += deal.swap

        # Build closed trades list
        closed_trades = []

        for pos_id, pos_data in positions.items():
            if not pos_data["entries"] or not pos_data["exits"]:
                # Position not fully closed yet
                continue

            # Calculate weighted average entry price
            total_entry_volume = sum(d.volume for d in pos_data["entries"])
            if total_entry_volume == 0:
                continue

            entry_price = sum(d.price * d.volume for d in pos_data["entries"]) / total_entry_volume

            # Calculate weighted average exit price
            total_exit_volume = sum(d.volume for d in pos_data["exits"])
            exit_price = sum(d.price * d.volume for d in pos_data["exits"]) / total_exit_volume if total_exit_volume > 0 else 0

            # Get first entry and last exit for timestamps
            first_entry = min(pos_data["entries"], key=lambda d: d.time)
            last_exit = max(pos_data["exits"], key=lambda d: d.time)

            # Determine direction from first entry deal type
            # DEAL_TYPE_BUY = 0, DEAL_TYPE_SELL = 1
            is_long = first_entry.type == 0

            # Calculate P/L (sum of all deal profits)
            total_pnl = sum(d.profit for d in pos_data["exits"])
            total_pnl += pos_data["commission"] + pos_data["swap"]

            # Convert symbol
            instrument = self._convert_symbol_reverse(pos_data["symbol"])

            # Get symbol info for contract size
            symbol_info = mt5.symbol_info(pos_data["symbol"])
            contract_size = getattr(symbol_info, "trade_contract_size", 100000.0) if symbol_info else 100000.0
            units = int(total_entry_volume * contract_size)
            if not is_long:
                units = -units

            # Calculate P/L percent (relative to position value)
            position_value = abs(units) * entry_price
            pnl_percent = (total_pnl / position_value * 100) if position_value > 0 else 0

            closed_trades.append({
                "trade_id": str(pos_id),
                "instrument": instrument,
                "direction": "LONG" if is_long else "SHORT",
                "entry_price": round(entry_price, 5),
                "exit_price": round(exit_price, 5),
                "units": units,
                "volume": round(total_entry_volume, 2),
                "pnl": round(total_pnl, 2),
                "pnl_percent": round(pnl_percent, 4),
                "opened_at": datetime.fromtimestamp(first_entry.time, tz=timezone.utc).isoformat(),
                "closed_at": datetime.fromtimestamp(last_exit.time, tz=timezone.utc).isoformat(),
                "stop_loss": None,  # Not available in deal history
                "take_profit": None,
                "commission": round(pos_data["commission"], 2),
                "swap": round(pos_data["swap"], 2),
                "comment": pos_data["comment"],
                "source": "MT5_SYNC"
            })

        # Sort by close time
        closed_trades.sort(key=lambda t: t["closed_at"])

        logger.info(f"Found {len(closed_trades)} closed trades in MT5 history")
        return closed_trades

    def get_closed_trade_by_position(
        self,
        position_id: int | str,
        days: int = 30,
    ) -> Optional[dict]:
        """
        Fetch one closed trade by MT5 position_id.

        Useful for reconciling DB rows that were closed without P/L when
        generic history queries missed a fresh close deal.
        """
        if not self._ensure_connected():
            raise MT5Error("Not connected to MT5 and reconnect failed")

        try:
            pos_id = int(position_id)
        except Exception:
            return None

        # See get_history(): include forward buffer for broker/server clock skew.
        to_date = datetime.now(timezone.utc) + timedelta(hours=6)
        from_date = to_date - timedelta(days=days)

        deals = mt5.history_deals_get(from_date, to_date, position=pos_id)
        if not deals:
            return None
        deals = [d for d in deals if int(getattr(d, "position_id", 0) or 0) == pos_id]
        if not deals:
            return None

        entries = []
        exits = []
        symbol = None
        commission = 0.0
        swap = 0.0
        comment = ""

        for deal in deals:
            if symbol is None:
                symbol = deal.symbol
                comment = deal.comment or ""
            commission += float(getattr(deal, "commission", 0.0) or 0.0)
            swap += float(getattr(deal, "swap", 0.0) or 0.0)
            if deal.entry == mt5.DEAL_ENTRY_IN:
                entries.append(deal)
            elif deal.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY):
                exits.append(deal)

        # No exit deal -> position is likely still open.
        if not exits:
            return None

        total_exit_volume = sum(float(d.volume) for d in exits)
        if total_exit_volume <= 0:
            return None

        # Entry may occasionally be missing from sliced history; infer fallback values.
        if entries:
            total_entry_volume = sum(float(d.volume) for d in entries) or total_exit_volume
            entry_price = sum(float(d.price) * float(d.volume) for d in entries) / total_entry_volume
            first_entry = min(entries, key=lambda d: d.time)
            is_long = first_entry.type == mt5.DEAL_TYPE_BUY
            opened_at = datetime.fromtimestamp(first_entry.time, tz=timezone.utc).isoformat()
        else:
            # Infer direction from exit type:
            # exiting LONG uses SELL deal, exiting SHORT uses BUY deal.
            first_exit = min(exits, key=lambda d: d.time)
            is_long = first_exit.type == mt5.DEAL_TYPE_SELL
            entry_price = float(first_exit.price)
            opened_at = datetime.fromtimestamp(first_exit.time, tz=timezone.utc).isoformat()

        exit_price = sum(float(d.price) * float(d.volume) for d in exits) / total_exit_volume
        last_exit = max(exits, key=lambda d: d.time)
        closed_at = datetime.fromtimestamp(last_exit.time, tz=timezone.utc).isoformat()

        total_pnl = sum(float(getattr(d, "profit", 0.0) or 0.0) for d in exits) + commission + swap

        symbol_info = mt5.symbol_info(symbol) if symbol else None
        contract_size = getattr(symbol_info, "trade_contract_size", 100000.0) if symbol_info else 100000.0
        units = int(total_exit_volume * float(contract_size))
        if not is_long:
            units = -units

        position_value = abs(units) * float(entry_price)
        pnl_percent = (float(total_pnl) / position_value * 100.0) if position_value > 0 else 0.0

        instrument = self._convert_symbol_reverse(symbol) if symbol else str(position_id)
        return {
            "trade_id": str(pos_id),
            "instrument": instrument,
            "direction": "LONG" if is_long else "SHORT",
            "entry_price": round(float(entry_price), 5),
            "exit_price": round(float(exit_price), 5),
            "units": units,
            "volume": round(float(total_exit_volume), 2),
            "pnl": round(float(total_pnl), 2),
            "pnl_percent": round(float(pnl_percent), 4),
            "opened_at": opened_at,
            "closed_at": closed_at,
            "stop_loss": None,
            "take_profit": None,
            "commission": round(float(commission), 2),
            "swap": round(float(swap), 2),
            "comment": comment,
            "source": "MT5_SYNC_RECON",
        }

    def shutdown(self):
        """Disconnect from MT5."""
        if self._connected:
            mt5.shutdown()
            self._connected = False
            logger.info("MT5 connection closed")

    def __del__(self):
        """Cleanup on destruction."""
        self.shutdown()
