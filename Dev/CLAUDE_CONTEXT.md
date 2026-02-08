# AI TRADER - Claude Session Context

> **VAZNO:** Ovaj fajl sluzi kao kontekst za Claude Code. Citaj ga na pocetku svake sesije.

---

## Sto je ovaj projekt?

**AI Trader** je **FULL AUTO SMC trading bot** koji koristi:
- **Smart Money Concepts (SMC)** za institucionalnu price action analizu
- **Claude Code CLI** kao sucelje
- **Claude AI** za validaciju + override odluke
- **MetaTrader 5** kao broker (Python API)
- **Python** kao runtime
- **Streamlit** za Web Dashboard

**Vlasnik:** Sirius Grupa d.o.o.
**Svrha:** Automatizirani forex/gold/crypto trading s SMC + AI analizom
**Cilj:** MIN 200 EUR profit dnevno

---

## Trenutni Status (2026-02-08)

| Faza | Status | Opis |
|------|--------|------|
| Faza 1-4 | DONE | Foundation, Core, AI, Dashboard |
| Faza 5: Full Auto Trading | DONE | Automatizirani scalping bot |
| Faza 5.1-5.4 | DONE | AI Visibility, Learning, Validation |
| Faza 5.5: 24/7 Daemon Mode | DONE | Heartbeat + Watchdog |
| Faza 5.6: Self-Tuning | DONE | AI Override za rejected signale |
| Faza 5.7: Adaptive Settings | DONE | Auto-optimizacija postavki |
| Faza 6: Modern AI Upgrades | DONE | Market Regime, External Sentiment, Walk-Forward |
| Faza 6.1: News API Integration | DONE | Finnhub, FMP, Recurring |
| Faza 7: Self-Upgrade System | DONE | AI generira filtere iz losing patterna |
| Faza 8: SMC Implementation | DONE | Smart Money Concepts - kompletna zamjena decision core-a |
| Faza 9: ISI (Institutional Sequence Intelligence) | DONE | 4 komponente: Calibration, Sequence, HeatMap, CrossAsset |
| Faza 10.1: ISI in Backtest Engine | DONE | Backtest engine koristi isti ISI pipeline kao produkcija |
| Faza 10.2: Walk-Forward + Fast Backtests | DONE | 264s suite, Monte Carlo, ISI DB isolation |
| **Faza 10.3: SL/Entry/TP Improvements** | **DONE** | **ATR-based SL, entry zone proximity, partial TP + trailing** |

**Ukupni napredak: 100% - SMC+ISI AI TRADING SUSTAV!**

### Trenutno stanje sustava (2026-02-08)

| Metrika | Vrijednost |
|---------|------------|
| **Balance** | 48,517.30 EUR (start: 50,000) |
| **Realized P/L** | -1,163.15 EUR |
| **Instruments** | EUR_USD, GBP_USD, XAU_USD |
| **Risk/Trade** | **0.3%** |
| **Max Daily Trades** | **3** |
| **STOP DAY** | **After 2 losses** |
| **Target R:R** | **1:2 minimum** |
| **Service** | STOPPED |
| **Dry Run** | TRUE |

**VAZNO:** `dry_run: true` u configu - sustav NE izvrsava prave tradeove!

---

## NOVO: Session 25 (2026-02-07) - SMC Implementation

### Sto je implementirano?

**Kompletna zamjena decision-making core-a s Smart Money Concepts!**

Stari sustav (EMA/RSI/MACD) je zamijenjen institucionalnom price action analizom:
- **Liquidity Sweeps** - "No sweep = No trade" - svaki trade zahtijeva sweep
- **Market Structure (CHoCH/BOS)** - Change of Character + Break of Structure
- **Fair Value Gaps (FVG)** - Imbalance zone za entry
- **Order Blocks (OB)** - Institutional supply/demand zone
- **Displacement** - Impulsive institutional moves
- **Premium/Discount** - Buy in discount, sell in premium

### SMC+ISI Pipeline (auto_scanner.py)

```
Price -> Spread -> Session -> News
-> Candles (H4 + H1 + M5)
-> SMC HTF Analysis (H4/H1: structure + liquidity map + HEAT MAP)  [ISI F3]
-> HTF Bias check (NEUTRAL = NO TRADE)           <- HARD GATE
-> SMC LTF Analysis (M5: sweep + CHoCH/BOS + FVG + displacement)
-> Sweep check (NO SWEEP = NO TRADE)              <- HARD GATE
-> CHoCH/BOS check (NONE = NO TRADE)              <- HARD GATE
-> SEQUENCE TRACKING (phase 1-5, modifier +/-20)  [ISI F2]
-> Setup Grading (A+/A/B/NO_TRADE)
-> Grade -> Confidence mapping (A+=92, A=82, B=68)
-> Regime filter (still useful)
-> Sentiment (additional edge)
-> CROSS-ASSET DIVERGENCE (modifier +/-15)         [ISI F4]
-> Confidence = SMC + Sentiment + Sequence + Divergence
-> BAYESIAN CALIBRATION (Platt Scaling)            [ISI F1]
-> Learning engine (adapts from history)
-> Filter chain (self-upgrade system)
-> SL/TP (SMC-based + HEAT MAP targets)            [ISI F3]
-> R:R check (min 1:2)
-> Signal -> AI Validation (+ISI context) -> Execute
-> Partial TP (50% at 1.5R) + Trailing Stop (ATR*1.0)
```

### Setup Grading

| Grade | Confidence | Requirements |
|-------|-----------|--------------|
| **A+** | 92% | All: sweep + CHoCH/BOS + HTF aligned + displacement + FVG + OB + premium/discount |
| **A** | 82% | Missing one non-critical element (e.g., no displacement) |
| **B** | 68% | Multiple weaker elements |
| **NO_TRADE** | 30% | Missing sweep OR CHoCH/BOS OR HTF neutral |

### Risk Model Changes

| Postavka | Prije | Sada |
|----------|-------|------|
| risk_per_trade_percent | 0.5% | **0.3%** |
| max_daily_trades | unlimited | **3** |
| max_trades_per_instrument | 2 | **1** |
| target_rr | 1.5 | **2.0** |
| instruments | 5 (EURUSD, GBPUSD, USDJPY, AUDUSD, BTCUSD) | **4 (EUR_USD, GBP_USD, XAU_USD, BTCUSD)** |
| STOP DAY | N/A | **After 2 losses** |
| ai_override | enabled | **disabled** |
| Decision logic | EMA/RSI/MACD | **Pure SMC** |

### Novi fajlovi (7 created)

```
src/smc/                          # Smart Money Concepts Module
├── __init__.py                   # Module exports (SMCAnalyzer, SMCAnalysis)
├── structure.py                  # Swing points, CHoCH, BOS, market structure
├── liquidity.py                  # Liquidity map, session levels, sweep detection
├── zones.py                      # FVG, Order Blocks, Premium/Discount, S/D zones
├── displacement.py               # Displacement (institutional impulse) detection
└── smc_analyzer.py               # Main orchestrator + grading + SL/TP calc

test_smc.py                       # 10 unit tests - ALL PASSED
```

### Modificirani fajlovi (13 modified)

```
settings/auto_trading.json        # Risk model, instruments, R:R, stop_day
settings/instrument_profiles.json # session_sweep_source per instrument
src/core/auto_config.py           # StopDayConfig dataclass
src/trading/auto_scanner.py       # COMPLETE REWRITE - SMC pipeline
src/trading/auto_executor.py      # STOP DAY mechanism
src/trading/mt5_client.py         # XAUUSD symbol mapping
src/strategies/scalping.py        # SMC patterns (FVG_ENTRY, OB_ENTRY, SWEEP_REVERSAL)
src/analysis/llm_engine.py        # SMC validation prompt (7 SMC rules)
src/analysis/confidence.py        # (unchanged but overridden by SMC confidence)
src/utils/database.py             # smc_analysis table
```

### Test Results

```
=== SMC MODULE TEST SUITE ===
RESULTS: 10 PASSED, 0 FAILED out of 10

1. Swing Points           - OK (4 detected)
2. Structure Classification - OK (HH_HL, LH_LL correct)
3. CHoCH Detection         - OK (Bearish CHoCH at correct level)
4. FVG Detection           - OK (1 bullish FVG)
5. Order Block Detection   - OK (1 bullish OB, 7.8x displacement)
6. Premium/Discount Zones  - OK (DISCOUNT/PREMIUM/EQUILIBRIUM correct)
7. Displacement Detection  - OK (15x ratio, confirmed)
8. Setup Grading           - OK (NO_TRADE without sweep, A+ with full setup)
9. Session Levels          - OK (Asian/London/NY detected)
10. Full Pipeline          - OK (NO_TRADE with synthetic data - expected)
```

### Per-Instrument Session Sweep Source

| Instrument | sweep_source | Meaning |
|-----------|-------------|---------|
| EUR_USD | london_ny | Sweep London or NY session high/low |
| GBP_USD | london | Sweep London session high/low |
| XAU_USD | london_ny | Sweep London or NY session high/low |
| BTCUSD | any | Sweep any session (24/7 market) |

---

## NOVO: Session 26 (2026-02-07) - ISI (Institutional Sequence Intelligence)

### Problem

Confidence score 82-92% ne odgovara stvarnom win rate-u od 5.1% (2/39 trades). SMC detekcija radi point-in-time scoring umjesto sekvencijalnog razumijevanja institucionalnog ponasanja.

### Sto je implementirano?

**4 ISI komponente koje poboljsavaju kvalitetu signala:**

#### 1. Bayesian Confidence Calibration (Platt Scaling)
- **Fajl:** `src/analysis/confidence_calibrator.py`
- Kad sustav kaze "65% confidence", to ZAISTA znaci ~65% win rate
- Formula: `P(win) = 1 / (1 + exp(-(A * raw + B)))`
- Min 30 tradeova za prvi fit, refit svakih 50
- Brier score < 0.25 = dobra kalibracija
- Fallback: manual gradient descent ako scipy nedostupan

#### 2. Sequence Tracker (5-Phase Institutional Cycle)
- **Fajl:** `src/smc/sequence_tracker.py`
- Prati GDJE u institucionalnom ciklusu se instrument nalazi:

| Faza | Naziv | Confidence Modifier | Opis |
|------|-------|-------------------|------|
| 1 | ACCUMULATION | -20 | Range, ne trguj, cekaj |
| 2 | MANIPULATION | -10 | Sweep u tijeku, rano |
| 3 | DISPLACEMENT | +5 | Potvrda, ali kasno za entry |
| **4** | **RETRACEMENT** | **+15** | **OPTIMALNI ENTRY!** |
| 5 | CONTINUATION | +0 | OK ali rizicnije |

- Tranzicije: 1->2 (sweep u range), 2->3 (displacement+CHoCH), 3->4 (pullback u FVG/OB), 4->5 (nastavak), 5->1 (reset)
- DB persistence: stanja prezive restart

#### 3. Liquidity Heat Map (Predictive Density Scoring)
- **Fajl:** `src/smc/liquidity_heat_map.py`
- PREDVIDJA gdje ce se sweep dogoditi umjesto da ceka
- Kombinirano:
  - Postojece buyside/sellside levels
  - Session highs/lows (London=3.0, NY=2.5, Asian=2.0 tezina)
  - Equal highs/lows (3.0 tezina)
  - Temporal decay: `exp(-0.05 * hours)` (stariji = manje relevantni)
  - Touch count (vise testova = vise clustered stop-lossova)
- Output: `sweep_direction_probability` (0-1) i `primary_target`
- Koristi se za:
  - Poboljsani TP targeting (najjaci buyside/sellside level)
  - Sweep direction prediction (buyside heavy -> sellside sweep vjerojatniji)

#### 4. Cross-Asset Divergence Detection
- **Fajl:** `src/analysis/cross_asset_detector.py`
- Detektira institucionalnu aktivnost kroz korelacijske anomalije
- Poznate korelacije:
  - EUR/GBP: 0.85 (positive)
  - EUR/XAU: 0.40 (positive)
  - GBP/XAU: 0.30 (positive)
  - BTC: iskljucen (nema stabilne forex korelacije)
- Threshold: 1.5 sigma za signal
- Primjer: EUR_USD LONG, ali GBP_USD pada (korelacija pala s 0.85 na 0.3)
  -> EUR buying je SPECIFICNO za EUR -> confidence boost +10
- Modifier: -10 do +15, 30-min cache na candle podatke

### Novi fajlovi (4 komponente + 4 testa)

```
src/analysis/confidence_calibrator.py  # ISI F1: Platt Scaling
src/smc/sequence_tracker.py            # ISI F2: 5-phase cycle
src/smc/liquidity_heat_map.py          # ISI F3: Predictive density
src/analysis/cross_asset_detector.py   # ISI F4: Correlation divergence

tests/test_calibrator.py               # 6 tests
tests/test_sequence_tracker.py         # 9 tests
tests/test_heat_map.py                 # 8 tests
tests/test_cross_asset.py              # 9 tests
```

### Modificirani fajlovi (5)

```
src/utils/database.py             # +5 ISI tablice + 8 indexa
src/trading/auto_scanner.py       # Integracija svih 4 ISI komponenti
src/smc/smc_analyzer.py           # Heat map u HTF + TP targeting
src/analysis/llm_engine.py        # ISI kontekst u AI validation prompt
src/smc/__init__.py               # Export SequenceTracker
```

### Nove DB tablice

| Tablica | Svrha |
|---------|-------|
| `calibration_params` | Platt Scaling A/B parametri |
| `sequence_states` | Aktivna stanja sekvenci po instrumentu |
| `sequence_transitions` | Log faznih prijelaza |
| `sequence_completions` | Dovrseni ciklusi |
| `correlation_snapshots` | Cross-asset korelacijski snimci |

### Test Results

```
ISI Phase 1 (Calibrator):       6/6 PASSED
ISI Phase 2 (Sequence Tracker): 9/9 PASSED
ISI Phase 3 (Heat Map):         8/8 PASSED
ISI Phase 4 (Cross-Asset):      9/9 PASSED
Existing SMC Tests:             10/10 PASSED
TOTAL: 42/42 ALL PASSED
```

---

## Session 24 (2026-02-03) - Self-Upgrade System

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

---

## Session 23 (2026-02-03) - News API Integration

- **News Provider System** - Multi-provider (Finnhub, FMP, FF, Recurring)
- **Recurring Provider** - Auto-generira high-impact evente bez API kljuca
- **NewsFilter integracija** - async refresh, calendar status

---

## Session 22 (2026-02-03) - Modern AI Trading Upgrades (Phase 6)

- **Market Regime Detection** - ADX + Bollinger za TRENDING/RANGING/VOLATILE/LOW_VOL
- **External Sentiment** - VIX + News (Claude) + Calendar
- **Walk-Forward Validation** - Out-of-sample + Monte Carlo
- **Regime-Aware Learning** - Win rate po rezimu

---

## Account Status

```
Account: 62859209 (OANDA-TMS-Demo)
Balance: 48,517.30 EUR
Started: 50,000 EUR
Realized P/L: -1,163.15 EUR
Instruments: EUR_USD, GBP_USD, XAU_USD
Dry Run: TRUE
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

# Run SMC tests
python test_smc.py
```

**VAZNO:** MT5 terminal MORA biti pokrenut PRIJE Python servisa!

---

## Trenutne postavke (auto_trading.json)

```json
{
  "enabled": true,
  "dry_run": true,
  "min_confidence_threshold": 75,
  "risk_per_trade_percent": 0.3,
  "max_daily_trades": 3,
  "max_concurrent_positions": 5,
  "instruments": ["EUR_USD", "GBP_USD", "XAU_USD"],
  "stop_day": { "enabled": true, "loss_trigger": 2 },
  "scalping": {
    "target_rr": 2.0,
    "max_spread_pips": 2.0,
    "max_sl_pips": 15.0,
    "min_atr_pips": 5.0
  },
  "ai_validation": { "enabled": true, "reject_on_failure": true },
  "ai_override": { "enabled": false },
  "learning_mode": { "enabled": true, "target_trades": 50 },
  "market_regime": { "enabled": true },
  "external_sentiment": { "enabled": true },
  "self_upgrade": { "enabled": true }
}
```

---

## Arhitektura - SMC+ISI Trading Pipeline

```
AUTO-TRADING SERVICE (SMC+ISI MODE)

  SCAN -> SPREAD/SESSION/NEWS -> CANDLES (H4+H1+M5)
    |                              |
    |                              v
    |                    SMC HTF Analysis (H4/H1)
    |                    Structure + Liquidity + HEAT MAP [ISI]
    |                              |
    |                              | HTF Bias (BULLISH/BEARISH/NEUTRAL)
    |                              v
    |                    SMC LTF Analysis (M5)
    |                    Sweep + CHoCH/BOS + FVG + OB + Displacement
    |                              |
    |                              | Setup Grade (A+/A/B/NO_TRADE)
    |                              v
    |                    SEQUENCE TRACKER [ISI]
    |                    Phase 1-5 (modifier: -20 to +15)
    |                              |
    |    +--- Regime Filter --+-- Sentiment --+-- Learning --+
    |    |                    |               |              |
    |    v                    v               v              v
    |    CROSS-ASSET DIVERGENCE [ISI] (modifier: -10 to +15)
    |                              |
    |    Confidence = SMC + Sentiment + Sequence + Divergence
    |                              |
    |    BAYESIAN CALIBRATION [ISI] (Platt Scaling: raw -> calibrated)
    |                              |
    |              +-- Filter Chain (Self-Upgrade) --+
    |              |                                  |
    |              v                                  |
    |    SMC SL/TP (SL behind sweep, TP at HEAT MAP) |
    |              |                                   |
    |              v                                   |
    |    R:R Check (min 1:2) -> AI Validate -> EXECUTE |
    |                                                   |
    +-- 3 instruments every 60s -----------------------+

  STOP DAY: 2 losses = stop for the day
  Max 3 trades/day | 0.3% risk | R:R >= 2:1 | A/A+ setups only
  SL: ATR-based (max(min_sl_pips, ATR*multiplier))
  Partial TP: 50% close at 1.5R, SL -> breakeven
  Trailing Stop: ATR*1.0 after partial TP

  SELF-UPGRADE SYSTEM (daily)
  Analyze losses -> Generate filter -> Validate -> Backtest -> Deploy

Cilj: 200 EUR/dan = max 3 kvalitetna SMC+ISI tradea po ~70 EUR
```

---

## Kljucni fajlovi (prioritet)

| # | Fajl | Svrha |
|---|------|-------|
| 1 | `CLAUDE_CONTEXT.md` | Ovaj fajl - session kontekst |
| 2 | `settings/auto_trading.json` | Trading konfiguracija |
| 3 | `src/smc/smc_analyzer.py` | **SMC orchestrator + grading + heat map** |
| 4 | `src/smc/liquidity.py` | **Sweep detection (CRITICAL)** |
| 5 | `src/smc/structure.py` | **CHoCH, BOS, swing points** |
| 6 | `src/smc/zones.py` | **FVG, OB, premium/discount** |
| 7 | `src/smc/sequence_tracker.py` | **ISI: 5-phase institutional cycle** |
| 8 | `src/smc/liquidity_heat_map.py` | **ISI: Predictive liquidity density** |
| 9 | `src/analysis/confidence_calibrator.py` | **ISI: Bayesian calibration** |
| 10 | `src/analysis/cross_asset_detector.py` | **ISI: Correlation divergence** |
| 11 | `src/trading/auto_scanner.py` | SMC+ISI market scanner |
| 12 | `src/services/auto_trading_service.py` | Main loop + sync + upgrade cycle |
| 13 | `src/trading/auto_executor.py` | Trade executor + STOP DAY |
| 14 | `src/analysis/llm_engine.py` | AI validation (SMC+ISI rules) |
| 15 | `src/upgrade/upgrade_manager.py` | Self-Upgrade System |
| 16 | `src/market/indicators.py` | Technical (regime detection) |
| 17 | `src/trading/mt5_client.py` | MT5 connection |
| 18 | `src/backtesting/engine.py` | SMC+ISI Backtest Engine |
| 19 | `run_backtest_suite.py` | Backtest parameter grid + ISI comparison |
| 20 | `test_smc.py` | SMC test suite (10 tests) |
| 21 | `tests/test_*.py` | ISI test suite (32 tests) |

---

## Troubleshooting

### "No IPC connection" error?
```bash
# 1. Provjeri da je MT5 terminal pokrenut i ulogiran
# 2. Restartaj Python servis NAKON sto je MT5 upaljen
python run_auto_trading.py
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

### Run SMC tests
```bash
cd Dev
python test_smc.py
# Expected: 10/10 PASSED
```

### Run ISI tests
```bash
cd Dev
python tests/test_calibrator.py         # 6 tests
python tests/test_sequence_tracker.py   # 9 tests
python tests/test_heat_map.py           # 8 tests
python tests/test_cross_asset.py        # 9 tests
# Expected: 32/32 ALL PASSED
```

---

## Hard Limits (NIKAD se ne mogu zaobici!)

| Limit | Vrijednost |
|-------|------------|
| Max risk per trade | 3% |
| Max daily drawdown | 5% |
| Max weekly drawdown | 10% |
| Max concurrent positions | 10 |
| STOP DAY | 2 losses = stop for the day |
| No sweep = No trade | HARD GATE |
| No CHoCH/BOS = No trade | HARD GATE |

---

## Session Log

### Session 31 (2026-02-08) - SL/Entry/TP Improvements
- **ATR-based dynamic SL** - Fixed 7-pip buffer replaced with `max(min_sl_pips, ATR*multiplier)`
  - Per-instrument: EUR=10/1.3x, GBP=12/1.5x, XAU=50/2.0x, default=12/1.5x
  - `_calculate_atr_from_candles()` helper (manual calc, no deps, period=14)
- **Entry zone proximity** - `_check_entry_zone_proximity()` scores distance to FVG/OB
  - In zone: +10 conf, near (<=5 pips): +5, far (>10 pips): -15
  - `SMCAnalysis.current_price` field added, `grade_setup(analysis, instrument)` signature changed
- **Partial TP + trailing stop** in backtest engine:
  - `partial_tp_enabled=True`, close 50% at 1.5R, SL moves to breakeven
  - `trailing_stop_enabled=True`, trail by ATR*1.0 after partial TP hit
  - `_check_sl_tp()` now handles partial/trailing/breakeven logic
  - PnL = partial_pnl + remaining_pnl - commission
- **BacktestConfig defaults** - target_rr 3.0->2.0, max_sl_pips 15->30
- 50/50 tests PASS (10 SMC + 40 ISI/import), 15 stale tests pre-existing

### Session 30 (2026-02-08) - Fast Backtests + Walk-Forward + Finnhub
- **Finnhub API** activated (economic calendar = premium, stock quotes work)
- **Backtest suite optimized** - 256->16 configs, 264s (100x speedup)
- **Walk-Forward rewrite** - SMCBacktestEngine with H4/H1/M5, temp DB, Monte Carlo
- **Results** - all instruments losing (WR ~20-26%, PF 0.3-0.8)

### Session 29 (2026-02-08) - ISI in Backtest Engine
- **BacktestConfig** - 3 ISI toggle polja (isi_sequence_tracker, isi_cross_asset, isi_calibrator)
- **SimulatedTrade** - 6 ISI metadata polja (raw_confidence, calibrated_confidence, sequence_phase/name, modifiers)
- **BacktestCrossAssetAdapter** - Zamjenjuje MT5 CrossAssetDetector s pre-loaded M5 podacima (no look-ahead bias)
- **_generate_smc_signal** - ISI pipeline: seq_tracker before hard gates, div_modifier after direction, calibrator after raw
- **run()** - Novi `cross_asset_data` param, lazy-import ISI komponenti
- **run_backtest_suite.py** - XAU_USD M5 za cross-asset, ISI grid (noISI vs Seq+XA+Cal), ISI comparison table
- **42/42 testova PASS** (10 SMC + 32 ISI)

### Session 28 (2026-02-07) - Fresh Start Reset
- **DB hard reset** - all 16 tables cleared, backup: data/trades_backup_20260207_230705.db
- **SL buffer** - 3.0 -> 7.0 pips (smc_analyzer.py LONG+SHORT)
- **Settings** - threshold 80->75, max_daily 2->3, target_rr 3.0->2.0, learning target 50->30
- **dry_run: true** - keep until results validated

### Session 26 (2026-02-07) - ISI (Institutional Sequence Intelligence)
- **4 ISI komponente** - Calibration, Sequence, HeatMap, CrossAsset
- **Bayesian Calibration** - Platt Scaling (raw confidence -> calibrated)
- **Sequence Tracker** - 5-phase cycle (ACCUM/MANIP/DISP/RETRACE/CONT)
- **Liquidity Heat Map** - Predictive density + temporal decay + TP targeting
- **Cross-Asset Divergence** - EUR/GBP/XAU correlation anomalies
- **5 novih DB tablica** - calibration_params, sequence_states, transitions, completions, correlation_snapshots
- **Scanner integration** - ISI modifiers u confidence pipeline
- **AI validation** - ISI context (phase, divergence) u validation prompt
- **Tests** - 42/42 PASSED (32 new + 10 existing)
- **13 files total** - 5 modified + 8 created

### Session 25 (2026-02-07) - SMC Implementation
- **Kompletna zamjena decision core-a** - EMA/RSI/MACD -> Pure SMC
- **6 novih SMC fajlova** - structure, liquidity, zones, displacement, analyzer
- **Scanner rewrite** - SMC pipeline s hard gates (sweep, CHoCH/BOS)
- **Risk model** - 0.3% risk, max 2/day, STOP DAY, R:R min 3:1
- **Instruments** - Dropped USDJPY/AUDUSD, added XAU_USD
- **XAUUSD mapping** - Added to MT5 SYMBOL_MAP
- **AI validation** - SMC-based rules (7 rejection criteria)
- **Scalping** - SMC patterns (FVG_ENTRY, OB_ENTRY, SWEEP_REVERSAL)
- **Tests** - 10/10 PASSED
- **20 files total** - 13 modified + 7 created

### Session 24 (2026-02-03) - Self-Upgrade System
- Performance Analyzer, Code Generator, Code Validator
- Upgrade Executor, Upgrade Manager
- Filter Registry, Builtin Filters
- 9/9 tests PASSED

### Session 23 (2026-02-03) - News API Integration
- Multi-provider news system (Finnhub, FMP, Recurring)

### Session 22 (2026-02-03) - Modern AI Trading Upgrades (Phase 6)
- Market Regime, External Sentiment, Walk-Forward, Regime-Aware Learning

### Session 21 (2026-02-03) - Adaptive Settings + Optimizacija
- Auto-tuning, MT5 reconnect, konzervativne postavke

### Session 14-20 (2026-02-02-03)
- Full Auto Trading, AI Visibility, Learning Loop, Daemon, AI Override

---

## Session 27 (2026-02-07) - Validation, Cleanup & SMC Backtest Engine

### Sto je napravljeno?

**1. Sustav validacija vs svijet**
- Pretrazeno 30+ izvora (GitHub, akademski radovi, komercijalne platforme)
- **Ocjena: 62/100 ukupno** (75/100 bez production readiness i proven performance)
- **88/100 za inovativnost** - Self-upgrade i ISI su unikatni
- Report: `Brainstorming/System_Validation_Report.md`

**2. Upgrade roadmap do 85/100**
- 7 konkretnih promjena identificirano
- Najbitnije: backtest rezultati + ML model (Random Forest)
- Plan: `Brainstorming/Upgrade_Roadmap_85.md`

**3. Operativni playbook (Q1 2026)**
- 4 faze za sljedeca 3 mjeseca
- Dnevna/tjedna/mjesecna rutina
- Postepena eskalacija: dry run -> mikro live -> full live
- Plan: `Brainstorming/Operational_Playbook_Q1_2026.md`

**4. FTMO Integration Plan**
- TradingView analiza (webhooks, tvDatafeed, PineConnector)
- FTMO kompatibilnost dokumentirana (MT5 = vec podrzano)
- Plan: `Brainstorming/FTMO_Plan.md`

**5. Cleanup & popravke**
- Zombie EUR_JPY trade ociscen iz DB (id=39, MANUAL_CLEANUP)
- BTCUSD uklonjen iz instrumenata (MT5 "No price data" error)
- XAU_USD dodan nazad u instrumente
- dry_run postavljeno na TRUE (bilo false!)
- Svi SMC+ISI testovi prolaze: 42/42 PASS
- 15 starijih testova (orders_security, risk_manager) trebaju update

**6. SMC BacktestEngine (NOVO!)**
- `src/backtesting/engine.py` - kompletno prepisan za SMC pipeline
- Multi-timeframe: H4 + H1 + M5 (pravi MTF backtest)
- Koristi SMCAnalyzer (isti pipeline kao auto_scanner)
- Hard gates: HTF bias, sweep, CHoCH/BOS, grade, R:R
- Market regime filter
- Session filter
- Spread + slippage + commission simulacija

**7. Backtest rezultati (EUR_USD 90d)**
- Stari pipeline: 179 trades, WR=24%, P/L=-39,173 EUR, DD=82%
- **SMC pipeline: 26 trades, WR=7.7%, P/L=-3,578 EUR, DD=7.63%**
- SMC je selektivniji (26 vs 179) i kontrolira drawdown (7.6% vs 82%)
- Problem: 92% tradeova zavrsava na SL - SL buffer preuzak (3 pips)

**8. Bug fix: smc_analyzer.py**
- `heat_map` varijabla bila undefined u SHORT grani `_calculate_sl_tp()`
- Fix: definirana `heat_map = analysis.heat_map` prije if/else bloka

### Novi fajlovi
```
Brainstorming/System_Validation_Report.md    # Validacija vs svijet (62/100)
Brainstorming/Upgrade_Roadmap_85.md          # 7 promjena za 85/100
Brainstorming/Operational_Playbook_Q1_2026.md # 3-mjesecni operativni plan
Brainstorming/FTMO_Plan.md                   # FTMO integration plan
backtest_results/EUR_USD_SMC_90d.json        # SMC backtest rezultati
```

### Modificirani fajlovi
```
src/backtesting/engine.py          # KOMPLETNO PREPISAN za SMC pipeline
src/smc/smc_analyzer.py            # Bug fix: heat_map u _calculate_sl_tp
settings/auto_trading.json         # BTCUSD -> XAU_USD, dry_run=true
```

### Poznati problemi za sljedecu sesiju
1. **15 starijih testova** - orders_security, risk_manager trebaju update
2. **Calibrator uncalibrated** - Treba min 30 zatvorenih tradeova za Platt Scaling fit
3. **Strategija jos nije profitabilna** - WR 20-27%, PF 0.3-0.8 (Session 30 backtests)
4. **Treba pokrenuti backtest suite** - Validirati Session 31 SL/Entry/TP poboljsanja

---

*Zadnje azuriranje: 2026-02-08 | Session 31 - SL/Entry/TP Improvements*
