# FAZA 1: Foundation

> Cilj: Uspostaviti osnovu - OANDA API komunikacija i price fetching

---

## Prerequisites (Ti moraš napraviti)

### 1. OANDA Demo Account
- [ ] Otvori account: https://www.oanda.com/eu-en/trading/demo-account/
- [ ] Prijavi se na OANDA fxTrade Practice
- [ ] Idi na: My Account → Manage API Access
- [ ] Generiraj API Token (Practice)
- [ ] Zapiši:
  - Account ID: `_______________`
  - API Token: `_______________`

### 2. Python Environment
```bash
# U Dev folderu
cd "C:\Users\mglav\Projects\AI Trader\Dev"

# Kreiraj virtual environment
python -m venv venv

# Aktiviraj (Windows)
venv\Scripts\activate

# Instaliraj dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
```bash
# Kopiraj .env.example u .env
copy .env.example .env

# Uredi .env i dodaj svoje credentials
# NIKAD ne commitaj .env!
```

---

## Tasks (COMPLETED)

### Task 1.1: Projekt Struktura ✅
- [x] Kreirati `src/` folder strukturu
- [x] Kreirati `__init__.py` fajlove
- [x] Kreirati `scripts/` folder
- [x] Kreirati `data/` folder
- [x] Kreirati `logs/` folder

### Task 1.2: Config Module ✅
- [x] `src/utils/config.py` - učitavanje .env
- [x] `src/utils/logger.py` - loguru setup
- [x] `src/utils/helpers.py` - utility funkcije
- [x] `src/utils/__init__.py`

### Task 1.3: OANDA Client ✅
- [x] `src/trading/oanda_client.py`
  - [x] `__init__(self)` - učitaj credentials
  - [x] `_headers()` - auth headers
  - [x] `_request()` - base HTTP method
  - [x] `get_account()` - account info
  - [x] `get_price(instrument)` - current bid/ask
  - [x] `get_prices(instruments)` - multiple prices
  - [x] `get_candles(instrument, granularity, count)` - OHLC data
  - [x] `get_positions()` - open positions
  - [x] Error handling (OandaError exception)

### Task 1.4: CLI Scripts ✅
- [x] `scripts/fetch_prices.py` - dohvati cijene
- [x] `scripts/check_connection.py` - test konekcije
- [x] `scripts/account_info.py` - prikaz računa

---

## Acceptance Criteria

### Faza 1 je DONE kada:

```bash
# Ova komanda radi:
python scripts/fetch_prices.py EUR_USD

# Output:
# EUR/USD Price
# ─────────────
# Bid:    1.0843
# Ask:    1.0845
# Spread: 0.0002 (2.0 pips)
# Time:   2026-01-30 15:30:00 UTC
```

---

## Code Specifications

### oanda_client.py Template
```python
"""
OANDA REST API v20 Client

Usage:
    client = OandaClient()
    price = client.get_price("EUR_USD")
"""

import httpx
from src.utils.config import config
from src.utils.logger import logger

class OandaClient:
    """OANDA REST API wrapper."""

    def __init__(self):
        self.api_key = config.OANDA_API_KEY
        self.account_id = config.OANDA_ACCOUNT_ID
        self.base_url = config.OANDA_BASE_URL

    def _headers(self) -> dict:
        """Authorization headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_price(self, instrument: str) -> dict:
        """
        Get current price for instrument.

        Args:
            instrument: e.g., "EUR_USD"

        Returns:
            {"instrument": "EUR_USD", "bid": 1.0843, "ask": 1.0845, "spread": 0.0002}
        """
        # TODO: Implement
        pass

    def get_account(self) -> dict:
        """Get account info (balance, margin, etc.)."""
        # TODO: Implement
        pass

    def get_candles(self, instrument: str, granularity: str = "H1", count: int = 100) -> list:
        """
        Get OHLC candles.

        Args:
            instrument: e.g., "EUR_USD"
            granularity: M1, M5, M15, H1, H4, D
            count: number of candles (max 5000)

        Returns:
            List of candle dicts with open, high, low, close, volume
        """
        # TODO: Implement
        pass
```

### config.py Template
```python
"""
Configuration loader from .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from Dev folder
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

class Config:
    """Application configuration."""

    # OANDA
    OANDA_API_KEY: str = os.getenv("OANDA_API_KEY", "")
    OANDA_ACCOUNT_ID: str = os.getenv("OANDA_ACCOUNT_ID", "")
    OANDA_BASE_URL: str = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")

    # Risk (hard-coded, cannot be overridden)
    MAX_RISK_PER_TRADE: float = 0.03  # 3% max
    MAX_DAILY_DRAWDOWN: float = 0.03  # 3%
    MAX_CONCURRENT_POSITIONS: int = 3

    def validate(self) -> bool:
        """Check if required config is present."""
        if not self.OANDA_API_KEY:
            return False
        if not self.OANDA_ACCOUNT_ID:
            return False
        return True

config = Config()
```

---

## Testing

### Manual Test
```bash
# Nakon implementacije, testiraj:
python scripts/fetch_prices.py EUR_USD
python scripts/fetch_prices.py GBP_USD
python scripts/fetch_prices.py USD_JPY
```

### Expected Errors
```
# Bez credentials:
Error: OANDA_API_KEY not configured. Check .env file.

# Invalid instrument:
Error: Invalid instrument 'INVALID'. Use format like EUR_USD.

# Network error:
Error: Could not connect to OANDA API. Check internet connection.
```

---

## Timeline

| Task | Procjena |
|------|----------|
| Prerequisites (ti) | ~30 min |
| Task 1.1: Struktura | ~5 min |
| Task 1.2: Config | ~15 min |
| Task 1.3: OANDA Client | ~30 min |
| Task 1.4: Script | ~15 min |
| Testing | ~15 min |
| **TOTAL** | ~2 sata |

---

## Kada si spreman

Javi mi:
1. "Imam OANDA credentials" - i počinjemo s implementacijom
2. Ili - "Setup venv i .env" - ako trebaš pomoć s tim

---

*Verzija: 1.0 | Kreirano: 2026-01-30*
