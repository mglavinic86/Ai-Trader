"""
Configuration loader from .env file.

Usage:
    from src.utils.config import config

    # For MT5
    login = config.MT5_LOGIN
    if not config.validate_mt5():
        print("Missing MT5 credentials!")

    # Legacy OANDA (deprecated)
    api_key = config.OANDA_API_KEY
    if not config.validate():
        print("Missing credentials!")
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Find .env file (in Dev folder)
_dev_dir = Path(__file__).parent.parent.parent
_env_path = _dev_dir / ".env"

# Load environment variables
load_dotenv(_env_path)


class Config:
    """Application configuration with hard-coded risk limits."""

    # ===================
    # MT5 Configuration
    # ===================
    MT5_LOGIN: int = int(os.getenv("MT5_LOGIN", "0"))
    MT5_PASSWORD: str = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER: str = os.getenv("MT5_SERVER", "OANDA-TMS-Demo")
    MT5_TERMINAL_PATH: str = os.getenv("MT5_TERMINAL_PATH", "")  # Optional, auto-detect if empty

    # ===================
    # OANDA Configuration (Legacy - kept for reference)
    # ===================
    OANDA_API_KEY: str = os.getenv("OANDA_API_KEY", "")
    OANDA_ACCOUNT_ID: str = os.getenv("OANDA_ACCOUNT_ID", "")
    OANDA_BASE_URL: str = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")

    # ===================
    # Risk Limits (HARD-CODED - Cannot be overridden!)
    # ===================
    MAX_RISK_PERCENT_TIER_1: float = 0.01  # 1% for confidence 50-69
    MAX_RISK_PERCENT_TIER_2: float = 0.02  # 2% for confidence 70-89
    MAX_RISK_PERCENT_TIER_3: float = 0.03  # 3% for confidence 90-100

    MAX_DAILY_DRAWDOWN: float = 0.03      # 3% daily limit
    MAX_WEEKLY_DRAWDOWN: float = 0.06     # 6% weekly limit
    MAX_CONCURRENT_POSITIONS: int = 3      # Max open positions
    MAX_LEVERAGE: int = 10                 # 10:1 max
    MIN_CONFIDENCE_TO_TRADE: int = 50      # Below this = no trade

    # ===================
    # Trading Parameters
    # ===================
    DEFAULT_PAIRS: list = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "BTC_USD"]
    MAX_SPREAD_PIPS: float = 3.0           # Don't trade if spread > 3 pips

    # ===================
    # Logging
    # ===================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def validate(self) -> tuple[bool, str]:
        """
        Check if required configuration is present (uses MT5 by default).

        Returns:
            (is_valid, error_message)
        """
        return self.validate_mt5()

    def validate_mt5(self) -> tuple[bool, str]:
        """
        Check if MT5 configuration is present.

        Returns:
            (is_valid, error_message)
        """
        if not self.MT5_LOGIN or self.MT5_LOGIN == 0:
            return False, "MT5_LOGIN not configured. Add it to .env file."

        if not self.MT5_PASSWORD:
            return False, "MT5_PASSWORD not configured. Add it to .env file."

        if not self.MT5_SERVER:
            return False, "MT5_SERVER not configured. Add it to .env file."

        return True, "OK"

    def validate_oanda(self) -> tuple[bool, str]:
        """
        Check if OANDA configuration is present (legacy).

        Returns:
            (is_valid, error_message)
        """
        if not self.OANDA_API_KEY:
            return False, "OANDA_API_KEY not configured. Add it to .env file."

        if not self.OANDA_ACCOUNT_ID:
            return False, "OANDA_ACCOUNT_ID not configured. Add it to .env file."

        if not self.OANDA_BASE_URL:
            return False, "OANDA_BASE_URL not configured."

        return True, "OK"

    def get_risk_percent(self, confidence: int) -> float:
        """
        Get max risk percent based on confidence score.

        Args:
            confidence: Score 0-100

        Returns:
            Risk percent (0.01, 0.02, or 0.03) or 0 if below minimum
        """
        if confidence < self.MIN_CONFIDENCE_TO_TRADE:
            return 0.0
        elif confidence < 70:
            return self.MAX_RISK_PERCENT_TIER_1
        elif confidence < 90:
            return self.MAX_RISK_PERCENT_TIER_2
        else:
            return self.MAX_RISK_PERCENT_TIER_3

    def is_demo(self) -> bool:
        """Check if using demo/practice account."""
        # MT5: Check server name for demo indicator
        if "demo" in self.MT5_SERVER.lower():
            return True
        # OANDA legacy
        if "practice" in self.OANDA_BASE_URL.lower():
            return True
        return False


# Singleton instance
config = Config()
