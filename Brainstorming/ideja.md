# AI TRADER - FOREX TRADING SUSTAV

**Detaljan tehnički plan implementacije**

Verzija 2.1 | Siječanj 2026
Sirius Grupa d.o.o.

---

## 1. EXECUTIVE SUMMARY

Ovaj dokument opisuje arhitekturu i plan implementacije automatiziranog forex trading sustava koji koristi **Claude Code CLI** kao sučelje i **Claude AI** za analizu tržišta i donošenje odluka.

### 1.1 Ciljevi projekta

- Automatizirano praćenje i analiza forex tržišta 24/5
- AI-potpomognuto donošenje trading odluka
- Risk management s hard-coded limitima
- Human-in-the-loop odobrenje za sve tradeove
- Post-trade analiza i kontinuirano učenje

### 1.2 Ključna promjena: Claude Code umjesto Moltbot

| Aspekt | Moltbot (v1) | Claude Code (v2) |
|--------|--------------|------------------|
| Sučelje | Telegram/Discord | Terminal CLI |
| Infrastruktura | VPS, Docker | Lokalno računalo |
| Kompleksnost | Visoka | Niska |
| Setup time | Tjedni | Sati |
| Mjesečni trošak | ~150 EUR | ~80 EUR |
| Human approval | Chat buttons | Direktno u CLI |

---

## 2. ARHITEKTURA SUSTAVA

### 2.1 Arhitektura dijagram

```
┌─────────────────────────────────────────────────────────────────┐
│                  TI (Terminal / Claude Code CLI)                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       CLAUDE CODE                                │
│  • AI reasoning (Claude Opus 4.5)                                │
│  • Čita/piše datoteke                                            │
│  • Pokreće Python skripte                                        │
│  • MCP: memory, supabase, filesystem                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
   ┌────────────┐     ┌────────────┐     ┌────────────┐
   │  Trading   │     │  Market    │     │  Storage   │
   │  Scripts   │     │  Data      │     │            │
   │  (Python)  │     │  Scripts   │     │  SQLite /  │
   │            │     │  (Python)  │     │  JSON      │
   └─────┬──────┘     └────────────┘     └────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OANDA REST API v20                          │
│                      (Demo → Live)                               │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Komponente sustava

#### A) Claude Code (Sučelje + AI Engine)
- CLI sučelje - direktna interakcija u terminalu
- AI reasoning - Claude Opus 4.5 za analizu tržišta
- File operations - čitanje/pisanje konfiguracija
- Script execution - pokretanje Python skripti
- MCP serveri - memory, filesystem (već konfigurirano)

#### B) Trading Scripts (Python)
- OANDA client - REST API wrapper
- Order management - kreiranje/zatvaranje pozicija
- Position sizing - izračun veličine pozicije
- Risk checks - hard-coded limiti
- Technical indicators - pandas-ta

#### C) Market Data Scripts (Python)
- Price fetcher - dohvaćanje cijena s OANDA
- Technical analysis - indikatori, levels
- Economic calendar - nadolazeći eventi (optional)

#### D) Storage
- SQLite - trade log, analiza performansi
- JSON files - konfiguracija, cache
- MCP Memory - RAG za pamćenje analiza (optional)

---

## 3. TEHNIČKI STACK

### 3.1 Python Environment

| Komponenta | Tehnologija | Razlog |
|------------|-------------|--------|
| Runtime | Python 3.11+ | Stabilan, dobar za finance |
| HTTP Client | httpx | Async support, moderno |
| Data | pandas | Analiza, manipulation |
| TA Library | pandas-ta | Tehnički indikatori |
| Database | SQLite | Jednostavno, bez servera |
| Config | python-dotenv | Environment variables |

### 3.2 AI (via Claude Code)

| Komponenta | Tehnologija | Razlog |
|------------|-------------|--------|
| Primary LLM | Claude Opus 4.5 | Best reasoning |
| Interface | Claude Code CLI | Direktna interakcija |
| Memory | MCP memory server | RAG (optional) |

### 3.3 Što je eliminirano

- ~~Node.js/TypeScript~~ → Samo Python
- ~~PostgreSQL + TimescaleDB~~ → SQLite
- ~~Redis~~ → In-memory / JSON cache
- ~~BullMQ~~ → Direktno izvršavanje
- ~~Pinecone/Chroma~~ → MCP memory
- ~~Docker Compose~~ → venv
- ~~VPS~~ → Lokalno računalo
- ~~Telegram/Discord~~ → CLI

---

## 4. OANDA INTEGRACIJA

### 4.1 Zašto OANDA?

| Aspekt | Vrijednost |
|--------|------------|
| API | REST v20 (odlična dokumentacija) |
| Demo | Besplatan practice account |
| Min Deposit | $0 |
| Spread EUR/USD | 1.0-1.2 pip |
| Regulacija | FCA, CFTC |

### 4.2 API Endpoints

```
Base URL (Demo): https://api-fxpractice.oanda.com
Base URL (Live): https://api-fxtrade.oanda.com

GET  /v3/accounts/{accountId}           - Account info
GET  /v3/accounts/{accountId}/pricing   - Current prices
POST /v3/accounts/{accountId}/orders    - Place order
GET  /v3/accounts/{accountId}/positions - Open positions
PUT  /v3/accounts/{accountId}/positions/{instrument}/close - Close position
```

### 4.3 Python Client Primjer

```python
# src/trading/oanda_client.py
import httpx
from dotenv import load_dotenv
import os

load_dotenv()

class OandaClient:
    def __init__(self):
        self.api_key = os.getenv("OANDA_API_KEY")
        self.account_id = os.getenv("OANDA_ACCOUNT_ID")
        self.base_url = "https://api-fxpractice.oanda.com"  # Demo

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_price(self, instrument: str) -> dict:
        """Get current price for instrument (e.g., 'EUR_USD')"""
        url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
        params = {"instruments": instrument}

        with httpx.Client() as client:
            response = client.get(url, headers=self._headers(), params=params)
            data = response.json()

        price = data["prices"][0]
        return {
            "instrument": instrument,
            "bid": float(price["bids"][0]["price"]),
            "ask": float(price["asks"][0]["price"]),
            "spread": float(price["asks"][0]["price"]) - float(price["bids"][0]["price"])
        }

    def open_position(self, instrument: str, units: int, sl: float, tp: float) -> dict:
        """Open a position. Positive units = long, negative = short"""
        url = f"{self.base_url}/v3/accounts/{self.account_id}/orders"

        payload = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(units),
                "stopLossOnFill": {"price": str(sl)},
                "takeProfitOnFill": {"price": str(tp)}
            }
        }

        with httpx.Client() as client:
            response = client.post(url, headers=self._headers(), json=payload)
            return response.json()
```

---

## 5. TRADING STRATEGIJE

### 5.1 AI-Assisted Analysis

Claude ne donosi odluke u milisekundama - fokus je na višim timeframeovima (H1, H4, D1).

#### Workflow (v2.1):
1. Ti pitaš: "Analiziraj EUR/USD"
2. Claude dohvaća podatke (pokreće Python skriptu)
3. **Sentiment Analysis** - price action + news sentiment
4. **Adversarial Thinking** - Bull vs Bear self-debate
5. **RAG Query** - provjera sličnih prošlih grešaka
6. Claude izračunava **confidence score** (0-100)
7. Risk tier se automatski određuje (1-3%)
8. Claude daje preporuku s obrazloženjem
9. Ti odobravaš ili odbijaš

### 5.2 Adversarial Thinking (NOVO)

Prije svakog tradea, Claude prolazi kroz strukturiranu debatu:

```
BULL CASE: Zašto bi trade uspio?
- Tehnički razlozi
- Fundamentalni razlozi
- Sentiment podrška

BEAR CASE: Zašto bi trade propao?
- Kontra-indikatori
- Rizici
- Što može poći po zlu?

VERDICT: Balance evaluacija
```

### 5.3 Sentiment Analysis (NOVO)

| Izvor | Output |
|-------|--------|
| Price action | -1 to +1 |
| News headlines | Bullish/Bearish/Neutral |
| Economic calendar | Risk score |

**Combined score:** -1.0 (bearish) to +1.0 (bullish)

### 5.4 RAG Error Memory (NOVO)

Sustav pamti sve gubitničke tradeove:
- Query prije svakog novog tradea
- Automatska penalizacija sličnih setupova
- Weekly review top 3 ponovljene greške

### 5.2 Primjer Analysis Prompta

```
Analiziraj EUR/USD za potencijalni trade.

PODACI:
- Trenutna cijena: 1.0843
- D1 Trend: EMA20 > EMA50 (bullish)
- H4: RSI(14) = 58
- Key support: 1.0800
- Key resistance: 1.0900
- Nadolazeći eventi: ECB sutra 13:45

ODGOVORI:
1. Bias (bullish/bearish/neutral)
2. Confidence (0-100)
3. Entry zone
4. Stop loss level
5. Take profit level
6. Risk/Reward ratio
7. Reasoning (zašto?)
```

---

## 6. RISK MANAGEMENT

> **KRITIČNO:** Core parametri su HARD-CODED i ne mogu biti overrideani!

### 6.1 Hard Limits

| Parametar | Vrijednost | Napomena |
|-----------|------------|----------|
| Max risk per trade | **1-3% equity** | Ovisno o confidence |
| Max daily drawdown | 3% equity | Auto-stop trading |
| Max weekly drawdown | 6% equity | Human review |
| Max concurrent positions | 3 | Diversifikacija |
| Max leverage | 10:1 | Konzervativno |

### 6.2 Risk Tiers (NOVO)

| Confidence Score | Max Risk | Kada |
|------------------|----------|------|
| 90-100% | 3% | Svi faktori poravnati |
| 70-89% | 2% | Većina faktora OK |
| 50-69% | 1% | Minimalni rizik |
| < 50% | 0% | **NE TRADATI** |

### 6.3 Position Sizing (Updated)

```python
# src/trading/position_sizer.py

def calculate_position_size(
    equity: float,
    confidence_score: int,  # 0-100
    entry_price: float,
    stop_loss: float
) -> tuple[int, float]:
    """
    Calculate position size based on confidence-driven risk tiers.
    Returns (units, risk_percent)
    """
    # Determine risk tier
    if confidence_score >= 90:
        risk_percent = 3.0
    elif confidence_score >= 70:
        risk_percent = 2.0
    elif confidence_score >= 50:
        risk_percent = 1.0
    else:
        return 0, 0.0  # DO NOT TRADE

    risk_amount = equity * (risk_percent / 100)
    pip_distance = abs(entry_price - stop_loss) / 0.0001
    pip_value_per_unit = 0.0001

    units = int(risk_amount / (pip_distance * pip_value_per_unit))
    return units, risk_percent

# Primjer: $10,000 equity, 75% confidence, 43 pip SL
# Risk tier = 2%, Risk = $200
# Units ≈ 4,651 units
```

### 6.4 Risk Validation

```python
# src/trading/risk_manager.py

MAX_RISK_PER_TRADE = 0.01  # 1%
MAX_DAILY_DRAWDOWN = 0.03  # 3%
MAX_CONCURRENT_POSITIONS = 3

def validate_trade(equity: float, risk_amount: float, open_positions: list) -> tuple:
    """
    Validate trade against hard-coded risk limits.
    Returns (is_valid, reason)
    """
    # Check risk per trade
    if risk_amount > equity * MAX_RISK_PER_TRADE:
        return False, f"Risk ${risk_amount:.2f} exceeds 1% limit (${equity * MAX_RISK_PER_TRADE:.2f})"

    # Check concurrent positions
    if len(open_positions) >= MAX_CONCURRENT_POSITIONS:
        return False, f"Max {MAX_CONCURRENT_POSITIONS} concurrent positions reached"

    return True, "OK"
```

### 6.5 Comprehensive Logging (NOVO)

Tri razine logiranja za debugging i post-mortem:

**1. Trade Log** (svaki izvršeni trade):
- timestamp, pair, direction, prices, size, risk
- confidence_score, bull_case, bear_case, sentiment
- execution_time, slippage

**2. Decision Log** (svaka analiza):
- technical_score, fundamental_score, sentiment_score
- adversarial_passed, rag_warnings
- final_decision, recommendation

**3. Error Log** (svi gubici):
- trade_id, loss_amount, root_cause
- error_category (NEWS_IGNORED, OVERCONFIDENT, etc.)
- lesson_learned, added_to_rag

---

## 7. IMPLEMENTACIJSKI PLAN

### 7.1 Faze projekta (6-8 tjedana)

#### FAZA 1: Foundation (Tjedan 1-2)
- [ ] OANDA demo account + API setup
- [ ] Python environment (venv)
- [ ] OANDA API wrapper
- [ ] Basic price fetching
- [ ] Project structure

**Milestone:** `python scripts/fetch_prices.py EUR_USD` radi

#### FAZA 2: Core Trading (Tjedan 3-4)
- [ ] Order management
- [ ] Position sizing calculator
- [ ] Risk management hard limits
- [ ] Technical indicators
- [ ] Trade logging (SQLite)

**Milestone:** Možeš izvršiti trade

#### FAZA 3: AI Integration (Tjedan 5-6)
- [ ] Claude analysis prompts
- [ ] Market analysis workflow
- [ ] Trade suggestion system
- [ ] Human approval flow

**Milestone:** Claude predlaže, ti odobravaš

#### FAZA 4: Production (Tjedan 7-8)
- [ ] Performance tracking
- [ ] Trade journaling
- [ ] Backtesting
- [ ] Demo testing

**Milestone:** Spreman za live

---

## 8. PROJEKT STRUKTURA

```
AI Trader/
├── Brainstorming/           # Planiranje (ovaj folder)
│
├── src/                     # Izvorni kod
│   ├── trading/
│   │   ├── __init__.py
│   │   ├── oanda_client.py  # OANDA API wrapper
│   │   ├── orders.py        # Order management
│   │   ├── position_sizer.py
│   │   └── risk_manager.py
│   │
│   ├── market/
│   │   ├── __init__.py
│   │   ├── price_fetcher.py
│   │   └── indicators.py
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   └── prompts.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config.py
│       └── logger.py
│
├── data/
│   ├── trades.db            # SQLite
│   └── cache/
│
├── scripts/
│   ├── fetch_prices.py
│   ├── execute_trade.py
│   └── emergency_close.py
│
├── .env.example
├── .env                     # (gitignored)
├── requirements.txt
└── README.md
```

---

## 9. SIGURNOST

### 9.1 Lokalna sigurnost
- API keys u .env (gitignored)
- Dedicated OANDA sub-account
- Nikad hardcode keys

### 9.2 Risk limiti
- Hard-coded u kodu
- Ne mogu biti overrideani
- Human approval za svaki trade

### 9.3 Emergency
- `python scripts/emergency_close.py` - zatvara sve
- Manualno: OANDA web platforma

---

## 10. TROŠKOVI

### Mjesečno
| Stavka | EUR |
|--------|-----|
| Claude API | ~50-100 |
| News API (optional) | 0-30 |
| **UKUPNO** | **~50-130** |

### Ušteda vs Moltbot
- VPS: -15 EUR
- Pinecone: -20 EUR
- Domain: -2 EUR
- **Total ušteda: ~45-50%**

---

## 11. SLJEDEĆI KORACI

### ODMAH:
1. **Otvori OANDA Practice Account**
   - https://www.oanda.com/eu-en/trading/demo-account/

2. **Setup Python environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install httpx pandas pandas-ta python-dotenv
   ```

3. **Konfiguriraj .env**
   ```
   OANDA_API_KEY=your_api_key_here
   OANDA_ACCOUNT_ID=your_account_id
   ```

4. **Testiraj price fetch**

---

> **VAŽNO:** Testiraj minimalno 3 mjeseca na demo accountu prije live tradinga!

---

*— Kraj dokumenta —*
*Verzija 2.1 | Adversarial + RAG + Sentiment + Logging | 2026-01-30*
