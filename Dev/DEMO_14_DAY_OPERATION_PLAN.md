# Demo 14-Day Operation Plan

## 1) Day 1 Setup
- Start demo live with current settings.
- Confirm startup flags in logs:
  - `smc_v2.enabled=true`
  - `grade_execution.enabled=true`
  - `killzone_gate_live=true`
  - `htf_poi_gate_live=true`
  - `market_order_fallback_enabled=false`
- Save baseline:
  - start date/time
  - balance/equity
  - active config snapshot

## 2) Daily Routine (Day 1-14)
- Extract per instrument:
  - `scans`
  - `signals`
  - `trades`
  - top `block_reason_primary`
- Record:
  - `A+` count and `A` count
  - count reaching `PRE_EXECUTOR_CHECKPOINT`
  - count blocked by:
    - `SL cap`
    - `HTF_POI`
    - `killzone`
    - `NO_CHOCH_BOS`
- Save:
  - daily PnL
  - max intraday drawdown

## 3) Day 3 Checkpoint
- If `XAU` has 0 setups and 0 trades:
  - do not change settings yet
  - confirm dominant block reason (`NO_CHOCH_BOS` / `NO_SWEEP` / other)

## 4) Day 5 Checkpoint
- If `GBP` still has 0 trades:
  - consider temporary focus on `EUR + XAU` for the rest of the cycle
- If `EUR` has trades but weak result:
  - no immediate change (need larger sample)

## 5) Day 7 Mid-Review
- Decision rules:
  - if total trades `< 5`, system is too restrictive
  - if demo DD `> 3%`, pause tuning and inspect execution
- Only if trade count is too low:
  - apply exactly one small instrument-specific relax

## 6) Allowed One-Step Relax (Only If Needed)
- Priority: `XAU` frequency/entry relax (one parameter only)
- Do not change:
  - `killzone` hard gate
  - `htf_poi` hard gate
  - `market_order_fallback=false`

## 7) Day 10 Checkpoint
- Compare before/after:
  - trade count
  - setup quality (`A/A+` share)
  - drawdown
- Keep change only if trade count improves without DD deterioration.
- Rollback if quality drops or DD worsens.

## 8) Day 14 Final Review
- Minimum criteria to continue:
  - `>= 10` trades total in demo period
  - stable DD (target `< 3%`)
  - no technical anomalies in `SMC_V2_EVAL` logs
- Outcome:
  - `GO`: keep setup for next 2-4 weeks
  - `TUNE`: one additional small targeted relax
  - `ROLLBACK`: revert last change

## 9) Daily Tracking Template
- `date`
- `instrument`
- `scans / signals / trades`
- `A+ count / A count`
- `top_block_reasons`
- `PnL day`
- `max_dd day`
- `notes`

## 10) Hard Safety Rules
- Keep demo risk at `0.3%` per trade.
- Never apply more than one change at a time.
- After each change, wait at least 3-5 days before next change.

## 11) Current Temporary Demo Overrides (2026-02-10)
- Goal:
  - increase probability of first executable demo trade while keeping core SMC gates active.
- Applied in `settings/auto_trading.json`:
  - `dry_run=false`
  - `ai_validation.enabled=true`
  - `ai_validation.reject_on_failure=false` (demo pass-through; AI remains advisory)
  - `smc_v2.risk.min_rr.A+=0.1`
  - `smc_v2.risk.min_rr.A=0.2`
  - `smc_v2.risk.min_rr.B=0.5`
  - `smc_v2.killzone_gate.always_true=true`
  - `smc_v2.grade_execution.enforce_live_hard_gates=false` (demo relax)
  - `smc_v2.risk.fx_sl_caps.max_pips=25.0` (demo relax from 18.0)
- Kept unchanged on purpose:
  - `smc_v2.enabled=true`
  - `grade_execution.enabled=true`
  - `killzone_gate_live=true`
  - `htf_poi_gate_live=true`
  - `market_order_fallback_enabled=false`
- Why this was done:
  - runtime logs showed valid setup structure was appearing, but entries were blocked primarily by RR threshold, resulting in zero executions.
  - AI validator was repeatedly rejecting otherwise executable demo signals due strict RR policy (3.0), so validation is now advisory during bootstrap.
  - additionally, runtime was frequently outside killzone windows, so demo bootstrap now forces `within_killzone=true` via explicit override flag.
  - additional blockers were persistent FX SL cap rejections (`>18 pips`) and forced live hard-gate scope for XAU/GBP; demo relax reduces false negatives while still keeping SMC grade/confidence controls.
- Revert plan (after bootstrap sample):
  - after first 3-5 demo trades, restore `ai_validation.reject_on_failure=true`.
  - after first 3-5 demo trades, restore RR gates toward baseline (`A+=3.0`, `A=2.5`, `B=2.0`) in one step.
  - keep one config snapshot before and after each rollback/tuning step.

## 12) Runtime/Dashboard Sync Hardening (2026-02-11)
- Implemented:
  - scanner now persists `scanner_stats` every scan (`total_scans`, `avg_scan_duration_ms` now reflect runtime).
  - `auto_signals` now stores final signal `entry_price` and final `risk_reward` (after limit-entry recalculation).
  - pending-limit lifecycle now updates DB on fill/expiry:
    - fill creates/updates trade mapping (`AUTO_SCALPING_LIMIT`) and marks signal as executed.
    - expiry updates signal skip reason.
  - service running-state now treats naive timestamps as local time (timezone-safe status on dashboard).
- Expected effect:
  - Home/Ops and Runtime Audit counters should match terminal/runtime behavior with much smaller drift.

## 13) Mild Demo Relax Update (2026-02-11)
- Goal:
  - allow first live-demo executions without removing core SMC structure checks.
- Applied in `settings/auto_trading.json`:
  - `ai_validation.enabled=false` (temporary; AI validator currently over-rejects demo-viable setups)
  - `smc_v2.grade_execution.min_confidence_a=55` (from 58)
  - `smc_v2.htf_poi_gate.enabled=false` (temporary bootstrap relax)
- Kept unchanged:
  - `smc_v2.enabled=true`
  - `grade_execution.enabled=true`
  - `market_order_fallback_enabled=false`
  - `killzone_gate.always_true=true` (demo bootstrap mode)
- Revert plan:
  - after first 3-5 executed demo trades, re-enable in order:
    1) `smc_v2.htf_poi_gate.enabled=true`
    2) `ai_validation.enabled=true`
    3) raise `min_confidence_a` back to 58-60

## 14) Bootstrap Relax v2 (2026-02-11)
- Goal:
  - break persistent `0 trades` state caused by repeated LTF `No CHoCH/BOS` and `No clear direction` blocks.
- Applied:
  - `min_confidence_threshold=65` (from 75)
  - `smc_v2.grade_execution.enabled=false` (temporary, demo only)
  - `limit_entry.allow_market_fallback=true` (temporary, to allow market execution when no pending-limit placement path exists)
  - scanner fallback in demo relax mode (`enforce_live_hard_gates=false`):
    - if sweep + displacement exist and CHoCH/BOS is missing, use `candidate_direction`
    - if direction missing, fallback to `candidate_direction`
    - if setup is `NO_TRADE` but direction+sweep exist, promote to `B`
  - fixed setup-label telemetry serialization to avoid JSON bool-type logging errors.
- Safety retained:
  - `market_order_fallback=false`
  - SL cap checks retained
  - spread/news/session prefilters retained
- Mandatory rollback after first fills:
  - set `limit_entry.allow_market_fallback=false`
  - re-enable `smc_v2.grade_execution.enabled=true`
  - restore confidence threshold to `70-75`
  - keep only one relax active at a time.

## 15) Mandatory Runtime Startup Protocol (ALWAYS)
- Scope:
  - this is mandatory whenever starting runtime from Codex session.
  - do not run only one component; all components below must be started and verified.
- Required startup order:
  - start `auto-trading`:
    - `Set-Location "C:\Users\mglav\Projects\AI Trader\Dev"`
    - `python run_auto_trading.py`
  - start `dashboard` with proxy-safe flags:
    - `python -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501 --server.enableCORS false --server.enableXsrfProtection false`
  - ensure Tailscale public access:
    - `tailscale serve reset`
    - `tailscale serve --bg 8501`
    - `tailscale funnel --bg 8501`
    - `tailscale funnel status`
- Mandatory post-start checks:
  - `netstat -ano | findstr :8501` must show `LISTENING`.
  - `tailscale funnel status` must show:
    - `Funnel on`
    - `proxy http://127.0.0.1:8501`
    - active public URL (`https://...ts.net`).
  - confirm heartbeat exists:
    - `Dev/data/.heartbeat.json`
- Operational note:
  - if URL stops working after restarts, re-run full `serve reset -> serve --bg 8501 -> funnel --bg 8501` sequence.
  - quick path: run `Dev/start_all_runtime.bat` to start auto-trading + dashboard + funnel in one step.

## 16) Trade Limit Update (2026-02-11)
- Request:
  - increase daily trade capacity to avoid repeated `Daily trade limit reached (2/2) [LEARNING]`.
- Applied in `settings/auto_trading.json`:
  - `max_daily_trades=4`
  - `max_trades_per_instrument=4`
  - `learning_mode.aggressive_settings.max_daily_trades=4`
  - `learning_mode.aggressive_settings.max_trades_per_instrument=4`
  - `learning_mode.production_settings.max_daily_trades=4`
  - `learning_mode.production_settings.max_trades_per_instrument=4`
- Scope:
  - effective for active demo instruments, including `EUR_USD` and `GBP_USD`.

## 17) Recovery-Safe Test Day Profile (2026-02-11, for 2026-02-12)
- reason:
  - after large same-day drawdown, switch to strict discipline profile for next test day
- applied config:
  - `risk_per_trade_percent=0.25`
  - `max_daily_trades=2`
  - `max_trades_per_instrument=1`
  - `learning_mode.aggressive_settings.max_daily_trades=2`
  - `learning_mode.aggressive_settings.max_trades_per_instrument=1`
  - `learning_mode.production_settings.max_daily_trades=2`
  - `learning_mode.production_settings.max_trades_per_instrument=1`
  - `limit_entry.allow_market_fallback=false`
  - `smc_v2.grade_execution.enabled=true`
  - `smc_v2.grade_execution.a_plus_only_live=true`
  - `smc_v2.grade_execution.enforce_live_hard_gates=true`
  - `smc_v2.htf_poi_gate.enabled=true`
  - `smc_v2.killzone_gate.enabled=true`
  - `smc_v2.killzone_gate.always_true=false`
  - `smc_v2.strict_sweep.enabled=true`
  - `smc_v2.strict_fvg.enabled=true`
  - `smc_v2.news_gate.enabled=true`
  - `smc_v2.news_gate.block_minutes=30`
  - `smc_v2.risk.min_rr.A+=3.0`
  - `smc_v2.risk.min_rr.A=2.5`
  - `smc_v2.risk.min_rr.B=2.0`
  - `smc_v2.risk.fx_sl_caps.max_pips=18.0`
  - `smc_v2.risk.xau_sl_caps.max_points=450`
- operational note:
  - profile is intentionally strict for one full test day; relax only after stable behavior

## 18) Intraday Capacity Update (2026-02-12)
- reason:
  - allow additional A/A+ opportunities without disabling quality filters
- applied:
  - `max_daily_trades=6`
  - `max_trades_per_instrument=3`
  - `learning_mode.aggressive_settings.max_daily_trades=6`
  - `learning_mode.aggressive_settings.max_trades_per_instrument=3`
  - `learning_mode.production_settings.max_daily_trades=6`
  - `learning_mode.production_settings.max_trades_per_instrument=3`
- unchanged (still strict):
  - `smc_v2.grade_execution.enabled=true`
  - `smc_v2.grade_execution.a_plus_only_live=true`
  - `limit_entry.allow_market_fallback=false`
  - `smc_v2.strict_sweep.enabled=true`
  - `smc_v2.strict_fvg.enabled=true`
  - `smc_v2.htf_poi_gate.enabled=true`
  - `smc_v2.killzone_gate.enabled=true`

## 19) Micro-Relaxation (2026-02-12)
- reason:
  - keep strict safety profile, but reduce over-blocking during valid intraday windows
- applied:
  - `smc_v2.killzone_gate.always_true=true`
  - `smc_v2.risk.min_rr.A+=2.5` (from `3.0`)
  - `smc_v2.risk.min_rr.A=2.2` (from `2.5`)
  - `smc_v2.htf_poi_gate.allow_neutral_with_liquidity_edge=true`
  - `smc_v2.htf_poi_gate.neutral_liquidity_edge_min=1`
- unchanged:
  - `smc_v2.grade_execution.enabled=true`
  - `smc_v2.grade_execution.a_plus_only_live=true`
  - `smc_v2.strict_sweep.enabled=true`
  - `smc_v2.strict_fvg.enabled=true`
  - `smc_v2.htf_poi_gate.enabled=true`
  - `limit_entry.allow_market_fallback=false`
