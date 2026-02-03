# AI TRADER - Claude Session Context

> **VAZNO:** Ovaj fajl sluzi kao kontekst za Claude Code. Citaj ga na pocetku svake sesije.

---

## Sto je ovaj projekt?

**AI Trader** je **FULL AUTO scalping bot** koji koristi:
- **Claude Code CLI** kao sucelje
- **Claude AI** za analizu trzista + validaciju + override odluke
- **MetaTrader 5** kao broker (Python API)
- **Python** kao runtime
- **Streamlit** za Web Dashboard

**Vlasnik:** Sirius Grupa d.o.o.
**Svrha:** Automatizirani forex trading s AI analizom
**Cilj:** MIN 200 EUR profit dnevno

---

## Trenutni Status (2026-02-03)

| Faza | Status | Opis |
|------|--------|------|
| Faza 1-4 | DONE | Foundation, Core, AI, Dashboard |
| Faza 5: Full Auto Trading | DONE | Automatizirani scalping bot |
| Faza 5.1-5.4 | DONE | AI Visibility, Learning, Validation |
| Faza 5.5: 24/7 Daemon Mode | DONE | Heartbeat + Watchdog |
| Faza 5.6: Self-Tuning | DONE | AI Override za rejected signale |
| Faza 5.7: Adaptive Settings | DONE | Auto-optimizacija postavki |
| Faza 6: Modern AI Upgrades | DONE | Market Regime, External Sentiment, Walk-Forward |
| **Faza 7: Self-Upgrade System** | **DONE** | **AI generira filtere iz losing patterna** |

**Ukupni napredak: 100% - SELF-LEARNING AI TRADING SUSTAV!**

---

## NOVO: Session 24 (2026-02-03) - Self-Upgrade System

### Sto je implementirano?

**AI sustav koji automatski uci iz gresaka i generira nove filtere!**

1. **Performance Analyzer** - Analizira zadnjih 7 dana, identificira losing patterns
2. **Code Generator** - Template-based Python kod s safety constraints
3. **Code Validator** - AST parsing + security checks (blokira os, exec, open)
4. **Upgrade Executor** - Walk-forward backtest prije deploya
5. **Upgrade Manager** - Orchestrira daily cycle, max 3 proposals

### Deployment Criteria (filter mora zadovoljiti SVE)

| Kriterij | Zahtjev | Razlog |
|----------|---------|--------|
| Block rate | ≤ 50% | Ne smije blokirati vecinu signala |
| Accuracy | > 50% | Mora blokirati vise losera nego winnera |
| Robustness | ≥ 60% | Kombinirani weighted score |
| Min signals | ≥ 20 | Dovoljno podataka za backtest |

### Test Results

```
ALL TESTS PASSED (9/9)
- BaseFilter, FilterRegistry, Builtin Filters
- PerformanceAnalyzer (6 patterns found)
- CodeValidator (blocks dangerous code)
- CodeGenerator (generates valid Python)
- UpgradeManager, Filter Chain, Full Cycle
```

### Trenutno detektirani patterni

| Pattern | Win Rate | Status |
|---------|----------|--------|
| regime=UNKNOWN | 9.1% | Nema historical data |
| session=london | 6.2% | Block rate 97% (previse!) |
| EUR_USD+LONG | 0% | Low sample size |

### Novi fajlovi

```
src/upgrade/                      # Self-Upgrade System
├── base_filter.py                # Abstract filter class
├── filter_registry.py            # Filter management
├── performance_analyzer.py       # Loss pattern analysis
├── code_generator.py             # Safe code generation
├── code_validator.py             # AST security check
├── upgrade_executor.py           # Backtest + deploy
└── upgrade_manager.py            # Main orchestrator

src/filters/                      # Trading filters
├── builtin/                      # Built-in filters
│   ├── consecutive_loss_filter.py
│   └── low_confidence_direction_filter.py
└── ai_generated/                 # AI-generated filters
```

### Rucno testiranje

```bash
# Run test suite
python test_upgrade_system.py

# Force upgrade cycle
python -c "
import asyncio
from src.upgrade.upgrade_manager import get_upgrade_manager
asyncio.run(get_upgrade_manager().run_daily_upgrade_cycle())
"
```

---

## Session 23 (2026-02-03) - News API Integration

### Sto je implementirano?

1. **News Provider System** (`src/analysis/news_providers.py`)
   - Multi-provider arhitektura s fallback podrškom
   - Automatsko dohvaćanje economic calendar podataka
   - Async refresh s caching mehanizmom

2. **Dostupni provideri:**
   | Provider | API Key | Opis |
   |----------|---------|------|
   | Finnhub | Potreban (besplatan) | 60 calls/min, [finnhub.io](https://finnhub.io/register) |
   | FMP | Potreban (besplatan) | 250 calls/day, [financialmodelingprep.com](https://site.financialmodelingprep.com/developer) |
   | ForexFactory | Potreban | JBlanked API |
   | **Recurring** | **NE TREBA** | Auto-generira NFP, FOMC, ECB, BoE, BoJ |

3. **UI konfiguracija** (Settings → News API tab)
   - Unos API ključeva
   - Enable/disable providera
   - Manual refresh button
   - Calendar status pregled

4. **NewsFilter integracija**
   - `refresh_from_api()` - async refresh iz providera
   - `get_calendar_status()` - status za UI
   - Auto-refresh u pozadini

### Novi fajlovi

```
src/analysis/news_providers.py    # Provider sustav (Finnhub, FMP, FF, Recurring)
settings/news_providers.json      # Provider konfiguracija
```

### Korištenje

```python
# Programski
from src.analysis import refresh_news_calendar, set_finnhub_api_key

set_finnhub_api_key("your-api-key")
events = await refresh_news_calendar(force=True)

# Ili preko UI
# Settings → News API → unesi API key → Save → Refresh Now
```

### Recurring Provider (radi bez API ključa!)

Automatski generira poznate high-impact evente:
- **USD:** Non-Farm Payrolls (prvi petak), FOMC, CPI, Retail Sales
- **EUR:** ECB odluke, German ZEW
- **GBP:** BoE odluke, UK CPI
- **JPY:** BoJ odluke

---

## Session 22 (2026-02-03) - Modern AI Trading Upgrades (Phase 6)

### Sto je implementirano?

1. **Market Regime Detection** (Phase 1)
   - ADX + Bollinger Bands za prepoznavanje trzisnog rezima
   - 4 rezima: TRENDING, RANGING, VOLATILE, LOW_VOLATILITY
   - Blokira LOW_VOLATILITY i VOLATILE (prevelik rizik)
   - TRENDING = samo S trendom, RANGING = samo kod S/R
   - `src/market/indicators.py` - novi indikatori
   - `src/trading/auto_scanner.py` - regime filter

2. **External Sentiment Integration** (Phase 2)
   - Claude-powered news analysis
   - VIX correlation (risk-on/risk-off)
   - Economic calendar sentiment
   - `src/sentiment/` - novi direktorij s providerima
   - Weights: PA 30%, News 35%, VIX 15%, Calendar 20%

3. **Walk-Forward Validation** (Phase 3)
   - Proper out-of-sample testing
   - Rolling train/test windows
   - Monte Carlo simulation za confidence intervals
   - `src/backtesting/walk_forward.py` - validator

4. **Regime-Aware Learning** (Phase 4)
   - Learning engine prati win rate po rezimu
   - Confidence adjustment baziran na rezimu
   - Pattern tracking: `regime_TRENDING_EUR_USD`

### Nove konfiguracije

```json
"market_regime": {
  "enabled": true,
  "block_low_volatility": true,
  "block_volatile": true,
  "trending_only_with_trend": true,
  "ranging_require_sr": true
},
"external_sentiment": {
  "enabled": true,
  "weights": {"price_action": 0.30, "news_claude": 0.35, "vix": 0.15, "calendar": 0.20}
}
```

### Novi fajlovi (Phase 6)

```
src/sentiment/                    # External Sentiment Integration
├── __init__.py
├── base_provider.py              # Abstract provider interface
├── aggregator.py                 # Combines all sentiment sources
└── providers/
    ├── news_provider.py          # Claude-powered news analysis
    ├── vix_provider.py           # VIX risk correlation
    └── calendar_provider.py      # Economic calendar sentiment

src/backtesting/walk_forward.py   # Walk-Forward Validation + Monte Carlo
src/market/indicators.py          # ADX, Bollinger Bands, Regime Detection
src/utils/database.py             # market_regimes tablica
```

### Ocekivano poboljsanje
- +10-20% win rate (konzervativna procjena)
- Manje tradeova u losim uvjetima (regime filter)
- Bolja kvaliteta signala (external sentiment)
- Robustniji backtest (walk-forward validation)

---

## Session 21 (2026-02-03) - Adaptive Settings + Optimizacija

### Sto je implementirano?

1. **Adaptive Settings Manager** (`src/analysis/adaptive_settings.py`)
   - Automatski prilagodava postavke na temelju performansi
   - Analizira win rate, stop hunts, R:R doseg
   - Primjenjuje promjene nakon svakog zatvorenog tradea

2. **Auto-Reconnect za MT5** (`src/trading/mt5_client.py`)
   - `_ensure_connected()` automatski reconnecta kad veza padne
   - `reconnect()` metoda za force reconnect
   - Nema vise "No IPC connection" errora

3. **Konzervativne postavke za profitabilnost**
   - Confidence threshold: 75%
   - Risk per trade: 1%
   - Target R:R: 2:1
   - Strogi MTF check (55%)
   - AI Override DISABLED

4. **Sync & Learn automatizacija**
   - Svaki 5. scan sync-a zatvorene pozicije
   - Automatski uci iz svakog tradea
   - Self-tuning se pokrece nakon ucenja

### Promjene u postavkama

| Postavka | Prije | Sada |
|----------|-------|------|
| min_confidence_threshold | 35% | 75% |
| risk_per_trade_percent | 2.0% | 1.0% |
| target_rr | 1.5 | 2.0 |
| max_spread_pips | 4.0 | 2.5 |
| MTF threshold | 85% | 55% |
| AI Override | enabled | disabled |

### Lekcije naucene

1. **Agresivne postavke = gubici** - 22% win rate, -1163 EUR
2. **Kvaliteta > Kvantiteta** - manje tradeova, bolji rezultati
3. **Samo S TRENDOM** - counter-trend = gubitak
4. **Manje pozicije** - max 5 umjesto 10

---

## Account Status

```
Account: 62859209 (OANDA-TMS-Demo)
Balance: ~48,720 EUR
Started: 50,000 EUR
Realized P/L: ~-1,280 EUR (lekcije naucene!)
```

---

## Quick Start

```bash
cd "C:\Users\mglav\Projects\AI Trader\Dev"

# 1. PRVO pokreni MT5 terminal i ulogiraj se!

# 2. Pokreni auto-trading
python run_auto_trading.py

# ILI za 24/7 daemon mode
python run_daemon.py

# ILI za web dashboard
python -m streamlit run dashboard.py
```

**VAZNO:** MT5 terminal MORA biti pokrenut PRIJE Python servisa!

---

## Kljucne postavke za profitabilnost

```json
{
  "enabled": true,
  "min_confidence_threshold": 75,
  "risk_per_trade_percent": 1.0,
  "max_concurrent_positions": 5,
  "max_daily_trades": 20,
  "scalping": {
    "target_rr": 2.0,
    "max_spread_pips": 2.5,
    "max_sl_pips": 15.0
  },
  "ai_validation": {
    "enabled": true,
    "reject_on_failure": true
  },
  "ai_override": {
    "enabled": false
  }
}
```

---

## Arhitektura - Modern AI Trading Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        AUTO-TRADING SERVICE                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  SCAN → REGIME → ANALYZE → FILTER CHAIN → AI VALIDATE → EXECUTE          │
│    │       │         │           │                           │           │
│    │       │         │           │                           v           │
│    │       │         │           │                     ┌──────────┐      │
│    │       │         │           └─ Builtin filters ──>│  CLOSE   │      │
│    │       │         │           └─ AI-generated ─────>└────┬─────┘      │
│    │       │         │                                      │            │
│    │       │         └── Technical + Sentiment ─────────────┤            │
│    │       │                                                v            │
│    │       └── Market Regime ──────────────────────────>┌──────────┐     │
│    │                                                    │  LEARN   │     │
│    └── 12 instruments every 15s                         └────┬─────┘     │
│                                                              │           │
│                                                              v           │
│  ┌─────────────────── SELF-UPGRADE SYSTEM (daily) ───────────────────┐   │
│  │  Analyze losses → Generate filter → Validate → Backtest → Deploy  │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘

Cilj: 200 EUR/dan = 4-5 kvalitetnih tradeova po 40-50 EUR
```

## Arhitektura - Self-Upgrade System

```
Every 24 hours:

  ┌─────────────────────────────────────────────────────────────────────┐
  │                    PERFORMANCE ANALYZER                              │
  │  Analyze last 7 days → Identify losing patterns                     │
  │  (instrument, session, regime, direction, combined)                 │
  └─────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    v
  ┌─────────────────────────────────────────────────────────────────────┐
  │                    CODE GENERATOR                                    │
  │  Template-based Python code with safety constraints                 │
  │  ALLOWED: dataclasses, typing, datetime, math, statistics           │
  │  BLOCKED: os, sys, subprocess, exec, eval, open, socket, requests   │
  └─────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    v
  ┌─────────────────────────────────────────────────────────────────────┐
  │                    CODE VALIDATOR                                    │
  │  AST parsing → Import whitelist → Dangerous function detection      │
  │  → Sandbox execution test → BaseFilter inheritance check            │
  └─────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    v
  ┌─────────────────────────────────────────────────────────────────────┐
  │                    UPGRADE EXECUTOR                                  │
  │  Walk-forward backtest on historical signals                        │
  │  Requirements: Block rate ≤50%, Accuracy >50%, Robustness ≥60%      │
  └─────────────────────────────────┬───────────────────────────────────┘
                                    │
                        ┌───────────┴───────────┐
                        │                       │
                   PASS │                       │ FAIL
                        v                       v
              ┌─────────────────┐     ┌─────────────────┐
              │ Deploy to       │     │ Log & discard   │
              │ ai_generated/   │     │                 │
              └────────┬────────┘     └─────────────────┘
                       │
                       v
              ┌─────────────────────────────────────────┐
              │  Monitor performance → Auto-rollback    │
              │  if win_rate drops >10% or 5 losses     │
              └─────────────────────────────────────────┘
```

---

## Kljucni fajlovi (prioritet)

| # | Fajl | Svrha |
|---|------|-------|
| 1 | `CLAUDE_CONTEXT.md` | Ovaj fajl - session kontekst |
| 2 | `settings/auto_trading.json` | Trading konfiguracija |
| 3 | `src/services/auto_trading_service.py` | Main loop + sync + upgrade cycle |
| 4 | `src/trading/auto_scanner.py` | Market scanner + MTF + Regime + Filter chain |
| 5 | `src/upgrade/upgrade_manager.py` | Self-Upgrade System orchestrator |
| 6 | `src/upgrade/filter_registry.py` | Filter chain management |
| 7 | `src/market/indicators.py` | Technical + ADX + Bollinger + Regime |
| 8 | `src/sentiment/aggregator.py` | External sentiment (VIX, News, Calendar) |
| 9 | `src/analysis/learning_engine.py` | Pattern learning + Regime-aware |
| 10 | `src/trading/mt5_client.py` | MT5 connection + auto-reconnect |
| 11 | `src/backtesting/walk_forward.py` | Walk-forward validation + Monte Carlo |
| 12 | `src/analysis/llm_engine.py` | AI validation rules |
| 13 | `src/analysis/news_providers.py` | News API providers (Finnhub, FMP, Recurring) |
| 14 | `test_upgrade_system.py` | Self-Upgrade test suite |

---

## Troubleshooting

### "No IPC connection" error?
```bash
# 1. Provjeri da je MT5 terminal pokrenut i ulogiran
# 2. Restartaj Python servis NAKON sto je MT5 upaljen
python run_auto_trading.py
```

### Previse gubitaka?
```bash
# Pauziraj trading
python -c "
import json
with open('settings/auto_trading.json', 'r') as f:
    cfg = json.load(f)
cfg['enabled'] = False
with open('settings/auto_trading.json', 'w') as f:
    json.dump(cfg, f, indent=2)
print('Trading PAUSED')
"
```

### Provjeri stanje
```bash
python -c "
import MetaTrader5 as mt5
mt5.initialize()
acc = mt5.account_info()
pos = mt5.positions_get()
print(f'Balance: {acc.balance:.2f} EUR')
print(f'Equity: {acc.equity:.2f} EUR')
print(f'Positions: {len(pos)}')
for p in pos:
    print(f'  {p.symbol} {\"LONG\" if p.type==0 else \"SHORT\"} P/L: {p.profit:+.2f}')
"
```

---

## Session Log

### Session 24 (2026-02-03) - Self-Upgrade System
- **Performance Analyzer** - Identificira losing patterns (6 pronadeno)
- **Code Generator** - Template-based Python s safety constraints
- **Code Validator** - AST + security checks (blokira os, exec, open, eval)
- **Upgrade Executor** - Walk-forward backtest, robustness score
- **Upgrade Manager** - Daily cycle, max 3 proposals, auto-rollback
- **Filter Registry** - Filter chain integration u auto_scanner
- **Builtin Filters** - consecutive_loss, low_confidence_direction
- **Novi direktorij:** `src/upgrade/` (8 fajlova)
- **Novi direktorij:** `src/filters/` (builtin + ai_generated)
- **Test suite:** `test_upgrade_system.py` - 9/9 PASSED
- **Config:** `self_upgrade` sekcija u auto_trading.json
- **Rezultat:** AI automatski generira filtere iz losing patterna

### Session 23 (2026-02-03) - News API Integration
- **News Provider System** - Multi-provider s fallback (Finnhub, FMP, FF, Recurring)
- **Recurring Provider** - Auto-generira high-impact evente bez API kljuca
- **Settings UI** - News API tab za konfiguraciju
- **NewsFilter integracija** - async refresh, status tracking
- **Novi fajl:** `src/analysis/news_providers.py`
- **Rezultat:** Automatsko dohvacanje economic calendar podataka

### Session 22 (2026-02-03) - Modern AI Trading Upgrades (Phase 6)
- **Market Regime Detection** - ADX + Bollinger za TRENDING/RANGING/VOLATILE/LOW_VOL
- **External Sentiment** - VIX + News (Claude) + Calendar (ENABLED!)
- **Walk-Forward Validation** - Out-of-sample testing + Monte Carlo
- **Regime-Aware Learning** - Learning engine prati win rate po rezimu
- **Novi direktorij:** `src/sentiment/` s 6 novih fajlova
- **Novi modul:** `src/backtesting/walk_forward.py`
- **Rezultat:** Sustav sada ima naprednu analizu trzisnih uvjeta

### Session 21 (2026-02-03) - Adaptive Settings + Optimizacija
- **Adaptive Settings Manager** - auto-tuning postavki
- **MT5 Auto-Reconnect** - automatski reconnect kad veza padne
- **Konzervativne postavke** - 75% confidence, 1% risk, 2:1 R:R
- **Learning Engine improvements** - bolje sync-anje
- **Lekcija:** Agresivne postavke = gubici. Kvaliteta > kvantiteta.
- **Rezultat:** Postavke optimizirane za 200 EUR/dan cilj

### Session 20 (2026-02-03) - Self-Tuning AI Override
- AI Override Evaluator
- Tunable Settings s granicama

### Session 14-19 (2026-02-02)
- Full Auto Trading implementiran
- AI Visibility, Learning Loop
- 24/7 Daemon Mode

---

## Hard Limits (NIKAD se ne mogu zaobici!)

| Limit | Vrijednost |
|-------|------------|
| Max risk per trade | 3% |
| Max daily drawdown | 5% |
| Max weekly drawdown | 10% |
| Max concurrent positions | 10 |
| Max position size | 100,000 units |

---

*Zadnje azuriranje: 2026-02-03 | Session 24 - Self-Upgrade System TESTED & WORKING*
