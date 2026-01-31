# AI TRADER - Claude Session Context

> **VAZNO:** Ovaj fajl sluzi kao kontekst za Claude Code. Citaj ga na pocetku svake sesije.

---

## Sto je ovaj projekt?

**AI Trader** je automatizirani forex trading sustav koji koristi:
- **Claude Code CLI** kao sucelje
- **Claude AI** za analizu trzista
- **MetaTrader 5** kao broker (Python API) - **NOVO! Zamjena za OANDA**
- **Python** kao runtime

**Vlasnik:** Sirius Grupa d.o.o.
**Svrha:** Interni sustav za forex trading s AI asistencijom

---

## Trenutni Status (2026-01-31)

| Faza | Status | Opis |
|------|--------|------|
| Faza 1: Foundation | DONE | Config, logging, database |
| Faza 2: Core Trading | DONE | Orders, position sizing, risk management |
| Faza 3: AI Integration | DONE | Indicators, sentiment, adversarial, interface |
| Faza 3.5: MT5 Integration | DONE | **MetaTrader 5 umjesto OANDA** |
| Faza 3.6: Web Dashboard | DONE | **Streamlit web UI** |
| Faza 4.1: Backtesting | DONE | Walk-forward backtesting |
| Faza 4.2: Auto Learning | DONE | **Automatsko ucenje iz gresaka** |
| Faza 4.3: UX Improvements | DONE | **Tooltips, Onboarding, Notifications** |
| Faza 4.4: Performance Analytics | DONE | **Trading statistike i grafovi** |
| Faza 4.5: Docs & Monitoring | DONE | **README.md, Error tracking** |
| Faza 4.6: Risk Validation Gate | DONE | **Enforced risk checks** |
| Faza 4.7: SMC Knowledge Integration | DONE | **56 PDF-ova, 7 knowledge, 3 skills** |
| Faza 4.8: Security Fixes | DONE | **Weekly drawdown, auto-reset, bypass removal** |
| Faza 4.9: Remote Access | DONE | **Tailscale VPN, auto-start, mobile access** |
| Faza 4.10: Skill Buttons + BTC | DONE | **Vizualni gumbi, BTC/USD kripto** |
| Faza 4: Production | IN PROGRESS | Live testing |

**Ukupni napredak: ~100%**

---

## VAZNO: MT5 Integracija (Session 2)

**OANDA REST API je zamijenjen s MetaTrader 5 Python API!**

### MT5 Credentials (konfigurirano u .env)
```
MT5_LOGIN=62859209
MT5_PASSWORD=2NCsTdqe6Abu!Bj
MT5_SERVER=OANDA-TMS-Demo
```

### MT5 Account Info
- **Account:** 62859209
- **Balance:** 50,000 EUR (demo)
- **Server:** OANDA-TMS-Demo
- **Status:** TESTIRANO I RADI

### Promijenjeni fajlovi (MT5)
| Fajl | Promjena |
|------|----------|
| `src/trading/mt5_client.py` | **NOVI** - MT5 client (zamjena za oanda_client.py) |
| `src/trading/orders.py` | Koristi MT5 za tradanje |
| `src/utils/config.py` | Dodane MT5 varijable |
| `.env.example` | MT5 kredencijali |
| `.env` | Stvarni kredencijali (NE COMMITAJ!) |
| `requirements.txt` | Dodan MetaTrader5 paket |
| Svi `scripts/*.py` | Import promijenjen na MT5Client |
| `src/core/interface.py` | MT5 integracija + ASCII fix za Windows |

### Vazno za MT5
1. **MT5 terminal MORA biti otvoren** da Python API radi
2. **Tools > Options > Expert Advisors** - ukljuci:
   - Allow algorithmic trading
   - Allow DLL imports
3. Symbol format: `EURUSD.pro` (ne `EUR_USD`)
4. Automatska konverzija u kodu: `EUR_USD` <-> `EURUSD.pro`

---

## VAZNO: Risk Validation Gate (Session 9 + 11)

**`OrderManager.open_position()` sada ZAHTIJEVA risk validaciju!**

### Novi parametri (REQUIRED)
```python
result = om.open_position(
    instrument="EUR_USD",
    units=1000,
    stop_loss=1.0800,
    take_profit=1.0900,
    confidence=75,          # NOVO - REQUIRED
    risk_amount=500.0       # NOVO - REQUIRED
)
```

### Sto se provjerava (6 checks)
| Check | Limit | Status |
|-------|-------|--------|
| Confidence | >= 50% | ENFORCED |
| Risk per trade | Tier-based (1-3%) | ENFORCED |
| Daily drawdown | < 3% | ENFORCED + AUTO-RESET |
| **Weekly drawdown** | < 6% | **NOVO - Session 11** |
| Open positions | < 3 | ENFORCED |
| Spread | < 3 pips | ENFORCED |

### Security Fixes (Session 11)
- **Weekly drawdown SADA SE PROVJERAVA** (6% limit)
- **Auto-reset** daily/weekly P/L na UTC midnight/Monday
- **Global bypass flag UKLONJEN** - samo per-call bypass
- **Equity fallback UKLONJEN** - mora biti dostupan equity
- **Pip calculation FIX** - koristi MT5 symbol_info.digits
- **Volume rounding FIX** - koristi broker volume_step

### Bypass (samo za emergency)
```python
result = om.open_position(..., _bypass_validation=True)
# LOGIRA WARNING! Global bypass vise ne postoji.
```

### Promijenjeni fajlovi
| Fajl | Promjena |
|------|----------|
| `src/trading/orders.py` | Risk validation gate + security fixes |
| `src/trading/risk_manager.py` | Weekly drawdown + auto-reset |
| `src/utils/helpers.py` | get_pip_divisor() helper |
| `tests/test_risk_manager_extended.py` | **NOVI** - 14 testova |
| `tests/test_orders_security.py` | **NOVI** - 13 testova |

---

## Quick Start

```bash
cd "C:\Users\mglav\Projects\AI Trader\Dev"

# 1. Otvori MT5 terminal i cekaj da se ucita

# 2. Testiraj konekciju
python scripts/check_connection.py

# 3. Pokreni trader (CLI)
python trader.py

# 4. ILI pokreni Web Dashboard
streamlit run dashboard.py --server.address 0.0.0.0

# 5. Remote pristup s mobitela (Tailscale)
# URL: http://100.106.24.4:8501
```

### Trader Komande
```
help              - Pomoc
price EUR_USD     - Cijena
account           - Stanje racuna
positions         - Otvorene pozicije
analyze EUR/USD   - AI analiza
trade             - Trade workflow
emergency         - Zatvori sve pozicije
exit              - Izlaz
```

---

## Implementirano

### Foundation (Faza 1)
- `src/utils/config.py` - Konfiguracija (.env)
- `src/utils/logger.py` - Loguru logging
- `src/utils/helpers.py` - Utility funkcije
- `src/utils/database.py` - SQLite (trades, decisions, errors)

### Trading (Faza 2)
- `src/trading/mt5_client.py` - **MT5 API wrapper** (NOVO)
- `src/trading/orders.py` - Open/close/modify pozicije (MT5)
- `src/trading/position_sizer.py` - Risk tiers (1-3%)
- `src/trading/risk_manager.py` - Hard-coded limiti

### AI (Faza 3)
- `src/market/indicators.py` - EMA, RSI, MACD, ATR, S/R
- `src/analysis/sentiment.py` - Price action sentiment
- `src/analysis/adversarial.py` - Bull vs Bear engine
- `src/analysis/confidence.py` - Final score (0-100)
- `src/core/interface.py` - Interaktivni CLI
- `src/core/settings_manager.py` - Settings loader

### Web Dashboard (Faza 3.6)
- `dashboard.py` - Streamlit entry point
- `pages/` - Multi-page app (10 stranica)
- `components/` - Reusable UI komponente (9 komponenti)
- Pokretanje: `streamlit run dashboard.py`

### UX Components (Faza 4.3)
- `components/tooltips.py` - 40+ metrika s objasnjenjima
- `components/suggested_actions.py` - Pametne preporuke
- `components/position_health.py` - Health indikatori
- `components/status_bar.py` - Globalni status
- `components/notifications.py` - Smart alerts
- `components/onboarding.py` - Welcome wizard
- `components/help_resources.py` - Help & FAQ

### Performance Analytics (Faza 4.4)
- `pages/10_Performance.py` - Kompletna statistika
- Equity curve, drawdown, P/L distribution
- Performance by pair, by day/hour

### Settings System
```
settings/
├── system_prompt.md    # AI ponasanje (SMC Enhanced)
├── config.json         # Konfiguracija
├── skills/             # Trading skillovi
│   ├── scalping.md
│   ├── swing_trading.md
│   ├── news_trading.md
│   ├── smc_trading.md       # NOVO - Smart Money Concepts
│   ├── fvg_strategy.md      # NOVO - FVG trading
│   └── killzone_trading.md  # NOVO - Session trading
└── knowledge/          # Domensko znanje
    ├── forex_basics.md
    ├── risk_rules.md
    ├── lessons.md
    ├── market_structure.md  # NOVO - HTF/LTF alignment
    ├── fair_value_gap.md    # NOVO - FVG, iFVG
    ├── order_blocks.md      # NOVO - OB identification
    ├── liquidity.md         # NOVO - BSL/SSL, PDH/PDL
    ├── bos_cisd.md          # NOVO - BOS vs CISD
    ├── entry_models.md      # NOVO - 3 ICT modela
    └── session_trading.md   # NOVO - Killzone strategies
```

### Automatic Learning System (Faza 4.2) - NOVO
- `src/analysis/error_analyzer.py` - Kategoriza greske (8 kategorija)
- `src/trading/trade_lifecycle.py` - Centralni handler za zatvaranje tradea
- Automatski zapisuje greske u `errors` tablicu za RAG
- Automatski generira lekcije u `lessons.md` za znacajne gubitke

---

## Risk Management (HARD-CODED)

```
Confidence 90-100%: Max 3% risk
Confidence 70-89%:  Max 2% risk
Confidence 50-69%:  Max 1% risk
Confidence < 50%:   NE TRADATI

Max daily drawdown:  3%
Max weekly drawdown: 6%
Max positions:       3
```

---

## Sljedece (Faza 4 - Ostalo)

Kada korisnik pokrene novu sesiju, nastavi s:

1. ~~Backtesting modul~~ - DONE
2. ~~Automatsko ucenje iz gresaka~~ - DONE
3. ~~Performance analytics~~ - DONE
4. ~~UX improvements~~ - DONE (3 faze)
5. ~~Documentation~~ - DONE (README.md)
6. ~~Error monitoring~~ - DONE
7. **Live trading test** - prvi pravi tradeovi na demo

---

## Session Log

### Session 1 (2026-01-30)
- Faza 1-3 implementirane
- OANDA client kreiran (nije testiran - nedostajali credentials)

### Session 2 (2026-01-30)
- **MT5 integracija ZAVRSENA**
- Zamijenjen OANDA s MetaTrader 5
- Konfiguriran account 62859209
- Testirano i RADI:
  - Konekcija
  - Dohvat cijena
  - Account info
  - trader.py interface
- Fixed Windows emoji encoding issues

### Session 3 (2026-01-30)
- **Web Dashboard ZAVRSEN**
- Streamlit web UI s 7 stranica
- Chat interface s AI komandama
- Technical analysis s chartovima
- **Skills/Knowledge EDITOR** - Create/Edit/Delete kroz UI
- System Prompt editor s markdown preview
- Dark theme
- CLI i dalje radi uz web

### Session 4 (2026-01-30)
- **Backtesting ZAVRSEN**
- Walk-forward simulation engine
- Performance metrike (Sharpe, Sortino, Win Rate, etc.)
- Equity curve i drawdown charts
- Save/load reports

### Session 5 (2026-01-31)
- **Automatsko Ucenje iz Gresaka ZAVRSENO**
- `src/analysis/error_analyzer.py` - 8 kategorija gresaka
- `src/trading/trade_lifecycle.py` - centralni handler
- Automatski zapisuje u `errors` tablicu (RAG)
- Automatski generira lekcije u `lessons.md`
- Integracija u orders.py, interface.py, 4_Positions.py
- Test suite: `test_learning_system.py` - 6/6 testova prolazi

### Session 6 (2026-01-31)
- **UX Poboljsanja Faza 1 ZAVRSENA**
- `components/tooltips.py` - 40+ metrika s objasnjenjima
- `components/suggested_actions.py` - pametne preporuke akcija
- Kontekstualni tooltipovi na svim metrikama
- "Objasni jednostavno" sekcije za pocetnike
- Suggested Actions kartice na Dashboard
- Windows emoji kompatibilnost popravljena

### Session 7 (2026-01-31)
- **UX Poboljsanja Faza 2 ZAVRSENA**
- `pages/9_Learn.py` - Edukativna stranica za pocetnike
- `components/position_health.py` - Health indikatori
- `components/status_bar.py` - Globalni status bar
- Simple/Detailed toggle na Analysis i Backtest

### Session 8 (2026-01-31)
- **UX Poboljsanja Faza 3 ZAVRSENA**
- `components/onboarding.py` - Welcome Wizard (5 koraka)
- `components/notifications.py` - Pametni notification sustav
- `components/help_resources.py` - Help & Resources
- **Performance Analytics ZAVRSENA**
- `pages/10_Performance.py` - Kompletna trading statistika
- **Documentation & Monitoring ZAVRSENO**
- `README.md` - Kompletna dokumentacija
- `src/utils/monitoring.py` - Error tracking
- `pages/11_Monitoring.py` - System health UI
- **Database Browser ZAVRSEN**
- `pages/12_Database.py` - SQLite GUI s SQL editorom
- **Bug fixes:** MT5 connection status konzistentnost

### Session 9 (2026-01-31)
- **Risk Validation Gate ZAVRSEN**
- `OrderManager.open_position()` sada ZAHTIJEVA risk validaciju
- Novi parametri: confidence, risk_amount
- 5/5 testova prolazi

### Session 10 (2026-01-31)
- **SMC Knowledge Integration ZAVRSEN**
- Hybrid Mode: 5 paralelnih agenata za ekstrakciju iz 56 PDF-ova
- 7 novih knowledge fajlova kreirano:
  - market_structure.md, fair_value_gap.md, order_blocks.md
  - liquidity.md, bos_cisd.md, entry_models.md, session_trading.md
- 3 nova skill fajla kreirano:
  - smc_trading.md, fvg_strategy.md, killzone_trading.md
- system_prompt.md azuriran s SMC workflow (11 koraka)
- AI sada razumije: FVG, OB, BOS, CISD, Liquidity, Killzones

### Session 11 (2026-01-31)
- **Security Fixes ZAVRSENI** - 6 kriticnih bugova popravljeno
- Weekly drawdown check DODAN (6% limit sada se PROVJERAVA)
- Auto-reset daily/weekly P/L na UTC granicama
- Global bypass flag UKLONJEN (sigurnosni rizik)
- Equity fallback UKLONJEN (50k default bio opasan)
- Pip calculation FIX za sve instrument tipove
- Volume rounding FIX za tocno poravnanje s brokerom
- 32 testa prolazi (14 novih + 13 novih + 5 postojecih azurirano)
- **Security score: 83/100 -> 92/100**

### Session 12 (2026-01-31)
- **Remote Access ZAVRSEN**
- Tailscale VPN instaliran na PC i Samsung S24
- PC IP: `100.106.24.4`, Mobile IP: `100.74.221.115`
- Zero-config mesh VPN (WireGuard encrypted)
- Dashboard dostupan s mobitela: `http://100.106.24.4:8501`
- Auto-start skripta za Windows Startup
- `start_dashboard.bat` + `start_dashboard_hidden.vbs`

### Session 13 (2026-01-31)
- **Skill Buttons ZAVRSENI**
- Nova komponenta: `components/skill_buttons.py`
- 6 vizualnih gumba: SMC, FVG, Killzone, Scalping, Swing, News
- Dashboard: Trading Strategies sekcija s karticama
- Chat: Skill gumbi u sidebaru s pair selectorom
- **BTC/USD podrska ZAVRSENA**
- BTCUSD simbol mapiran (bez .pro sufiksa)
- Pip value = 1.0 za kripto
- Spread kalkulacija prilagodena
- Dostupno u Chat, Analysis, Backtest
- **Tailscale Funnel** za javni pristup
- Public URL: `https://mgpc.taild09bbd.ts.net/`
- **Git repozitorij inicijaliziran**
- Initial commit: 171 fajlova, 987k linija

---

## Dashboard Stranice

| # | Stranica | Opis |
|---|----------|------|
| 1 | Dashboard | Account overview, Suggested Actions |
| 2 | Chat | AI conversation interface |
| 3 | Analysis | Technical analysis + Simple/Detailed |
| 4 | Positions | Position management + Health |
| 5 | History | Trade history |
| 6 | Settings | Configuration editor |
| 7 | Skills | Skills/Knowledge/Prompt editor |
| 8 | Backtest | Walk-forward backtesting |
| 9 | Learn | Educational content |
| 10 | Performance | Trading statistics & analytics |
| 11 | Monitoring | System health, errors, alerts |
| 12 | Database | SQLite browser, queries, maintenance |

---

## Kljucni fajlovi

| Fajl | Svrha |
|------|-------|
| `CLAUDE_CONTEXT.md` | Ovaj fajl - session kontekst |
| `PROGRESS.md` | Detaljan napredak |
| `.env` | MT5 credentials (NE COMMITAJ!) |
| `trader.py` | CLI Entry Point |
| `dashboard.py` | WEB Dashboard Entry Point |
| `start_dashboard.bat` | Auto-start batch skripta |
| `start_dashboard_hidden.vbs` | Hidden launcher (Startup) |
| `src/trading/mt5_client.py` | MT5 API wrapper |

---

*Zadnje azuriranje: 2026-01-31 | Session 13 - Skill Buttons + BTC/USD DONE*
