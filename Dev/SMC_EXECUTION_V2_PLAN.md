# SMC Execution v2 - Implementation Plan

## 1. Objective

Implement a stricter, higher-quality execution framework based on:

- Grade-driven live trading (`A+`, `A` live; `B` shadow-only)
- Stronger SMC gates (HTF POI/range, strict sweep, strict FVG)
- Instrument-aware SL/RR controls (XAU vs FX)
- Killzone/news hard blocks
- Better learning labels for self-upgrade

The goal is to improve expectancy and reduce low-quality entries without breaking current production flow.

## 2. Design Principles

- Preserve current pipeline shape and logging style.
- Add all major changes behind feature flags.
- Enforce unit consistency (`price_distance` internal; convert to pips/points for display).
- Introduce gates incrementally (shadow-first rollout).
- Keep backward compatibility for current config and DB data.

## 3. Scope Summary

### 3.1 Live execution policy

- Live allowed only for:
  - `A+` with `confidence >= 45` (0-100 scale)
  - `A` with `confidence >= 60` (0-100 scale)
- `B` and `NO_TRADE`:
  - no live execution
  - still logged for training/shadow analytics

### 3.2 RR policy

- `A+`: `min_rr = 3.0`
- `A`: `min_rr = 2.5`
- `B`: `min_rr = 2.0` (shadow only)

### 3.3 SL policy

- XAU:
  - min cap `120 points`
  - max cap `450 points`
- FX:
  - min cap `4 pips`
  - max cap `18 pips`
- Formula:
  - `SL = max(distance_to_sweep, ATR_M5 * 1.2)`
  - clamp to min cap
  - block trade if above max cap

### 3.4 Mandatory gates

- Killzone gate (instrument-specific)
- News gate (`<= 15 min` high-impact)
- HTF POI/range gate
- Strict sweep validation
- Confirmed direction required (`CHoCH`/`BOS`)
- Grade-aware RR + SL cap gates

### 3.5 Learning labels

Persist enriched label set per evaluated setup (including shadow rejections) for self-upgrade.

## 4. Configuration Changes

Update `Dev/settings/auto_trading.json` and config dataclasses with new keys:

- `smc_v2.enabled` (bool)
- `smc_v2.shadow_mode` (bool)
- `smc_v2.grade_execution.enabled` (bool)
- `smc_v2.grade_execution.min_confidence_a_plus` (int, default 45)
- `smc_v2.grade_execution.min_confidence_a` (int, default 60)
- `smc_v2.strict_sweep.enabled` (bool)
- `smc_v2.strict_fvg.enabled` (bool)
- `smc_v2.htf_poi_gate.enabled` (bool)
- `smc_v2.killzone_gate.enabled` (bool)
- `smc_v2.news_gate.enabled` (bool)
- `smc_v2.news_gate.block_minutes` (int, default 15)
- `smc_v2.risk.min_rr` map by grade
- `smc_v2.risk.fx_sl_caps` and `smc_v2.risk.xau_sl_caps`

Add per-instrument killzone profile fields into `Dev/settings/instrument_profiles.json`:

- `killzone_windows_utc`
- `news_currencies`

## 5. Code Changes by File

## 5.1 Core Config

- `Dev/src/core/auto_config.py`
  - add nested `SMCv2Config` dataclasses
  - parse/save new config keys
  - keep defaults backward-compatible

## 5.2 SMC Data Models and Detection

- `Dev/src/smc/liquidity.py`
  - extend `LiquiditySweep`:
    - `close_back_inside: bool`
    - `valid_rejection: bool`
    - `displacement_after: bool`
  - implement strict sweep validation helper

- `Dev/src/smc/zones.py`
  - extend `FairValueGap` metadata:
    - `gap_atr_ratio`
    - `is_part_of_displacement`
    - `aligns_with_htf_bias`
    - `in_htf_poi`
  - add strict FVG filter function

- `Dev/src/smc/smc_analyzer.py`
  - integrate new sweep/FVG filters
  - add HTF range position gate helper
  - split grade scoring from execution gating output
  - add structured gate results object (why/no-go)

## 5.3 Scanner and Execution

- `Dev/src/trading/auto_scanner.py`
  - add `evaluate_setup_v2(...)`
  - apply hard gates in order:
    1) pre-filters
    2) killzone/news
    3) HTF POI/range
    4) sweep strict
    5) direction confirm
    6) grade-aware risk checks
  - `B` -> shadow logging only
  - keep `WHY/NEXT` explain logs for each gate

- `Dev/src/trading/auto_executor.py`
  - enforce grade-based live permission
  - reject execution if `setup_grade` not allowed
  - log explicit reason and retain shadow label

## 5.4 Risk / Units

- `Dev/src/utils/helpers.py` or dedicated new module `Dev/src/trading/units.py`
  - add unified conversion helpers:
    - `price_distance_to_points(...)`
    - `price_distance_to_pips(...)`
    - `points_to_price_distance(...)`
    - `pips_to_price_distance(...)`

- `Dev/src/trading/auto_scanner.py`
  - SL cap checks via unified units

- `Dev/src/trading/orders.py`
  - ensure spread/SL comparisons use same unit standard

## 5.5 News/Killzone Gate

- `Dev/src/trading/auto_scanner.py`
  - enforce instrument-specific killzone gate as hard gate for live
  - enforce high-impact news window gate (`<= block_minutes`)
  - keep scanning active outside killzone (no execution)

## 5.6 Learning / Dataset

- `Dev/src/analysis/learning_engine.py`
  - add method to store setup evaluation labels even when not executed
  - add fields:
    - grade
    - sweep_quality
    - fvg_quality
    - poi_quality
    - session
    - regime
    - outcome placeholder
    - actual_rr
    - time_in_trade
    - sl_distance
    - spread_at_entry

- `Dev/src/utils/database.py`
  - new table `setup_labels` (or extend existing table)
  - indexes by `instrument`, `grade`, `session`, `regime`, `timestamp`

## 5.7 UI / Monitoring

- `Dev/pages/11_Monitoring.py` (if used)
  - add rejection reason distribution
  - add grade distribution (`A+`, `A`, `B`, `NO_TRADE`)
  - add shadow-vs-live counts

- `Dev/pages/13_AutoTrading.py`
  - show active SMC v2 flags and gate statuses

## 6. Phase Plan

## Phase 0 - Baseline Snapshot

- freeze baseline metrics:
  - scan count
  - signal count
  - execution count
  - win rate
  - expectancy
  - avg RR
  - rejection reasons
- create baseline report artifact in `Dev/backtest_results/`

## Phase 1 - Plumbing and Flags (No behavior change)

- add config keys and defaults
- add models/helpers for strict sweep/FVG/units
- add DB migrations for labels
- verify no behavior change with flags off

## Phase 2 - Shadow Evaluation Engine

- implement full v2 gate evaluator
- run in shadow mode only
- store labels and gate decisions
- no live execution changes yet

## Phase 3 - Live `A+` Only

- enable live execution only for `A+`
- keep `A`/`B` in shadow
- monitor 1-2 weeks or minimum N setups

## Phase 4 - Live `A+` + `A`

- enable `A` with confidence threshold
- keep `B` shadow-only
- monitor acceptance and expectancy changes

## Phase 5 - Calibration and Tuning

- tune thresholds:
  - confidence (`A+`, `A`)
  - RR minima
  - sweep/fvg strictness
  - HTF range threshold
- update defaults only after statistical confirmation

## 7. Testing Plan

## 7.1 Unit tests

- `tests/test_smc_v2_sweep.py`
- `tests/test_smc_v2_fvg.py`
- `tests/test_smc_v2_htf_gate.py`
- `tests/test_smc_v2_grade_execution.py`
- `tests/test_units_conversion.py`

## 7.2 Integration tests

- scanner end-to-end with v2 flags off -> parity with current behavior
- scanner with v2 shadow on -> deterministic gate outputs
- executor blocking non-live grades

## 7.3 Regression tests

- existing `Dev/tests/` suite must pass
- no schema regressions in `trades.db`

## 8. Rollout and Rollback

Rollout sequence:

1. deploy with all v2 flags off
2. enable shadow mode only
3. enable `A+` live
4. enable `A` live

Rollback:

- single switch: `smc_v2.enabled = false`
- preserve labels/logs for post-mortem

## 9. Acceptance Criteria

- no runtime crashes when toggling v2 flags
- all live trades satisfy v2 checklist
- `B` never executes live
- explain logs show exact gate reason for every skip
- measurable improvement vs baseline on expectancy and drawdown profile

## 10. Immediate Implementation Order (Next Actions)

1. Implement Phase 1 config and dataclass updates.
2. Add `setup_labels` DB table + write path.
3. Add strict sweep fields and logic.
4. Add strict FVG filter and metadata.
5. Build `evaluate_setup_v2` in scanner (shadow only).
6. Add grade-based execution filter in executor.
7. Add tests and run full regression.

## 11. Deferred Finalization Note (Added 2026-02-09)

Decision: Do NOT close all remaining v2 tasks immediately.

Reason:
- The system now has SMC v2 shadow telemetry, grade gates, and rollout presets.
- Final hardening/tuning without fresh live sample risks overfitting and unnecessary churn.

Execution plan before final closure:
1. Run `A+ Live` preset for 24-72h with `shadow_mode=true`.
2. Monitor in `pages/13_AutoTrading.py` -> `SMC v2 Shadow`:
   - allow_rate / block_rate
   - top block reasons
   - gate pass rates (`fvg_valid`, `rr_pass`, `htf_poi_gate`, `sweep_valid`)
   - instrument breakdown
3. Export `setup_labels` CSV daily and snapshot key metrics.

Go/No-Go for moving to `A+ & A Live`:
- Keep `A+` only if quality gates are unstable (low pass-rates or deteriorating execution quality).
- Move to `A+ & A` only if shadow/live metrics remain stable for at least 24h and no risk anomalies are observed.

Deferred items to close after observation window:
- Full deep SMC model refactors listed in sections 5.2/5.4 (where still partial).
- Final threshold calibration (Phase 5) using collected dataset.
- Complete planned test matrix and acceptance checklist sign-off.

## 12. Immediate Run Recommendation (Added 2026-02-09)

Recommended next runtime profile:
- Keep `smc_v2.enabled=true`
- Keep `smc_v2.grade_execution.enabled=true`
- Turn ON strict gates for first observation window:
  - `smc_v2.strict_sweep.enabled=true`
  - `smc_v2.strict_fvg.enabled=true`
- Optional safety-first mode for first 24h:
  - `smc_v2.grade_execution.a_plus_only_live=true`

Observation window (24-48h):
- Monitor in `AutoTrading -> SMC v2 Shadow`:
  - allow_rate
  - top block reasons
  - gate pass rates (`fvg_valid`, `htf_poi_gate`, `rr_pass`)
  - instrument breakdown

Adjustment rule:
- If allow_rate drops too low and execution quality degrades, relax only `strict_fvg` first (keep strict sweep ON).

Runtime readiness:
- System is runnable with current implementation.
- Core gates active now: v2 enabled + grade execution enabled + hard live killzone/HTF POI for XAU/GBP.
- Market fallback is disabled unless explicitly enabled (`limit_entry.allow_market_fallback`).
