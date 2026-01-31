# FAZA 3: AI Integration + Interface

> Cilj: AI analiza, interaktivno sučelje, system prompt i skills sustav

---

## Overview

Faza 3 dodaje:
1. **Technical Indicators** - pandas-ta za tehničku analizu
2. **Sentiment Analysis** - analiza tržišnog sentimenta
3. **Adversarial Thinking** - Bull vs Bear debate
4. **Interactive Interface** - CLI sučelje za komunikaciju
5. **Settings System** - system prompt + skills za AI ponašanje

---

## Tasks

### Task 3.1: Market Indicators
- [ ] `src/market/indicators.py`
  - [ ] EMA, SMA, RSI, MACD, ATR
  - [ ] Support/Resistance detection
  - [ ] Trend identification

### Task 3.2: Sentiment Analysis
- [ ] `src/analysis/sentiment.py`
  - [ ] Price action sentiment (-1 to +1)
  - [ ] Trend strength scoring
  - [ ] Momentum analysis

### Task 3.3: Adversarial Engine
- [ ] `src/analysis/adversarial.py`
  - [ ] Bull case generator
  - [ ] Bear case generator
  - [ ] Verdict evaluator

### Task 3.4: Confidence Calculator
- [ ] `src/analysis/confidence.py`
  - [ ] Combine all scores
  - [ ] Weight factors
  - [ ] Final confidence (0-100)

### Task 3.5: AI Prompts
- [ ] `src/analysis/prompts.py`
  - [ ] Analysis prompt template
  - [ ] Bull/Bear prompt templates
  - [ ] Trade decision prompt

### Task 3.6: Settings System
- [ ] `settings/system_prompt.md` - glavni AI prompt
- [ ] `settings/skills/` - dodatni skill-ovi
- [ ] `settings/knowledge/` - domensko znanje
- [ ] `src/core/settings_manager.py` - učitavanje settings-a

### Task 3.7: Interactive Interface
- [ ] `src/core/interface.py` - main UI
- [ ] `trader.py` - entry point
- [ ] Menu system
- [ ] Command handling
- [ ] AI conversation mode

### Task 3.8: CLI Scripts
- [ ] `scripts/analyze_pair.py` - full AI analiza
- [ ] `scripts/daily_report.py` - dnevni izvještaj

---

## Settings Structure

```
settings/
├── system_prompt.md      # Glavni AI personality i ponašanje
├── config.json           # UI i behavior konfiguracija
│
├── skills/               # Dodatni skill-ovi
│   ├── README.md
│   ├── scalping.md       # Scalping strategija
│   ├── swing_trading.md  # Swing trading
│   └── news_trading.md   # Trading oko vijesti
│
└── knowledge/            # Domensko znanje
    ├── README.md
    ├── forex_basics.md   # Forex osnove
    ├── risk_rules.md     # Tvoja pravila rizika
    └── lessons.md        # Naučene lekcije
```

---

## Interface Commands

```
AI Trader> help              # Pomoć
AI Trader> analyze EUR/USD   # Analiziraj par
AI Trader> price EUR/USD     # Trenutna cijena
AI Trader> account           # Status računa
AI Trader> positions         # Otvorene pozicije
AI Trader> trade             # Započni trade workflow
AI Trader> close EUR/USD     # Zatvori poziciju
AI Trader> emergency         # Zatvori sve
AI Trader> report            # Dnevni izvještaj
AI Trader> settings          # Otvori settings
AI Trader> skills            # Lista skill-ova
AI Trader> chat              # Slobodan razgovor s AI
AI Trader> exit              # Izlaz
```

---

*Verzija: 1.0 | Kreirano: 2026-01-30*
