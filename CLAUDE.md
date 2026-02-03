# AI Trader - Claude Instructions

> **CLAUDE:** Na pocetku sesije procitaj `Dev/CLAUDE_CONTEXT.md` za kompletan kontekst projekta.

---

## Quick Start

```bash
cd Dev
cat CLAUDE_CONTEXT.md   # Procitaj kontekst
```

## Projekt Status (2026-02-03)

| Faza | Status |
|------|--------|
| Faza 1-4 | DONE |
| Faza 5: Full Auto Trading | DONE |
| Faza 5.1-5.4: AI Visibility, Learning, Validation | DONE |
| Faza 5.5: 24/7 Daemon Mode | DONE |
| Faza 5.6: Self-Tuning (AI Override) | DONE |
| Faza 5.7: Adaptive Settings + Optimizacija | DONE |
| Faza 6: Modern AI Upgrades | DONE |
| Faza 6.1: News API Integration | DONE |
| **Faza 7: Self-Upgrade System** | **DONE** |

**NOVO: AI Self-Upgrade System - automatski generira i deploya filtere bazirane na losing patternima!**

## NOVO: Full Auto Trading (Session 14)

**Potpuno automatizirani scalping bot!**

### Pokretanje
```bash
cd Dev

# Web Dashboard (preporuceno za monitoring)
python -m streamlit run dashboard.py
# Idi na stranicu AutoTrading (13)

# 24/7 Daemon mode (preporuceno za autonomni rad)
python run_daemon.py

# ILI simple background servis (bez auto-restart)
python run_auto_trading.py
```

### Kljucne komponente
```
src/
├── core/auto_config.py           # Konfiguracija + RegimeConfig + SentimentConfig + SelfUpgradeConfig
├── trading/auto_scanner.py       # Market scanner + Regime filter + Filter chain
├── trading/auto_executor.py      # Trade executor
├── trading/emergency.py          # Emergency stop
├── market/indicators.py          # Technical + ADX + Bollinger + Regime Detection
├── sentiment/                    # External Sentiment (Phase 6)
│   ├── aggregator.py             # Combines all sources
│   └── providers/                # VIX, News, Calendar
├── backtesting/walk_forward.py   # Walk-Forward Validation + Monte Carlo
├── analysis/learning_engine.py   # Pattern learning + Regime-aware
├── upgrade/                      # Self-Upgrade System (Phase 7)
│   ├── base_filter.py            # Abstract filter class
│   ├── filter_registry.py        # Filter management
│   ├── performance_analyzer.py   # Loss pattern analysis
│   ├── code_generator.py         # Safe code generation
│   ├── code_validator.py         # AST security check
│   ├── upgrade_executor.py       # Backtest + deploy
│   └── upgrade_manager.py        # Main orchestrator
├── filters/                      # Trading filters
│   ├── builtin/                  # Built-in filters
│   └── ai_generated/             # AI-generated filters
├── services/
│   ├── auto_trading_service.py   # Main loop + upgrade cycle
│   ├── heartbeat.py              # Heartbeat manager
│   └── watchdog.py               # Watchdog monitor
└── strategies/scalping.py        # Scalping strategija

settings/auto_trading.json        # Config file (+ self_upgrade sekcija)
pages/13_AutoTrading.py           # UI Control Panel
run_auto_trading.py               # Simple runner
run_daemon.py                     # 24/7 daemon s auto-restart
```

### Kako radi
1. Scanner skenira 14 instrumenata svakih 15s
2. **Market Regime Check** - blokira LOW_VOLATILITY i VOLATILE
3. Analizira s Technical + **External Sentiment** (VIX, News, Calendar) + Adversarial
4. Kad je confidence >= threshold (50% learning / 65% production)
5. **Claude AI validira signal** (APPROVE/REJECT) ~3-4s
6. **AI Override** - ako signal odbijen (MTF, spread, R:R), AI može override-ati
7. Ako APPROVE, izvršava trade s risk management
8. Learning Mode prati win rate **po market režimu**

### Hard Limits (NIKAD se ne mogu zaobici)
- Max risk/trade: 3%
- Max daily drawdown: 5%
- Max weekly drawdown: 10%
- Max positions: 10

### Cooldown
- 3 gubitka u nizu = 30 min pauza
- Sprecava prekomjerno tradanje

## MT5 Integracija

- Account: `62859209`
- Server: `OANDA-TMS-Demo`
- Balance: `~48,720 EUR` (started 50,000)
- Status: **AKTIVNO TRGUJE**
- Cilj: **200 EUR/dan**

## Dashboard Stranice (13)

| # | Stranica | Opis |
|---|----------|------|
| 1 | Dashboard | Account overview + Auto status |
| 2 | Chat | AI analiza |
| 3 | Analysis | Technical analysis |
| 4 | Positions | Position management |
| 5 | History | Trade history |
| 6 | Settings | Konfiguracija |
| 7 | Skills | Skills/Knowledge editor |
| 8 | Backtest | Backtesting |
| 9 | Learn | Edukacija |
| 10 | Performance | Statistike |
| 11 | Monitoring | System health |
| 12 | Database | SQLite browser |
| **13** | **AutoTrading** | **Auto-trading Control Panel** |

## Kljucni fajlovi

| Prioritet | Fajl |
|-----------|------|
| 1 | `Dev/CLAUDE_CONTEXT.md` - Session kontekst |
| 2 | `Dev/settings/auto_trading.json` - Auto config |
| 3 | `Dev/src/services/auto_trading_service.py` - Main loop |
| 4 | `Dev/pages/13_AutoTrading.py` - UI |
| 5 | `Dev/run_daemon.py` - 24/7 daemon runner |
| 6 | `Dev/src/services/watchdog.py` - Auto-restart |

## Session 14 - Full Auto Trading (2026-02-02)

**Implementirano:**
- 8 novih fajlova
- Auto-scanner, auto-executor, emergency controller
- Cooldown mehanizam
- UI Control Panel
- **PRVI AUTO TRADE USPJESNO IZVRSHEN!**
  - USD/JPY LONG, 6000 units, Order #136294630

---

## Session 15 - AI Visibility Dashboard (2026-02-02)

**Implementirano:**
- **Activity Log sustav** - nova `activity_log` tablica
- **AI Thinking panel** - live view AI razmisljanja na AutoTrading stranici
- **Decision Trail** - detaljna povijest odluka po instrumentu
- **Bull/Bear Case** - AI objasnjava zasto da/ne za svaki signal
- **AUTO/MANUAL** indikator na pozicijama
- **Service Control** - START/STOP SERVICE buttoni
- **Config Fix** - Save Configuration sada ispravno sprema

**Sto korisnik sada vidi:**
- Real-time AI aktivnost (scanning, analyzing)
- Razlog odbijanja signala (spread, confidence, direction)
- Technical/Sentiment/Adversarial scoreove
- Detaljne bull/bear case objasnjenja
- Koje pozicije su AUTO vs MANUAL

**Modificirani fajlovi:**
- `src/utils/database.py` - activity_log tablica
- `src/trading/auto_scanner.py` - detaljno logging
- `src/trading/auto_executor.py` - execution logging
- `src/analysis/confidence.py` - bull_case/bear_case
- `pages/1_Dashboard.py` - AI Activity Feed
- `pages/13_AutoTrading.py` - AI Thinking, Decision Trail, Service Control
- `pages/4_Positions.py` - AUTO/MANUAL, AI reasoning

---

## Session 16 - Learning Loop Integration (2026-02-02)

**Implementirano:**
- **Learning Engine AKTIVAN** - sustav uci iz tradeova i primjenjuje znanje
- **Confidence Adjustment** - adjustira se na temelju pattern historije
- **Pattern Stats** - 12 tipova patterna (instrument, direction, session...)
- **Trade Blocking** - blokira instrumente s 5+ uzastopnih gubitaka

**Bug Fixes:**
- UNIQUE constraint (duplicate trade logging)
- Service state detection (activity_log based)
- Signal tracking (skip_reason logging)
- Position duplicate prevention (MT5 + DB)
- NaN values (MT5 history sync)

**Config promjene:**
- Uklonjeni: GBP_JPY, XAU_USD (nedostupni na MT5)
- MIN_TRADES_FOR_CRITICAL: 1 → 5
- MIN_TRADES_FOR_PATTERN: 2 → 3

**Modificirani fajlovi:**
- `src/trading/auto_scanner.py` - LearningEngine integration
- `src/trading/auto_executor.py` - DB position check
- `src/utils/database.py` - update_trade_source(), update_auto_signal_result()
- `src/analysis/learning_engine.py` - Threshold adjustments
- `pages/13_AutoTrading.py` - Service state from activity_log

---

## Session 17 - Scalping Improvements (2026-02-02)

- Multi-Timeframe Analysis (MTF)
- Market Structure Detection
- Killzone Detection
- News Calendar Filter
- Dynamic Spread Limits
- Trailing Stop / Break-Even

---

## Session 18 - Learning Mode + AI Validation (2026-02-02)

### Learning Mode
- **Adaptive thresholds** - agresivnije postavke za learning fazu
- **Progress tracking** - 0/50 tradeova do graduation
- **Auto-graduation** - automatski prelazak na production postavke
- **Konfigurabilan** - target trades, aggressive/production settings

### AI Validation (PRAVI AI!)
- **Claude validira SVAKI trade** prije izvršenja
- **APPROVE/REJECT** odluka s obrazloženjem
- **~3-4 sekunde** response time
- **Konfigurabilan** - enable/disable, reject on failure

### Arhitektura
```
Scanner → Signal (87%) → Claude validates → APPROVE → Execute
                                        → REJECT  → Skip
```

### Test Result
```
Signal found: GBP_USD LONG conf=87%
Requesting AI validation for GBP_USD LONG...
AI APPROVED: Technical indicators align with LONG direction...
```

### Novi fajlovi/promjene
- `auto_trading.json` - learning_mode + ai_validation sekcije
- `auto_config.py` - LearningModeConfig, AIValidationConfig
- `llm_engine.py` - validate_signal() metoda
- `auto_executor.py` - AI validation step
- `13_AutoTrading.py` - Learning Mode tab, AI config

---

## Session 19 - 24/7 Daemon Mode (2026-02-02)

**Implementirano:**
- **Heartbeat sustav** - piše status svakih 10 sekundi u `.heartbeat.json`
- **Watchdog service** - nadzire heartbeat i automatski restarta servis
- **Daemon runner** - `run_daemon.py` za 24/7 rad bez nadzora
- **Auto-restart** - max 5 restarta/sat (crash loop protection)
- **Graceful shutdown** - čeka do 10s za cleanup

### Pokretanje 24/7 moda

**Iz Dashboard-a (preporuceno):**
1. Otvori `python -m streamlit run dashboard.py`
2. Idi na stranicu **13 - AutoTrading**
3. Klikni **START DAEMON** button

**Ili iz terminala:**
```bash
cd Dev
python run_daemon.py
# Press Ctrl+C to stop
```

### Kako radi
1. `run_daemon.py` pokreće watchdog
2. Watchdog pokreće auto-trading kao subprocess
3. Heartbeat se piše svakih 10 sekundi
4. Watchdog provjerava heartbeat svakih 30 sekundi
5. Ako heartbeat stariji od 120s → automatski restart
6. Max 5 restarta/sat (sprječava crash loop)

### Novi fajlovi
```
src/services/
├── heartbeat.py      # Heartbeat manager (piše .heartbeat.json)
└── watchdog.py       # Watchdog monitor (auto-restart)

run_daemon.py         # Main entry point za 24/7 rad
data/
├── .heartbeat.json   # Heartbeat status file
└── watchdog.log      # Watchdog log
```

### Zaustavljanje iz drugog terminala
```python
from src.services.watchdog import create_stop_signal
create_stop_signal()
```

---

## Session 20 - Self-Tuning AI Override (2026-02-02)

**Implementirano:**
- **AI Override sustav** - AI može prilagoditi postavke kad vidi dobru priliku
- **Tunable Settings** - definirane granice za sve prilagodljive postavke
- **Override Evaluator** - Claude evaluira odbijene signale
- **Override Log tablica** - tracking svih override odluka i ishoda
- **Learning from Outcomes** - sustav uči iz override rezultata

### Kako radi
```
Scanner → Signal REJECTED (MTF conflict) → AI Override Evaluator
                                        ↓
                    "Je li ovo ipak dobar trade?"
                                        ↓
            AI confidence >= 65% → OVERRIDE APPROVED
                                        ↓
            Temporary adjustment → Re-evaluate → Execute
```

### Postavke koje AI MOŽE prilagoditi
| Postavka | Min | Max | Default |
|----------|-----|-----|---------|
| max_spread_pips | 1.5 | 3.5 | 2.0 |
| min_atr_pips | 2.0 | 5.0 | 3.0 |
| target_rr | 1.3 | 3.0 | 2.0 |
| min_confidence_threshold | 50 | 70 | 55 |
| mtf_strength_threshold | 40 | 80 | 60 |

### Postavke koje AI NE MOŽE prilagoditi (Hard Limits)
- max_risk_per_trade (3%) - NIKAD
- max_daily_drawdown (5%) - NIKAD
- max_weekly_drawdown (10%) - NIKAD
- max_concurrent_positions (10) - NIKAD

### Sigurnosne mjere
- Max 10 override-a dnevno
- Min 65% AI confidence za override
- 30 min cooldown nakon gubitka
- 3 gubitka = disable te postavke

### Config sekcija
```json
"ai_override": {
  "enabled": true,
  "min_ai_confidence": 65,
  "max_overrides_per_day": 10,
  "cooldown_after_loss_minutes": 30
}
```

### Novi/Modificirani fajlovi
```
src/core/tuning_config.py       # Tunable settings + limits
src/analysis/ai_override.py     # AI Override Evaluator
src/core/auto_config.py         # AIOverrideConfig
src/trading/auto_scanner.py     # Override integration
src/utils/database.py           # override_log tablica
settings/auto_trading.json      # ai_override config
```

### Očekivano ponašanje
```
SIGNAL_REJECTED | EUR_USD | MTF conflict: M5=BULLISH but H1=BEARISH(73%)
AI_OVERRIDE_EVAL | EUR_USD | Evaluating override opportunity...
AI_OVERRIDE_APPROVED | EUR_USD | confidence=82% | HTF opposition weak
AI_OVERRIDE_APPLIED | EUR_USD | Continuing despite MTF conflict
TRADE_EXECUTED | EUR_USD | Order #123456 via AI Override
```

---

## Session 21 - Adaptive Settings + Optimizacija (2026-02-03)

**Problem:** Agresivne postavke dovele do gubitaka (-1,163 EUR, 22% win rate)

**Rijesenje:**
1. **Adaptive Settings Manager** (`src/analysis/adaptive_settings.py`)
   - Auto-tuning postavki na temelju performansi
   - Smanjuje rizik na losing streak
   - Povisuje threshold na loš win rate

2. **MT5 Auto-Reconnect** (`src/trading/mt5_client.py`)
   - `_ensure_connected()` - automatski reconnect
   - Nema više "No IPC connection" errora

3. **Konzervativne postavke za profitabilnost**
   ```json
   {
     "min_confidence_threshold": 75,
     "risk_per_trade_percent": 1.0,
     "target_rr": 2.0,
     "max_concurrent_positions": 5,
     "ai_override": { "enabled": false }
   }
   ```

4. **Strogi AI Validation** - "Kad si u sumnji, ODBIJ"

5. **Strogi MTF Check** - threshold 55% (samo s trendom)

### Lekcije naučene
- Agresivne postavke = gubici
- Kvaliteta > Kvantiteta
- Samo S TRENDOM trgovati
- Max 5 pozicija istovremeno

### Novi fajlovi
- `src/analysis/adaptive_settings.py` - Self-tuning manager
- `src/services/auto_trading_service.py` - `_sync_and_learn()` metoda

### Cilj: 200 EUR/dan
- 4-5 profitabilnih tradeova
- ~40-50 EUR po tradeu
- Win rate 50%+ = profitabilnost

---

## Session 22 - Modern AI Trading Upgrades (2026-02-03)

**Faza 6 - Napredne AI nadogradnje bazirane na hedge fund tehnikama!**

### Implementirano:

1. **Market Regime Detection** (Phase 1)
   - ADX + Bollinger Bands za prepoznavanje tržišnog režima
   - 4 režima: TRENDING, RANGING, VOLATILE, LOW_VOLATILITY
   - Blokira LOW_VOLATILITY i VOLATILE (prevelik rizik)
   - TRENDING = samo S trendom, RANGING = samo kod S/R

2. **External Sentiment Integration** (Phase 2) - **ENABLED!**
   - Claude-powered news analysis (35% weight)
   - VIX correlation risk-on/risk-off (15% weight)
   - Economic calendar sentiment (20% weight)
   - Price action (30% weight)

3. **Walk-Forward Validation** (Phase 3)
   - Proper out-of-sample testing
   - Rolling train/test windows
   - Monte Carlo simulation za confidence intervals
   - Robustness scoring (0-100)

4. **Regime-Aware Learning** (Phase 4)
   - Learning engine prati win rate po režimu
   - Confidence adjustment baziran na režimu
   - Pattern tracking: `regime_TRENDING_EUR_USD`

### Novi fajlovi
```
src/sentiment/                    # External Sentiment
├── __init__.py
├── base_provider.py
├── aggregator.py
└── providers/
    ├── news_provider.py          # Claude news analysis
    ├── vix_provider.py           # VIX correlation
    └── calendar_provider.py      # Economic calendar

src/backtesting/walk_forward.py   # Walk-Forward + Monte Carlo
src/market/indicators.py          # +ADX, +Bollinger, +Regime
```

### Config dodaci
```json
"market_regime": {
  "enabled": true,
  "block_low_volatility": true,
  "block_volatile": true
},
"external_sentiment": {
  "enabled": true,
  "weights": {"price_action": 0.30, "news_claude": 0.35, "vix": 0.15, "calendar": 0.20}
}
```

### Očekivano poboljšanje
- +10-20% win rate
- Manje tradeova u lošim uvjetima
- Bolja kvaliteta signala

---

## Session 23 - News API Integration (2026-02-03)

**Automatsko dohvaćanje economic calendar podataka!**

### Implementirano:

1. **News Provider System** (`src/analysis/news_providers.py`)
   - Multi-provider arhitektura s fallback podrškom
   - Async refresh s caching mehanizmom
   - Auto-save u `news_calendar.json`

2. **Dostupni provideri:**

   | Provider | API Key | Opis |
   |----------|---------|------|
   | **Finnhub** | Potreban (besplatan) | 60 calls/min, [finnhub.io](https://finnhub.io/register) |
   | **FMP** | Potreban (besplatan) | 250 calls/day, [financialmodelingprep.com](https://site.financialmodelingprep.com/developer) |
   | ForexFactory | Potreban | JBlanked API |
   | **Recurring** | **NE TREBA** | Auto-generira NFP, FOMC, ECB, BoE, BoJ |

3. **UI konfiguracija** (Settings → News API tab)
   - Unos API ključeva za Finnhub/FMP
   - Enable/disable providera
   - Manual refresh button
   - Calendar status pregled

4. **NewsFilter integracija**
   - `await news_filter.refresh_from_api()` - async refresh
   - `news_filter.get_calendar_status()` - status za UI
   - Automatski čita iz `news_calendar.json`

### Novi fajlovi
```
src/analysis/news_providers.py    # Provider sustav
settings/news_providers.json      # Provider konfiguracija
```

### Korištenje

```python
# Programski
from src.analysis import refresh_news_calendar, set_finnhub_api_key

set_finnhub_api_key("your-api-key")
events = await refresh_news_calendar(force=True)
```

```bash
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

## Session 24 - Self-Upgrade System (2026-02-03)

**AI sustav koji automatski uci iz gresaka i generira nove filtere!**

### Implementirano:

1. **Performance Analyzer** (`src/upgrade/performance_analyzer.py`)
   - Analizira zadnjih 7 dana tradeova
   - Identificira losing patterns (instrument, session, regime, combined)
   - Generira filter proposals

2. **Code Generator** (`src/upgrade/code_generator.py`)
   - Template-based generiranje Python koda
   - Safety constraints (ALLOWED_IMPORTS, FORBIDDEN_PATTERNS)
   - Claude integration za kompleksnije filtere

3. **Code Validator** (`src/upgrade/code_validator.py`)
   - AST parsing za syntax check
   - Import whitelist enforcement
   - Dangerous function/attribute detection
   - Sandbox execution testing

4. **Upgrade Executor** (`src/upgrade/upgrade_executor.py`)
   - Walk-forward backtesting na historical signals
   - Robustness score calculation (min 60%)
   - Deploy to `src/filters/ai_generated/`
   - Auto-rollback mechanism

5. **Upgrade Manager** (`src/upgrade/upgrade_manager.py`)
   - Orchestrira daily upgrade cycle
   - Max 3 proposals per cycle
   - Monitors deployed filters
   - Triggers rollback when needed

### Arhitektura
```
Daily (00:00 UTC)
       |
Performance Analyzer -> Identify losing patterns
       |
Filter Proposals (max 3)
       |
Code Generator -> Safe Python code
       |
Code Validator -> AST + Security check
       |
Upgrade Executor -> Backtest (robustness >= 60%?)
       |
Deploy to ai_generated/ -> Track performance
       |
Auto-Rollback if:
  - Win rate drop > 10%
  - 5 consecutive losses
  - Block rate > 50%
```

### Filter Chain Integration
```python
# U auto_scanner.py nakon confidence check-a:
filter_result = self.filter_registry.run_all_filters(signal_data)
if not filter_result.passed:
    return skip_result(f"Filter: {filter_result.reason}")
```

### Safety Mechanisms (HARD CODED!)

**AI-generirani kod NE MOZE:**
- Importati: os, sys, subprocess, socket, requests, pickle
- Koristiti: exec, eval, open, __import__, getattr s dunder
- Pristupati: filesystem, network, __builtins__, __dict__
- Modificirati: Hard limits (risk, drawdown, positions)

**Auto-Rollback:**
- Win rate drop > 10% -> rollback
- 5 consecutive losses -> rollback
- Block rate > 50% -> rollback

### Novi fajlovi
```
src/upgrade/
├── __init__.py
├── base_filter.py           # Abstract filter class
├── filter_registry.py       # Filter management
├── performance_analyzer.py  # Loss pattern analysis
├── code_generator.py        # Safe code generation
├── code_validator.py        # AST security check
├── upgrade_executor.py      # Backtest + deploy
└── upgrade_manager.py       # Main orchestrator

src/filters/
├── builtin/
│   ├── consecutive_loss_filter.py
│   └── low_confidence_direction_filter.py
└── ai_generated/
    └── (auto-generated filters)
```

### Database tablice
```sql
-- AI-generirani prijedlozi
CREATE TABLE upgrade_proposals (...)

-- Deployani filteri
CREATE TABLE deployed_filters (...)

-- Audit log
CREATE TABLE upgrade_audit_log (...)
```

### Config sekcija
```json
"self_upgrade": {
  "enabled": true,
  "analysis_interval_hours": 24,
  "min_trades_for_analysis": 20,
  "max_proposals_per_cycle": 3,
  "min_robustness_score": 60,
  "auto_rollback_threshold": {
    "win_rate_drop": 0.10,
    "consecutive_losses": 5,
    "max_block_rate": 50
  }
}
```

### Deployment Criteria (filter mora zadovoljiti SVE)

| Kriterij | Zahtjev | Razlog |
|----------|---------|--------|
| **Block rate** | ≤ 50% | Ne smije blokirati većinu signala |
| **Accuracy** | > 50% | Mora blokirati više losera nego winnera |
| **Robustness** | ≥ 60% | Kombinirani weighted score |
| **Min signals** | ≥ 20 | Dovoljno podataka za statistički značajan backtest |

### Robustness Score Formula
```
Robustness = (Accuracy * 0.5) + (BlockRateScore * 0.3) + (PnLImpactScore * 0.2)

BlockRateScore:
  - 10-30% block rate = 30 points (ideal)
  - <10% = lower score (too permissive)
  - >30% = penalized (too aggressive)

PnLImpactScore:
  - Positive PnL impact = up to 20 points
  - Negative = negative points
```

### Test Results (2026-02-03)

```
=== ALL TESTS PASSED (9/9) ===
1. BaseFilter         - OK
2. FilterRegistry     - OK
3. Builtin Filters    - OK (2 loaded)
4. PerformanceAnalyzer- OK (6 patterns found)
5. CodeValidator      - OK (blocks os, exec, open)
6. CodeGenerator      - OK (1890 chars generated)
7. UpgradeManager     - OK
8. Filter Chain       - OK (0ms for 2 filters)
9. Full Upgrade Cycle - OK
```

### Current Patterns Detected

| Pattern | Win Rate | Block Rate | Status |
|---------|----------|------------|--------|
| regime=UNKNOWN | 9.1% | 0% | No regime data in history |
| session=london | 6.2% | 97.1% | Too aggressive (>50%) |
| EUR_USD+LONG | 0% | 0% | Low sample size |
| GBP_USD+london | 0% | 0% | Low sample size |

**Zašto nema deployanih filtera:**
- London filter blokira 97% signala (limit je 50%)
- Regime filter nema historical podatke
- Combined patterni imaju premalo sample size

### Ručno testiranje

```bash
cd Dev

# Run test suite
python test_upgrade_system.py

# Check current patterns
python -c "
from src.upgrade.performance_analyzer import PerformanceAnalyzer
analyzer = PerformanceAnalyzer()
for p in analyzer.analyze_recent_performance(days=7):
    print(f'{p.severity}: {p.pattern_type}={p.pattern_key} WR={p.win_rate:.1f}%')
"

# Force upgrade cycle
python -c "
import asyncio
from src.upgrade.upgrade_manager import get_upgrade_manager
asyncio.run(get_upgrade_manager().run_daily_upgrade_cycle())
"
```

### Quick Fixes Applied
- Uklonjeni EUR_PLN, USD_PLN (nedostupni na MT5)
- Learning mode threshold: 35 → 50 (kvalitetniji signali)
- Fixed CodeGenerator safety regex (was blocking valid imports)
- Fixed UpgradeExecutor sandbox (proper module imports)

---

*Zadnje azuriranje: 2026-02-03 | Session 24 - Self-Upgrade System TESTED & WORKING*
