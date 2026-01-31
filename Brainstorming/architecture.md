# Arhitektura - AI TRADER (Claude Code) v2.0

## Dijagram sustava

```
┌─────────────────────────────────────────────────────────────────┐
│                  TI (Terminal / Claude Code CLI)                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       CLAUDE CODE                                │
│  • AI reasoning (Claude Opus 4.5)                                │
│  • Adversarial thinking (Bull vs Bear)                           │
│  • Čita/piše datoteke                                            │
│  • Pokreće Python skripte                                        │
│  • MCP: memory (RAG), filesystem                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
┌──────────┐          ┌──────────┐          ┌──────────────┐
│ Trading  │          │ Market   │          │   Analysis   │
│ Scripts  │          │ Data     │          │   Engine     │
│ (Python) │          │ (Python) │          │   (Python)   │
└────┬─────┘          └────┬─────┘          └──────┬───────┘
     │                     │                       │
     │                     │              ┌────────┴────────┐
     │                     │              ▼                 ▼
     │                     │        ┌──────────┐     ┌──────────┐
     │                     │        │Sentiment │     │Adversarial│
     │                     │        │ Analyzer │     │  Engine   │
     │                     │        └──────────┘     └──────────┘
     │                     │
     ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                         STORAGE LAYER                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐     │
│  │ SQLite  │  │  JSON   │  │  Logs   │  │  RAG Memory     │     │
│  │ Trades  │  │ Config  │  │ Files   │  │  (MCP/Local)    │     │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OANDA REST API v20                          │
│                      (Demo → Live)                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Komponente sustava

### A) Claude Code (Sučelje + AI Engine)
- **CLI sučelje** - direktna interakcija u terminalu
- **AI reasoning** - Claude Opus 4.5 za analizu tržišta
- **Adversarial thinking** - Bull vs Bear self-debate
- **File operations** - čitanje/pisanje konfiguracija
- **Script execution** - pokretanje Python skripti
- **MCP serveri** - memory (RAG), filesystem

### B) Trading Scripts (Python)
- **OANDA client** - REST API wrapper
- **Order management** - kreiranje/zatvaranje pozicija
- **Position sizing** - confidence-based tiers (1-3%)
- **Risk checks** - hard-coded limiti
- **Trade logger** - SQLite zapisivanje

### C) Market Data Scripts (Python)
- **Price fetcher** - dohvaćanje cijena s OANDA
- **Technical analysis** - indikatori (pandas-ta)
- **Economic calendar** - nadolazeći eventi

### D) Analysis Engine (NOVO)
- **Sentiment analyzer** - analiza tržišnog sentimenta
- **Adversarial engine** - strukturirana Bull vs Bear analiza
- **Confidence calculator** - kombinira sve faktore

### E) Storage Layer
- **SQLite** - trade log, performanse
- **JSON files** - konfiguracija, cache
- **Log files** - trade logs, decision logs, error logs
- **RAG Memory** - pamćenje grešaka (MCP memory ili lokalno)

---

## Tech Stack

### Python Environment
| Komponenta | Tehnologija | Razlog |
|------------|-------------|--------|
| Runtime | Python 3.11+ | Stabilan, dobar za finance |
| HTTP Client | httpx | Async support, moderno |
| Data | pandas | Analiza, manipulation |
| TA Library | pandas-ta | Tehnički indikatori |
| Database | SQLite | Jednostavno, bez servera |
| Config | python-dotenv | Environment variables |
| Logging | loguru | Strukturirano logiranje |

### AI (via Claude Code)
| Komponenta | Tehnologija | Razlog |
|------------|-------------|--------|
| Primary LLM | Claude Opus 4.5 | Best reasoning |
| Interface | Claude Code CLI | Direktna interakcija |
| RAG Memory | MCP memory / SQLite | Pamćenje grešaka |

### Lokalna infrastruktura
- **OS:** Windows (tvoje računalo)
- **Python:** venv
- **IDE:** Claude Code + VS Code
- **Secrets:** `.env` file (gitignored)

---

## Projekt struktura (v2.0)

```
AI Trader/
├── Brainstorming/           # Planiranje
│
├── src/
│   ├── trading/             # Trading logika
│   │   ├── __init__.py
│   │   ├── oanda_client.py  # OANDA API wrapper
│   │   ├── orders.py        # Order management
│   │   ├── position_sizer.py # Confidence-based sizing
│   │   └── risk_manager.py  # Hard limits + tiers
│   │
│   ├── market/              # Tržišni podaci
│   │   ├── __init__.py
│   │   ├── price_fetcher.py
│   │   ├── indicators.py
│   │   └── calendar.py      # Economic calendar
│   │
│   ├── analysis/            # AI analiza (NOVO)
│   │   ├── __init__.py
│   │   ├── sentiment.py     # Sentiment analysis
│   │   ├── adversarial.py   # Bull vs Bear engine
│   │   ├── confidence.py    # Score calculator
│   │   └── prompts/
│   │       ├── analysis.py
│   │       ├── bull_case.py
│   │       └── bear_case.py
│   │
│   ├── memory/              # RAG sustav (NOVO)
│   │   ├── __init__.py
│   │   ├── error_store.py   # Greške storage
│   │   ├── query.py         # RAG queries
│   │   └── learn.py         # Post-trade learning
│   │
│   ├── logging/             # Logging sustav (NOVO)
│   │   ├── __init__.py
│   │   ├── trade_logger.py
│   │   ├── decision_logger.py
│   │   └── error_logger.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config.py
│       └── helpers.py
│
├── data/
│   ├── trades.db            # SQLite - trade log
│   ├── errors.db            # SQLite - RAG errors
│   ├── cache/               # Cached market data
│   └── exports/             # CSV exports
│
├── logs/                    # Log files (NOVO)
│   ├── trades/              # Trade logs po danu
│   ├── decisions/           # Decision logs
│   └── errors/              # Error logs
│
├── scripts/
│   ├── fetch_prices.py
│   ├── analyze_pair.py
│   ├── execute_trade.py
│   ├── review_errors.py     # Weekly error review
│   └── emergency_close.py
│
├── tests/
│
├── .env.example
├── .env                     # (gitignored)
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Data Flow: Trade Decision

```
1. USER REQUEST
   "Analiziraj EUR/USD"
          │
          ▼
2. MARKET DATA
   ├── Fetch prices (OANDA)
   ├── Calculate indicators (pandas-ta)
   └── Check calendar (events)
          │
          ▼
3. SENTIMENT ANALYSIS
   ├── Price action sentiment
   ├── News sentiment (if available)
   └── Combined score (-1 to +1)
          │
          ▼
4. ADVERSARIAL ANALYSIS
   ├── Generate BULL case
   ├── Generate BEAR case
   └── Evaluate balance
          │
          ▼
5. RAG QUERY
   ├── "Similar past errors?"
   ├── If found → penalize confidence
   └── Display warnings
          │
          ▼
6. CONFIDENCE CALCULATION
   ├── Technical score (0-100)
   ├── Sentiment score (adjusted)
   ├── Adversarial adjustment
   ├── RAG penalty (if any)
   └── Final confidence (0-100)
          │
          ▼
7. RISK TIER SELECTION
   ├── 90-100% → 3% risk
   ├── 70-89% → 2% risk
   ├── 50-69% → 1% risk
   └── <50% → NO TRADE
          │
          ▼
8. PRE-TRADE CHECKLIST
   ├── All limits OK?
   ├── Adversarial completed?
   ├── RAG checked?
   └── Sentiment calculated?
          │
          ▼
9. HUMAN APPROVAL
   └── "Želiš li tradati? (da/ne)"
          │
          ▼
10. EXECUTION + LOGGING
    ├── Execute order (OANDA)
    ├── Log trade (SQLite)
    ├── Log decision (file)
    └── Update state
          │
          ▼
11. POST-TRADE (if loss)
    ├── Analyze root cause
    ├── Categorize error
    ├── Add to RAG memory
    └── Log lesson learned
```

---

## Broker: OANDA

| Aspekt | Vrijednost |
|--------|------------|
| API | REST v20 |
| Demo | https://api-fxpractice.oanda.com |
| Live | https://api-fxtrade.oanda.com |
| Min Deposit | $0 |
| Spread EUR/USD | 1.0-1.2 pip |
| Regulacija | FCA, CFTC |
| Dokumentacija | https://developer.oanda.com |

---

## Prednosti arhitekture v2.0

| Aspekt | v1.0 | v2.0 |
|--------|------|------|
| Decision quality | Single analysis | Adversarial debate |
| Learning | None | RAG error memory |
| Observability | Basic | Comprehensive logging |
| Risk sizing | Fixed 1% | Dynamic 1-3% tiers |
| Sentiment | None | Integrated |

---
*Ažurirano: 2026-01-30 | v2.0 - Adversarial, RAG, Sentiment, Logging*
