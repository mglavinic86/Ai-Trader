# AI TRADER - Development Context

> Glavni dokument za development. Claude Code koristi ovaj fajl kao kontekst.

---

## Quick Reference

| Aspekt | Vrijednost |
|--------|------------|
| **Projekt** | AI Trader - Forex Trading System |
| **Sučelje** | Claude Code CLI |
| **AI Model** | Claude Opus 4.5 |
| **Broker** | OANDA (REST API v20) |
| **Runtime** | Python 3.11+ |
| **Database** | SQLite |
| **Lokacija** | Lokalno (Windows) |

---

## Projekt Opis

Automatizirani forex trading sustav koji koristi Claude Code kao sučelje i Claude AI za:
- Analizu tržišta (H1, H4, D1 timeframe)
- Adversarial thinking (Bull vs Bear debate)
- Risk management s confidence-based tierovima
- Human-in-the-loop odobrenje za sve tradeove

---

## Arhitektura (Sažetak)

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
│  • Pokreće Python skripte                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
   ┌────────────┐     ┌────────────┐     ┌────────────┐
   │  Trading   │     │  Market    │     │  Storage   │
   │  Scripts   │     │  Data      │     │  SQLite +  │
   │  (Python)  │     │  (Python)  │     │  JSON      │
   └─────┬──────┘     └────────────┘     └────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OANDA REST API v20                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Risk Management (Hard Limits)

| Parametar | Vrijednost |
|-----------|------------|
| Max risk per trade | 1-3% (confidence-based) |
| Max daily drawdown | 3% |
| Max weekly drawdown | 6% |
| Max concurrent positions | 3 |
| Min confidence za trade | 50% |

### Risk Tiers

| Confidence | Max Risk |
|------------|----------|
| 90-100% | 3% |
| 70-89% | 2% |
| 50-69% | 1% |
| < 50% | NO TRADE |

---

## Tech Stack

```
Python 3.11+
├── httpx          # HTTP client (OANDA API)
├── pandas         # Data manipulation
├── pandas-ta      # Technical indicators
├── python-dotenv  # Environment variables
├── loguru         # Structured logging
└── sqlite3        # Database (built-in)
```

---

## Folder Struktura

```
Dev/
├── PROJECT.md          # Ovaj fajl - glavni kontekst
├── ARCHITECTURE.md     # Detaljna arhitektura
├── PROGRESS.md         # Praćenje napretka
├── PHASE-1.md          # Faza 1 tasks
├── PHASE-2.md          # Faza 2 tasks (kreirati kasnije)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
│
├── src/                # Izvorni kod
│   ├── trading/        # Trading logika
│   ├── market/         # Market data
│   ├── analysis/       # AI analiza
│   └── utils/          # Helpers
│
├── scripts/            # CLI skripte
├── data/               # SQLite + cache
├── logs/               # Log files
└── tests/              # Unit tests
```

---

## Workflow

1. **Claude čita PROJECT.md** za kontekst
2. **Provjeri PROGRESS.md** za trenutni status
3. **Otvori PHASE-X.md** za aktivne taskove
4. **Implementiraj** prema specifikaciji
5. **Ažuriraj PROGRESS.md** nakon svakog taska

---

## OANDA API Reference

```
Demo Base URL: https://api-fxpractice.oanda.com
Live Base URL: https://api-fxtrade.oanda.com

Key Endpoints:
GET  /v3/accounts/{id}              - Account info
GET  /v3/accounts/{id}/pricing      - Current prices
POST /v3/accounts/{id}/orders       - Place order
GET  /v3/accounts/{id}/positions    - Open positions
PUT  /v3/accounts/{id}/positions/{instrument}/close
```

---

## Links

- [OANDA API Docs](https://developer.oanda.com/rest-live-v20/introduction/)
- [OANDA Demo Account](https://www.oanda.com/eu-en/trading/demo-account/)
- Brainstorming: `../Brainstorming/`

---

*Verzija: 1.0 | Kreirano: 2026-01-30*
