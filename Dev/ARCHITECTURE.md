# AI TRADER - Detaljna Arhitektura

---

## Komponente Sustava

### 1. Trading Module (`src/trading/`)

```
src/trading/
├── __init__.py
├── oanda_client.py    # OANDA API wrapper
├── orders.py          # Order management
├── position_sizer.py  # Confidence-based sizing
└── risk_manager.py    # Hard-coded limits
```

#### oanda_client.py
- HTTP client za OANDA REST API v20
- Metode: `get_price()`, `get_account()`, `get_positions()`
- Error handling za API failures

#### orders.py
- `open_position(instrument, units, sl, tp)`
- `close_position(instrument)`
- `modify_position(instrument, sl=None, tp=None)`

#### position_sizer.py
- `calculate_position_size(equity, confidence, entry, sl)`
- Returns (units, risk_percent) based on confidence tier

#### risk_manager.py
- Hard-coded limits (MAX_RISK, MAX_DRAWDOWN, etc.)
- `validate_trade()` - provjera svih limita
- `check_daily_drawdown()`
- `check_correlation()`

---

### 2. Market Module (`src/market/`)

```
src/market/
├── __init__.py
├── price_fetcher.py   # OANDA price data
├── indicators.py      # Technical analysis
└── calendar.py        # Economic events (optional)
```

#### price_fetcher.py
- `get_current_price(instrument)` - bid/ask/spread
- `get_candles(instrument, granularity, count)`
- Cache za smanjenje API poziva

#### indicators.py
- `calculate_ema(df, period)`
- `calculate_rsi(df, period)`
- `calculate_atr(df, period)`
- `identify_support_resistance(df)`

---

### 3. Analysis Module (`src/analysis/`)

```
src/analysis/
├── __init__.py
├── prompts.py         # Claude prompt templates
├── sentiment.py       # Sentiment scoring
├── adversarial.py     # Bull vs Bear engine
└── confidence.py      # Score calculator
```

#### prompts.py
- `ANALYSIS_PROMPT` - glavni template za analizu
- `BULL_CASE_PROMPT` - generiranje bull argumenta
- `BEAR_CASE_PROMPT` - generiranje bear argumenta

#### sentiment.py
- `calculate_price_action_sentiment(candles)`
- Returns: -1.0 (bearish) to +1.0 (bullish)

#### adversarial.py
- Struktura za Bull vs Bear debate
- `generate_bull_case(data)`
- `generate_bear_case(data)`
- `evaluate_verdict(bull, bear)`

#### confidence.py
- `calculate_confidence(technical, sentiment, adversarial)`
- Returns: 0-100 score

---

### 4. Utils Module (`src/utils/`)

```
src/utils/
├── __init__.py
├── config.py          # Configuration loader
├── logger.py          # Logging setup
└── helpers.py         # Common utilities
```

#### config.py
- Loads `.env` variables
- Provides typed config access

#### logger.py
- Loguru setup
- Trade log, Decision log, Error log

---

### 5. Scripts (`scripts/`)

```
scripts/
├── fetch_prices.py       # CLI: dohvati cijene
├── analyze_pair.py       # CLI: analiza para
├── execute_trade.py      # CLI: izvrši trade
├── check_positions.py    # CLI: status pozicija
├── emergency_close.py    # CLI: zatvori sve
└── daily_report.py       # CLI: dnevni izvještaj
```

---

## Data Flow: Trade Decision

```
1. USER: "Analiziraj EUR/USD"
          │
          ▼
2. FETCH MARKET DATA
   ├── price_fetcher.get_current_price("EUR_USD")
   ├── price_fetcher.get_candles("EUR_USD", "H4", 100)
   └── indicators.calculate_all(candles)
          │
          ▼
3. SENTIMENT ANALYSIS
   └── sentiment.calculate_price_action_sentiment(candles)
          │
          ▼
4. ADVERSARIAL ANALYSIS
   ├── adversarial.generate_bull_case(data)
   ├── adversarial.generate_bear_case(data)
   └── adversarial.evaluate_verdict(bull, bear)
          │
          ▼
5. CONFIDENCE CALCULATION
   └── confidence.calculate_confidence(tech, sent, adv)
          │
          ▼
6. RISK TIER SELECTION
   └── position_sizer.calculate_position_size(...)
          │
          ▼
7. VALIDATE TRADE
   └── risk_manager.validate_trade(...)
          │
          ▼
8. HUMAN APPROVAL
   └── "Želiš li tradati? (da/ne)"
          │
          ▼
9. EXECUTE
   └── orders.open_position(...)
          │
          ▼
10. LOG
    └── logger.log_trade(...)
```

---

## Database Schema (SQLite)

### trades table
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    trade_id TEXT UNIQUE,
    timestamp TEXT,
    instrument TEXT,
    direction TEXT,  -- LONG/SHORT
    entry_price REAL,
    exit_price REAL,
    stop_loss REAL,
    take_profit REAL,
    units INTEGER,
    risk_amount REAL,
    risk_percent REAL,
    confidence_score INTEGER,
    pnl REAL,
    pnl_percent REAL,
    status TEXT,  -- OPEN/CLOSED/STOPPED
    closed_at TEXT,
    notes TEXT
);
```

### decisions table
```sql
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    instrument TEXT,
    technical_score INTEGER,
    sentiment_score REAL,
    confidence_score INTEGER,
    bull_case TEXT,
    bear_case TEXT,
    recommendation TEXT,
    decision TEXT,  -- TRADE/SKIP/WAIT
    trade_id TEXT  -- if traded
);
```

### errors table (RAG)
```sql
CREATE TABLE errors (
    id INTEGER PRIMARY KEY,
    trade_id TEXT,
    timestamp TEXT,
    instrument TEXT,
    loss_amount REAL,
    error_category TEXT,
    root_cause TEXT,
    lessons TEXT,
    tags TEXT  -- JSON array
);
```

---

## API Response Formats

### OANDA Price Response
```json
{
  "prices": [{
    "instrument": "EUR_USD",
    "bids": [{"price": "1.08430"}],
    "asks": [{"price": "1.08445"}],
    "tradeable": true
  }]
}
```

### OANDA Order Response
```json
{
  "orderFillTransaction": {
    "id": "12345",
    "instrument": "EUR_USD",
    "units": "3000",
    "price": "1.08435",
    "pl": "0.0000"
  }
}
```

---

## Error Handling

| Error Type | Action |
|------------|--------|
| API Timeout | Retry 3x, then abort |
| Invalid Price | Skip trade, log warning |
| Risk Limit Hit | Block trade, notify user |
| Position Error | Log, attempt recovery |
| Network Error | Retry with exponential backoff |

---

## Security Notes

1. **API Keys** - samo u `.env`, nikad u kodu
2. **Risk Limits** - hard-coded, ne mogu biti promijenjeni
3. **Human Approval** - obavezno za sve tradeove
4. **Emergency Close** - uvijek dostupno

---

*Verzija: 1.0 | Kreirano: 2026-01-30*
