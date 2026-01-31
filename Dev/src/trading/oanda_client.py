"""
OANDA REST API v20 Client.

Handles all communication with OANDA broker API.

Usage:
    from src.trading.oanda_client import OandaClient

    client = OandaClient()
    price = client.get_price("EUR_USD")
    account = client.get_account()
    candles = client.get_candles("EUR_USD", "H1", 100)
"""

from typing import Optional
from datetime import datetime
import httpx

from src.utils.config import config
from src.utils.logger import logger


class OandaError(Exception):
    """Custom exception for OANDA API errors."""
    pass


class OandaClient:
    """
    OANDA REST API v20 wrapper.

    Provides methods for:
    - Account info
    - Price fetching
    - Candle data (OHLC)
    - Order management (Phase 2)
    """

    def __init__(self):
        """Initialize client with credentials from config."""
        self.api_key = config.OANDA_API_KEY
        self.account_id = config.OANDA_ACCOUNT_ID
        self.base_url = config.OANDA_BASE_URL

        # Validate configuration
        is_valid, error_msg = config.validate()
        if not is_valid:
            logger.warning(f"OANDA client initialized without valid credentials: {error_msg}")

    def _headers(self) -> dict:
        """Get authorization headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept-Datetime-Format": "RFC3339"
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        timeout: float = 10.0
    ) -> dict:
        """
        Make HTTP request to OANDA API.

        Args:
            method: HTTP method (GET, POST, PUT)
            endpoint: API endpoint (e.g., /v3/accounts/{id})
            params: Query parameters
            json_data: JSON body for POST/PUT
            timeout: Request timeout in seconds

        Returns:
            JSON response as dict

        Raises:
            OandaError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    params=params,
                    json=json_data
                )

                # Check for errors
                if response.status_code >= 400:
                    error_body = response.json() if response.text else {}
                    error_msg = error_body.get("errorMessage", response.text)
                    logger.error(f"OANDA API error {response.status_code}: {error_msg}")
                    raise OandaError(f"API error {response.status_code}: {error_msg}")

                return response.json()

        except httpx.TimeoutException:
            logger.error(f"OANDA API timeout: {endpoint}")
            raise OandaError("Request timeout. Check your internet connection.")

        except httpx.RequestError as e:
            logger.error(f"OANDA API request error: {e}")
            raise OandaError(f"Request failed: {e}")

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
            - marginAvailable: Available margin
            - openPositionCount: Number of open positions
            - pl: Unrealized P/L
        """
        endpoint = f"/v3/accounts/{self.account_id}"
        response = self._request("GET", endpoint)

        account = response.get("account", {})

        return {
            "id": account.get("id"),
            "balance": float(account.get("balance", 0)),
            "currency": account.get("currency"),
            "margin_available": float(account.get("marginAvailable", 0)),
            "margin_used": float(account.get("marginUsed", 0)),
            "open_position_count": int(account.get("openPositionCount", 0)),
            "open_trade_count": int(account.get("openTradeCount", 0)),
            "unrealized_pl": float(account.get("unrealizedPL", 0)),
            "nav": float(account.get("NAV", 0))
        }

    def get_account_summary(self) -> dict:
        """Get account summary (lighter than full account info)."""
        endpoint = f"/v3/accounts/{self.account_id}/summary"
        response = self._request("GET", endpoint)
        return response.get("account", {})

    # ===================
    # Price Methods
    # ===================

    def get_price(self, instrument: str) -> dict:
        """
        Get current price for an instrument.

        Args:
            instrument: Currency pair (e.g., "EUR_USD")

        Returns:
            Dict with price info:
            - instrument: Pair name
            - bid: Bid price
            - ask: Ask price
            - spread: Spread in price units
            - spread_pips: Spread in pips
            - tradeable: Whether pair is tradeable
            - time: Price timestamp
        """
        endpoint = f"/v3/accounts/{self.account_id}/pricing"
        params = {"instruments": instrument}

        response = self._request("GET", endpoint, params=params)

        prices = response.get("prices", [])
        if not prices:
            raise OandaError(f"No price data for {instrument}")

        price_data = prices[0]

        bid = float(price_data["bids"][0]["price"])
        ask = float(price_data["asks"][0]["price"])
        spread = ask - bid

        # Calculate spread in pips (assuming 4 decimal places for most pairs)
        pip_multiplier = 10000 if "JPY" not in instrument else 100
        spread_pips = spread * pip_multiplier

        return {
            "instrument": instrument,
            "bid": bid,
            "ask": ask,
            "spread": spread,
            "spread_pips": round(spread_pips, 1),
            "tradeable": price_data.get("tradeable", True),
            "time": price_data.get("time", "")
        }

    def get_prices(self, instruments: list[str]) -> list[dict]:
        """
        Get prices for multiple instruments.

        Args:
            instruments: List of currency pairs

        Returns:
            List of price dicts
        """
        endpoint = f"/v3/accounts/{self.account_id}/pricing"
        params = {"instruments": ",".join(instruments)}

        response = self._request("GET", endpoint, params=params)

        results = []
        for price_data in response.get("prices", []):
            instrument = price_data.get("instrument")
            bid = float(price_data["bids"][0]["price"])
            ask = float(price_data["asks"][0]["price"])
            spread = ask - bid

            pip_multiplier = 10000 if "JPY" not in instrument else 100
            spread_pips = spread * pip_multiplier

            results.append({
                "instrument": instrument,
                "bid": bid,
                "ask": ask,
                "spread": spread,
                "spread_pips": round(spread_pips, 1),
                "tradeable": price_data.get("tradeable", True)
            })

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
            price: Price type - M (mid), B (bid), A (ask)

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
        endpoint = f"/v3/instruments/{instrument}/candles"
        params = {
            "granularity": granularity,
            "count": min(count, 5000),
            "price": price
        }

        response = self._request("GET", endpoint, params=params)

        candles = []
        for candle in response.get("candles", []):
            mid = candle.get("mid", {})
            candles.append({
                "time": candle.get("time"),
                "open": float(mid.get("o", 0)),
                "high": float(mid.get("h", 0)),
                "low": float(mid.get("l", 0)),
                "close": float(mid.get("c", 0)),
                "volume": int(candle.get("volume", 0)),
                "complete": candle.get("complete", False)
            })

        return candles

    # ===================
    # Position Methods (Phase 2)
    # ===================

    def get_positions(self) -> list[dict]:
        """
        Get all open positions.

        Returns:
            List of position dicts
        """
        endpoint = f"/v3/accounts/{self.account_id}/openPositions"
        response = self._request("GET", endpoint)

        positions = []
        for pos in response.get("positions", []):
            long_units = int(pos.get("long", {}).get("units", 0))
            short_units = int(pos.get("short", {}).get("units", 0))

            positions.append({
                "instrument": pos.get("instrument"),
                "long_units": long_units,
                "short_units": abs(short_units),
                "unrealized_pl": float(pos.get("unrealizedPL", 0)),
                "direction": "LONG" if long_units > 0 else "SHORT" if short_units < 0 else "FLAT"
            })

        return positions

    # ===================
    # Utility Methods
    # ===================

    def is_connected(self) -> bool:
        """
        Check if API connection is working.

        Returns:
            True if connected, False otherwise
        """
        try:
            self.get_account_summary()
            return True
        except OandaError:
            return False

    def validate_instrument(self, instrument: str) -> bool:
        """
        Check if instrument is valid and tradeable.

        Args:
            instrument: Currency pair

        Returns:
            True if valid and tradeable
        """
        try:
            price = self.get_price(instrument)
            return price.get("tradeable", False)
        except OandaError:
            return False
