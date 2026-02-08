# AI Trader - Claude Instructions

> **CLAUDE:** Na pocetku sesije procitaj `Dev/CLAUDE_CONTEXT.md` za kompletan kontekst projekta.

---

## Quick Start

```bash
cd Dev
cat CLAUDE_CONTEXT.md   # Procitaj kontekst
```

## Projekt Status (2026-02-08)

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
| Faza 7: Self-Upgrade System | DONE |
| Faza 8: SMC Implementation | DONE |
| Faza 9: ISI (Institutional Sequence Intelligence) | DONE |
| Faza 10: Validation & SMC Backtest Engine | DONE |
| Faza 10.1: ISI in Backtest Engine | DONE |
| Faza 10.2: Walk-Forward + Fast Backtests | DONE |
| Faza 10.3: SL/Entry/TP Improvements | DONE |
| Faza 10.4: Limit Entry (Breakthrough) | DONE |
| Faza 10.5: Limit Entry in Production | DONE |

### Trenutno stanje (2026-02-08)

| Metrika | Vrijednost |
|---------|------------|
| Balance | 48,517.30 EUR (start: 50,000) |
| Realized P/L | -1,163.15 EUR |
| Instruments | EUR_USD, GBP_USD, XAU_USD |
| Risk/Trade | 0.3% |
| Max Daily Trades | 3 |
| Target R:R | 2.0 minimum |
| Service | STOPPED |
| Dry Run | TRUE |
| Decision Logic | Pure SMC + ISI |

**NAPOMENA:** Service ne radi, dry_run=true. SMC+ISI pipeline potpuno implementiran.

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
├── smc/                             # Smart Money Concepts (Phase 8)
│   ├── smc_analyzer.py              # HTF/LTF analysis + grading + SL/TP
│   ├── structure.py                 # CHoCH, BOS, swing points
│   ├── liquidity.py                 # Liquidity map, sweep detection
│   ├── zones.py                     # FVG, OB, premium/discount
│   ├── displacement.py              # Displacement detection
│   ├── sequence_tracker.py          # ISI: 5-phase institutional cycle
│   └── liquidity_heat_map.py        # ISI: Predictive liquidity density
├── analysis/
│   ├── confidence_calibrator.py     # ISI: Bayesian calibration (Platt Scaling)
│   ├── cross_asset_detector.py      # ISI: Correlation divergence
│   ├── learning_engine.py           # Pattern learning + Regime-aware
│   └── llm_engine.py               # AI validation (SMC+ISI rules)
├── core/auto_config.py              # Konfiguracija + Risk model
├── trading/auto_scanner.py          # SMC+ISI market scanner pipeline
├── trading/auto_executor.py         # Trade executor + STOP DAY
├── trading/emergency.py             # Emergency stop
├── market/indicators.py             # Technical + ADX + Bollinger + Regime
├── sentiment/                       # External Sentiment (Phase 6)
│   ├── aggregator.py                # Combines all sources
│   └── providers/                   # VIX, News, Calendar
├── backtesting/walk_forward.py      # Walk-Forward Validation + Monte Carlo
├── upgrade/                         # Self-Upgrade System (Phase 7)
│   ├── base_filter.py               # Abstract filter class
│   ├── filter_registry.py           # Filter management
│   ├── performance_analyzer.py      # Loss pattern analysis
│   ├── code_generator.py            # Safe code generation
│   ├── code_validator.py            # AST security check
│   ├── upgrade_executor.py          # Backtest + deploy
│   └── upgrade_manager.py           # Main orchestrator
├── filters/                         # Trading filters
│   ├── builtin/                     # Built-in filters
│   └── ai_generated/                # AI-generated filters
├── services/
│   ├── auto_trading_service.py      # Main loop + upgrade cycle
│   ├── heartbeat.py                 # Heartbeat manager
│   └── watchdog.py                  # Watchdog monitor
└── strategies/scalping.py           # Scalping strategija

settings/auto_trading.json           # Config file
pages/13_AutoTrading.py              # UI Control Panel
run_auto_trading.py                  # Simple runner
run_daemon.py                        # 24/7 daemon s auto-restart
test_smc.py                          # SMC tests (10)
tests/test_*.py                      # ISI tests (32)
```

### Kako radi
1. Scanner skenira 4 instrumenta svakih 60s (EUR_USD, GBP_USD, XAU_USD, BTCUSD)
2. **SMC HTF Analysis** - H4/H1 struktura + likvidnost + **heat map** [ISI]
3. **SMC LTF Analysis** - M5 sweep + CHoCH/BOS + FVG/OB + displacement
4. **Sequence Tracking** - 5-phase cycle, modifier -20 to +15 [ISI]
5. **Market Regime Check** - blokira LOW_VOLATILITY i VOLATILE
6. Analizira s Technical + **External Sentiment** (VIX, News, Calendar) + Adversarial
7. **Cross-Asset Divergence** - correlation anomalies, modifier -10 to +15 [ISI]
8. **Bayesian Calibration** - Platt Scaling maps raw -> calibrated confidence [ISI]
9. Kad je confidence >= threshold (75% trenutno)
10. **Claude AI validira signal** (APPROVE/REJECT) s ISI kontekstom
11. Ako APPROVE, izvrsava trade s risk management (ako dry_run=false)
12. Learning Mode prati win rate **po market rezimu**

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
- Balance: `48,517.30 EUR` (started 50,000)
- Status: **STOPPED** (dry_run: true)
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

## Session 26 - ISI: Institutional Sequence Intelligence (2026-02-07)

**4 ISI komponente za poboljsanje kvalitete signala!**

### Problem
Confidence 82-92% ne odgovara win rate-u od 5.1%. SMC radi point-in-time scoring umjesto sekvencijalnog razumijevanja.

### Implementirano:

1. **Bayesian Confidence Calibration** (`src/analysis/confidence_calibrator.py`)
   - Platt Scaling: `P(win) = 1/(1+exp(-(A*raw+B)))`
   - Min 30 trades za fit, refit svakih 50
   - Fallback: manual gradient descent (bez scipy)

2. **Sequence Tracker** (`src/smc/sequence_tracker.py`)
   - 5-phase cycle: ACCUM(-20) -> MANIP(-10) -> DISP(+5) -> **RETRACE(+15)** -> CONT(0)
   - Phase 4 = OPTIMAL ENTRY (highest confidence boost)
   - DB persistence: stanja prezive restart

3. **Liquidity Heat Map** (`src/smc/liquidity_heat_map.py`)
   - Predvidja WHERE sweep ce se dogoditi
   - Temporal decay: `exp(-0.05 * hours)`
   - Session weights: London=3.0, NY=2.5, Asian=2.0
   - Poboljsan TP targeting (najjaci level umjesto nearest)

4. **Cross-Asset Divergence** (`src/analysis/cross_asset_detector.py`)
   - EUR/GBP(0.85), EUR/XAU(0.40), GBP/XAU(0.30)
   - 1.5 sigma threshold za signal
   - Modifier: -10 to +15 (30-min cache)

### Pipeline integracija
```
Confidence = SMC_grade + sentiment + seq_modifier + divergence_modifier
           -> Bayesian calibration (Platt Scaling)
           -> Learning adjustment
           -> Threshold check
SL/TP     = SMC zones + Heat Map targets (strongest density level)
AI Prompt = SMC rules + ISI context (phase, divergence)
```

### Nove DB tablice
- `calibration_params` - Platt Scaling parametri
- `sequence_states` - Aktivna stanja sekvenci
- `sequence_transitions` - Log faznih prijelaza
- `sequence_completions` - Dovrseni ciklusi
- `correlation_snapshots` - Korelacijski snimci

### Test Results
```
ISI Phase 1 (Calibrator):        6/6 PASSED
ISI Phase 2 (Sequence Tracker):  9/9 PASSED
ISI Phase 3 (Heat Map):          8/8 PASSED
ISI Phase 4 (Cross-Asset):       9/9 PASSED
Existing SMC Tests:              10/10 PASSED
TOTAL: 42/42 ALL PASSED
```

---

## Session 27 - Validation, Cleanup & SMC Backtest Engine (2026-02-07)

**Implementirano:**
- **Sustav validacija vs svijet** - 30+ izvora, ocjena 62/100 (75/100 bez perf.)
- **Upgrade roadmap** - 7 promjena za 85/100 (`Brainstorming/Upgrade_Roadmap_85.md`)
- **Operativni playbook** - 3-mjesecni plan (`Brainstorming/Operational_Playbook_Q1_2026.md`)
- **FTMO plan** - MT5 kompatibilan (`Brainstorming/FTMO_Plan.md`)
- **SMC BacktestEngine** - kompletno prepisan za SMC pipeline (H4+H1+M5)
- **Cleanup** - zombie trade, BTCUSD removed, dry_run=true
- **Bug fix** - `heat_map` undefined u smc_analyzer.py SHORT grani

**SMC Backtest (EUR_USD 90d):**
- 26 trades, WR=7.7%, P/L=-3,578 EUR, Max DD=7.63%
- SMC je selektivniji (26 vs 179 stari) i kontrolira DD (7.6% vs 82%)
- Problem: SL buffer (3 pips) preuzak - 92% SL hitova

**Novi fajlovi:** `Brainstorming/` (4 plana), `backtest_results/`
**Modificirani:** `engine.py` (rewrite), `smc_analyzer.py` (fix), `auto_trading.json`

---

## Session 29 - ISI in Backtest Engine (2026-02-08)

**Backtest engine sada koristi isti ISI pipeline kao produkcija!**

### Implementirano:

1. **BacktestConfig ISI toggles** - 3 nova boolean polja (default False = backward compat)
   - `isi_sequence_tracker` - Enable sequence phase tracking
   - `isi_cross_asset` - Enable cross-asset divergence
   - `isi_calibrator` - Enable Platt Scaling calibration

2. **SimulatedTrade ISI metadata** - 6 novih polja
   - `raw_confidence` - Pre-calibration confidence
   - `calibrated_confidence` - Post-calibration confidence
   - `sequence_phase` / `sequence_phase_name` - Current ISI phase
   - `sequence_modifier` / `divergence_modifier` - Applied modifiers

3. **BacktestCrossAssetAdapter** (`engine.py`)
   - Zamjenjuje MT5-ovisni CrossAssetDetector s pre-loaded M5 podacima
   - Time-aligned po timestampu (bez look-ahead bias)
   - Ista korelacijska matematika kao produkcija

4. **ISI Pipeline u _generate_smc_signal**
   - Sequence tracker update PRIJE hard gates (kontinuirano pracenje)
   - Divergence modifier NAKON sto je direction poznat
   - Calibrator na kraju (passthrough ako nije fitted)

5. **run_backtest_suite.py nadograde**
   - Ucitava XAU_USD M5 kao cross-asset referencu
   - ISI toggle u parameter grid (noISI vs Seq+XA+Cal)
   - Nova `print_isi_comparison()` funkcija za side-by-side analizu
   - ISI metadata summary u rezultatima

### Confidence Pipeline (production parity)
```
SMC grade confidence (68-92)
+ sequence_modifier (-20 to +15)     <- SequenceTracker
+ divergence_modifier (-10 to +15)   <- CrossAssetDetector
= raw_score (clamped 0-100)
-> calibrator.calibrate()            <- ConfidenceCalibrator (passthrough if unfitted)
= final confidence
-> threshold check (>= min_confidence)
```

### Pokretanje backtesta s ISI
```python
config = BacktestConfig(
    instrument="EUR_USD", ...,
    isi_sequence_tracker=True,
    isi_cross_asset=True,
    isi_calibrator=True,
)
result = engine.run(h4, h1, m5, config, cross_asset_data={"GBP_USD": gbp_m5, "XAU_USD": xau_m5})
```

### Test Results
```
SMC Tests:  10/10 PASSED
ISI Tests:  32/32 PASSED
TOTAL:      42/42 ALL PASSED
```

---

## Session 30 - Fast Backtests + Walk-Forward + Finnhub (2026-02-08)

**Implementirano:**

1. **Finnhub API aktiviran** (`settings/news_providers.json`)
   - API key: `d644co9r01ql6dj251rgd644co9r01ql6dj251s0`
   - Economic calendar = PREMIUM (403), stock quotes RADE
   - Recurring provider radi kao fallback bez API kljuca

2. **XAU_USD u DataLoader** (`src/backtesting/data_loader.py`)
   - `"XAU_USD": "GOLD.pro"` (NE `XAUUSD.pro`!)
   - MORA se `mt5.symbol_select('GOLD.pro', True)` prije fetchanja

3. **Walk-Forward Validator REWRITE** (`src/backtesting/walk_forward.py`)
   - `WalkForwardConfig` dataclass sa svim parametrima
   - `WalkForwardValidator.run(config, h4, h1, m5, cross_asset_data)`
   - ISI DB izolacija: monkey-patch `src.utils.database._db_path` na temp file
   - Monte Carlo integracija na svim OOS tradeovima
   - `_slice_candles()` helper za timestamp-based slicing
   - 15-dnevni lookback buffer za HTF kontekst

4. **Backtest Suite OPTIMIZIRAN** (`run_backtest_suite.py`)
   - Grid: 256 -> 16 konfiguracija (8 per instrument)
   - signal_interval: 3 -> 6 (30 min umjesto 15)
   - ProcessPoolExecutor(max_workers=6) za paralelno izvrsavanje
   - ISI DB izolacija per worker (temp DB file per PID)
   - **264s ukupno** (100x ubrzanje vs procjena 2-4h)

5. **Walk-Forward Runner** (`run_walk_forward.py`) - NOVI
   - 3 instrumenta: EUR_USD, GBP_USD, XAU_USD
   - ISI vs noISI usporedba za svaki
   - 4 prozora (45d train / 15d test)
   - Monte Carlo 1000 iteracija
   - 972s ukupno za sve

### Backtest rezultati (Session 30)

**Suite (16 configs, 264s):**
| Config | Trades | WR | Return | MaxDD | PF |
|--------|--------|-----|--------|-------|-----|
| GBP HighConf ISI | 30 | 26.7% | -1.74% | 4.21% | 0.78 |
| GBP Baseline | 31 | 25.8% | -2.10% | 4.32% | 0.74 |
| EUR Baseline | 33 | 21.2% | -5.46% | 7.05% | 0.41 |
| EUR NoFilters | 60 | 18.3% | -10.40% | 11.77% | 0.37 |

**Walk-Forward (972s):**
| Config | OOS WR | OOS P/L | Consistency | P(Profit) |
|--------|--------|---------|-------------|-----------|
| XAU_USD noISI | 23.8% | +2,170 | 50% | 100% |
| EUR_USD noISI | 23.8% | -1,673 | 0% | 0% |
| GBP_USD noISI | 20.4% | -1,672 | 25% | 0% |

**ISI impact**: Minimalan na trenutnim podacima (calibrator unfitted, premalo tradeova za statistical significance)

### DB izolacija VERIFICIRANA
- Prod DB: 0 sequence_states, 0 sequence_transitions, 0 correlation_snapshots
- Temp DB-ovi automatski obrisani nakon zavrsetka

### Rezultati spremljeni u
- `backtest_results/suite_20260208_094138.json`
- `backtest_results/walk_forward_20260208_095852.json`

### Pokretanje
```bash
cd Dev

# Backtest suite (16 configs, ~4-5 min)
python run_backtest_suite.py

# Walk-Forward Validation (3 instruments, ~16 min)
python run_walk_forward.py
```

---

## Session 31 - SL/Entry/TP Improvements (2026-02-08)

**3 strukturalna poboljsanja za profitabilnost:**

### 1. ATR-Based Dynamic SL
- Zamijenjen fiksni 7-pip buffer s `max(min_sl_pips, ATR * multiplier)`
- `_calculate_atr_from_candles()` - manualni ATR izracun (period=14, bez vanjskih deps)
- Per-instrument podesavanje u `instrument_profiles.json`:
  - EUR_USD: min_sl=10, multiplier=1.3x
  - GBP_USD: min_sl=12, multiplier=1.5x
  - XAU_USD: min_sl=50, multiplier=2.0x
  - Default: min_sl=12, multiplier=1.5x, max_sl=30

### 2. Entry Zone Proximity Check
- `_check_entry_zone_proximity()` - ocjenjuje udaljenost od FVG/OB zone
  - U zoni: +10 confidence
  - Blizu (<=5 pips): +5
  - Daleko (>10 pips): -15 (filtrira prerane ulaze)
- `SMCAnalysis.current_price` field dodan
- `grade_setup(analysis, instrument)` - instrument param za pip_value lookup

### 3. Partial TP + Trailing Stop (Backtest Engine)
- **Partial TP**: Zatvori 50% pozicije na 1.5R, SL se pomice na breakeven
- **Trailing Stop**: Trail po ATR*1.0 nakon partial TP
- `BacktestConfig` nova polja: `partial_tp_enabled`, `partial_tp_rr`, `trailing_stop_enabled`, `trailing_atr_multiplier`
- `SimulatedTrade` nova polja: `partial_tp_price`, `partial_pnl`, `current_sl`, `original_units`, etc.
- `_check_sl_tp(trade, candle, config)` - kompletni rewrite s partial/trailing/breakeven logikom
- PnL = partial_pnl + remaining_pnl - commission (total units za commission)
- `BacktestConfig` defaults: target_rr 3.0->2.0, max_sl_pips 15->30

### Modificirani fajlovi
```
settings/instrument_profiles.json   # min_sl_pips, sl_atr_multiplier, max_sl_pips per instrument
src/smc/smc_analyzer.py             # ATR calc, entry zone proximity, grade_setup(analysis, instrument)
src/backtesting/engine.py           # Partial TP, trailing stop, BacktestConfig defaults
```

### Test Results
```
SMC Tests:    10/10 PASSED
ISI + Import: 40/40 PASSED
TOTAL:        50/50 PASSED (15 stale tests pre-existing)
```

---

---

## Session 32 - Limit Entry + Breakeven SL (2026-02-08)

**BREAKTHROUGH: Limit entry at FVG/OB midpoint = PROFITABILNO!**

### Otkriće
- Umjesto market entry, čekamo da se cijena vrati u FVG/OB zonu
- Limit order na midpoint zone = bolji entry = bolji R:R

### Backtest rezultati (Aug 2025 - Feb 2026, 6 mj):
| Config | Trades | WR | Return | PF | MaxDD |
|--------|--------|-----|--------|-----|-------|
| **GBP Lim12 Mid** | **13** | **46%** | **+5.72%** | **2.68** | **2.99%** |
| **GBP Lim6 Mid** | **9** | **44%** | **+5.31%** | **3.80** | **1.60%** |
| GBP OLD Market | 30 | 20% | -4.74% | 0.40 | 4.87% |

**10.5pp poboljšanje** od market do limit midpoint entry!

### Ključni nalazi:
- **Partial TP škodi**: reže winnere na 1.5R, max R:R = 1.75x (disabled)
- **Breakeven SL malo škodi**: pretvara potencijalne winnere u 0 (disabled)
- **Midpoint entry ključan**: dublje = bolja cijena = 3-5x W/L ratio
- **Limit orderi filtriraju kvalitetu**: samo 28-42% signala se ispuni = prirodni filter
- **EUR i dalje neprofitabilan** (PF 0.76-0.80) ali značajno bolji od 0.47

### Implementirano u backtest engine:
- `PendingOrder` dataclass, `limit_entry_enabled/max_bars/midpoint`, `breakeven_sl_enabled`
- `_create_trade()` helper, breakeven exit reason

---

## Session 33 - Limit Entry in Production (2026-02-08)

**Limit entry sada radi u produkciji, ne samo u backtestu!**

### Implementirano:

1. **BacktestConfig defaults**: `limit_entry_max_bars=12`, `limit_entry_midpoint=True`
2. **LimitEntryConfig** u `auto_config.py` - enabled, midpoint_entry, expiry_minutes, max_pending
3. **TradingSignal** polja: `entry_zone`, `limit_price`, `use_limit_entry`
4. **Scanner Step 13.5**: računa limit price iz FVG/OB zone midpoint/edge
5. **OrderManager.place_pending_order()**: MT5 `TRADE_ACTION_PENDING` + limit orderi
6. **OrderManager.cancel_pending_order()**: MT5 `TRADE_ACTION_REMOVE`
7. **OrderManager.get_pending_orders()**: queries `mt5.orders_get()`
8. **AutoExecutor** branching na `signal.use_limit_entry` (limit vs market)
9. **AutoExecutor.check_pending_orders()**: detektira FILLED/EXPIRED evente
10. **AutoExecutor._rebuild_pending_orders()**: rebuild iz MT5 na startupu
11. **Service loop** provjerava pending order status prije svakog scan ciklusa
12. **auto_trading.json**: `limit_entry` config sekcija

### Config sekcija
```json
"limit_entry": {
    "enabled": true,
    "midpoint_entry": true,
    "expiry_minutes": 60,
    "max_pending_per_instrument": 1
}
```

### Dizajn odluke:
- Expiry: pokušava `ORDER_TIME_SPECIFIED`, fallback na `ORDER_TIME_GTC`
- `_pending_orders` dict po instrumentu (max 1 per instrument)
- Pending order blokira nove signale za isti instrument
- Dry run logira "would place limit order"

### Test Results
```
SMC Tests:  10/10 PASSED
ISI Tests:  32/32 PASSED
TOTAL:      42/42 ALL PASSED
```

### Novi/Modificirani fajlovi
```
src/core/auto_config.py          # LimitEntryConfig dataclass
src/trading/auto_scanner.py      # TradingSignal fields + Step 13.5
src/trading/orders.py            # 3 nova MT5 pending order metoda
src/trading/auto_executor.py     # Limit entry branching + tracking
src/services/auto_trading_service.py # Pending order check u loopu
src/backtesting/engine.py        # Default: max_bars=12, midpoint=True
settings/auto_trading.json       # limit_entry config section
```

---

## Poznati problemi (2026-02-08)

1. **Service STOPPED** - daemon ne radi, heartbeat star 1h+
2. **dry_run: true** - sustav ne izvrsava prave tradeove
3. **Calibrator uncalibrated** - Treba min 30 zatvorenih tradeova za Platt Scaling fit
4. **15 starijih testova** - orders_security, risk_manager trebaju update
5. **Finnhub economic calendar** - zahtijeva premium plan (403 na free tier)
6. **EUR_USD** - limit entry pomaže ali nije dovoljno, treba drugačiji pristup

---

*Zadnje azuriranje: 2026-02-08 | Session 33 - Limit Entry in Production*
