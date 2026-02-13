"""
SMC Backtest Suite - Optimized Parameter Grid

Reduced grid (16 configs vs 256) + multiprocessing for fast execution.
Tests: 2 instruments x 8 configs = 16 total, target <5 min.
"""

import sys
import os
import json
import time
import argparse
import tempfile
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_single_backtest(args):
    """
    Run a single backtest config in a worker process.

    Module-level function required for ProcessPoolExecutor on Windows.
    Each worker creates its own engine + metrics calculator.
    """
    (label, instrument, h4_candles, h1_candles, m5_candles,
     config_dict, cross_asset_data) = args

    # Import inside worker (each process needs its own)
    from src.backtesting.engine import SMCBacktestEngine, BacktestConfig
    from src.backtesting.metrics import MetricsCalculator

    # ISI DB isolation: use temp DB per worker
    isi_enabled = (
        config_dict.get("isi_sequence_tracker", False) or
        config_dict.get("isi_cross_asset", False) or
        config_dict.get("isi_calibrator", False)
    )
    temp_db_path = None

    if isi_enabled:
        temp_db_path = tempfile.mktemp(suffix=f"_bt_{os.getpid()}.db")
        import src.utils.database as db_module
        db_module._db_path = Path(temp_db_path)

    try:
        config = BacktestConfig(**config_dict)
        engine = SMCBacktestEngine()
        calc = MetricsCalculator()

        t0 = time.time()
        try:
            result = engine.run(
                h4_candles, h1_candles, m5_candles, config,
                cross_asset_data=cross_asset_data,
            )
        except Exception as e:
            return {"label": label, "error": str(e)}

        elapsed = time.time() - t0

        if result.trades:
            metrics = calc.calculate(result)
        else:
            metrics = None

        # Trade breakdown
        winners = [t for t in result.trades if t.pnl > 0]
        losers = [t for t in result.trades if t.pnl <= 0]

        # Grade distribution
        grades = {}
        for t in result.trades:
            g = t.setup_grade
            grades[g] = grades.get(g, 0) + 1

        # Direction distribution
        longs = sum(1 for t in result.trades if t.direction.value == "LONG")
        shorts = len(result.trades) - longs

        # Top skip reasons
        top_skips = sorted(result.skip_reasons.items(), key=lambda x: -x[1])[:5]

        # ISI metadata summary
        isi_phases = {}
        total_seq_mod = 0
        total_div_mod = 0
        for t in result.trades:
            if t.sequence_phase_name:
                isi_phases[t.sequence_phase_name] = isi_phases.get(t.sequence_phase_name, 0) + 1
            total_seq_mod += t.sequence_modifier
            total_div_mod += t.divergence_modifier

        summary = {
            "label": label,
            "instrument": config.instrument,
            "min_confidence": config.min_confidence,
            "target_rr": config.target_rr,
            "check_regime": config.check_regime,
            "check_session": config.check_session,
            "session_hours": config.session_hours,
            "isi_enabled": isi_enabled,
            "trades": len(result.trades),
            "signals_generated": result.signals_generated,
            "signals_skipped": result.signals_skipped,
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": (len(winners) / len(result.trades) * 100) if result.trades else 0,
            "return_pct": metrics.total_return_pct if metrics else 0,
            "return_abs": metrics.total_return_abs if metrics else 0,
            "max_dd_pct": metrics.max_drawdown_pct if metrics else 0,
            "sharpe": metrics.sharpe_ratio if metrics else None,
            "profit_factor": metrics.profit_factor if metrics else None,
            "expectancy": metrics.expectancy if metrics else 0,
            "avg_win": metrics.avg_win if metrics else 0,
            "avg_loss": metrics.avg_loss if metrics else 0,
            "largest_win": metrics.largest_win if metrics else 0,
            "largest_loss": metrics.largest_loss if metrics else 0,
            "max_consec_wins": metrics.max_consecutive_wins if metrics else 0,
            "max_consec_losses": metrics.max_consecutive_losses if metrics else 0,
            "longs": longs,
            "shorts": shorts,
            "grades": grades,
            "top_skips": top_skips,
            "run_time": elapsed,
            "final_equity": result.final_equity,
            # ISI summary
            "isi_phases": isi_phases if isi_phases else None,
            "avg_seq_modifier": (total_seq_mod / len(result.trades)) if result.trades else 0,
            "avg_div_modifier": (total_div_mod / len(result.trades)) if result.trades else 0,
        }
        return summary

    finally:
        # Cleanup temp DB
        if temp_db_path:
            # Restore default path for this process
            import src.utils.database as db_module
            _dev_dir = Path(__file__).parent
            db_module._db_path = _dev_dir / "data" / "trades.db"
            if os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except Exception:
                    pass


def print_summary_table(results):
    """Print comparison table of all results."""
    print("\n" + "=" * 130)
    print("BACKTEST RESULTS COMPARISON")
    print("=" * 130)

    hdr = (
        f"{'Config':<40} {'Trades':>6} {'Win%':>6} {'Return%':>9} "
        f"{'Return$':>10} {'MaxDD%':>7} {'PF':>6} {'Exp$':>8} "
        f"{'Sharpe':>7} {'W/L':>5} {'Time':>5}"
    )
    print(hdr)
    print("-" * 130)

    for r in results:
        if "error" in r:
            print(f"{r['label']:<40} ERROR: {r['error']}")
            continue

        pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] else "N/A"
        sh_str = f"{r['sharpe']:.2f}" if r['sharpe'] else "N/A"

        row = (
            f"{r['label']:<40} {r['trades']:>6} {r['win_rate']:>5.1f}% "
            f"{r['return_pct']:>+8.2f}% {r['return_abs']:>+9.2f} "
            f"{r['max_dd_pct']:>6.2f}% {pf_str:>6} {r['expectancy']:>+7.2f} "
            f"{sh_str:>7} "
            f"{r['max_consec_wins']}/{r['max_consec_losses']:>1} "
            f"{r['run_time']:>4.0f}s"
        )
        print(row)

    print("=" * 130)


def print_best_configs(results):
    """Identify and print best configurations."""
    valid = [r for r in results if "error" not in r and r["trades"] > 0]

    if not valid:
        print("\nNo valid results to analyze!")
        return

    print("\n" + "=" * 80)
    print("BEST CONFIGURATIONS")
    print("=" * 80)

    best_return = max(valid, key=lambda x: x["return_pct"])
    print(f"\nBest Return:        {best_return['label']}")
    print(f"  Return: {best_return['return_pct']:+.2f}% | "
          f"Trades: {best_return['trades']} | "
          f"Win Rate: {best_return['win_rate']:.1f}%")

    with_trades = [r for r in valid if r["trades"] >= 5]
    if with_trades:
        best_wr = max(with_trades, key=lambda x: x["win_rate"])
        print(f"\nBest Win Rate (5+): {best_wr['label']}")
        print(f"  Win Rate: {best_wr['win_rate']:.1f}% | "
              f"Trades: {best_wr['trades']} | "
              f"Return: {best_wr['return_pct']:+.2f}%")

    with_pf = [r for r in (with_trades or valid) if r.get("profit_factor") is not None]
    if with_pf:
        best_pf = max(with_pf, key=lambda x: x["profit_factor"])
        print(f"\nBest Profit Factor: {best_pf['label']}")
        print(f"  PF: {best_pf['profit_factor']:.2f} | "
              f"Trades: {best_pf['trades']} | "
              f"Return: {best_pf['return_pct']:+.2f}%")

    with_sharpe = [r for r in (with_trades or valid) if r.get("sharpe") is not None]
    if with_sharpe:
        best_sh = max(with_sharpe, key=lambda x: x["sharpe"])
        print(f"\nBest Sharpe Ratio:  {best_sh['label']}")
        print(f"  Sharpe: {best_sh['sharpe']:.2f} | "
              f"Trades: {best_sh['trades']} | "
              f"Return: {best_sh['return_pct']:+.2f}%")

    if with_trades:
        lowest_dd = min(with_trades, key=lambda x: x["max_dd_pct"])
        print(f"\nLowest Drawdown:    {lowest_dd['label']}")
        print(f"  MaxDD: {lowest_dd['max_dd_pct']:.2f}% | "
              f"Trades: {lowest_dd['trades']} | "
              f"Return: {lowest_dd['return_pct']:+.2f}%")

    print(f"\n--- COMPOSITE RANKING (return - drawdown + win_rate_bonus) ---")
    for r in (with_trades or valid):
        r["composite"] = (
            r["return_pct"]
            - r["max_dd_pct"]
            + max(0, (r["win_rate"] - 50)) * 0.5
        )
    ranked = sorted((with_trades or valid), key=lambda x: x["composite"], reverse=True)
    for i, r in enumerate(ranked[:5], 1):
        isi_tag = " [ISI]" if r.get("isi_enabled") else ""
        print(f"  #{i} {r['label']:<40} score={r['composite']:+.2f} "
              f"(ret={r['return_pct']:+.2f}% dd={r['max_dd_pct']:.2f}% "
              f"wr={r['win_rate']:.1f}%){isi_tag}")


def print_isi_comparison(results):
    """Print ISI vs noISI comparison for matching configs."""
    isi_results = [r for r in results if r.get("isi_enabled") and "error" not in r]
    no_isi_results = [r for r in results if not r.get("isi_enabled") and "error" not in r]

    if not isi_results or not no_isi_results:
        return

    print("\n" + "=" * 80)
    print("ISI IMPACT ANALYSIS")
    print("=" * 80)

    for isi_r in isi_results:
        base_label = isi_r["label"].replace(" ISI", "")
        match = next((r for r in no_isi_results if r["label"] == base_label), None)
        if not match:
            continue

        trade_diff = isi_r["trades"] - match["trades"]
        wr_diff = isi_r["win_rate"] - match["win_rate"]
        ret_diff = isi_r["return_pct"] - match["return_pct"]

        print(f"\n  {base_label}:")
        print(f"    noISI: {match['trades']} trades, WR={match['win_rate']:.1f}%, "
              f"Ret={match['return_pct']:+.2f}%")
        print(f"    ISI:   {isi_r['trades']} trades, WR={isi_r['win_rate']:.1f}%, "
              f"Ret={isi_r['return_pct']:+.2f}%")
        print(f"    Delta: {trade_diff:+d} trades, WR={wr_diff:+.1f}%, "
              f"Ret={ret_diff:+.2f}%")

        if isi_r.get("isi_phases"):
            phases = ", ".join(f"{k}:{v}" for k, v in isi_r["isi_phases"].items())
            print(f"    Phases: {phases}")
        if isi_r["trades"] > 0:
            print(f"    Avg Seq modifier: {isi_r['avg_seq_modifier']:+.1f}, "
                  f"Avg Div modifier: {isi_r['avg_div_modifier']:+.1f}")


def print_skip_analysis(results):
    """Aggregate skip reasons across all configs."""
    valid = [r for r in results if "error" not in r]
    if not valid:
        return

    print("\n" + "=" * 80)
    print("SKIP REASON ANALYSIS (aggregated)")
    print("=" * 80)

    all_skips = {}
    for r in valid:
        for reason, count in r.get("top_skips", []):
            all_skips[reason] = all_skips.get(reason, 0) + count

    sorted_skips = sorted(all_skips.items(), key=lambda x: -x[1])
    total = sum(v for _, v in sorted_skips)

    for reason, count in sorted_skips[:15]:
        pct = count / total * 100 if total > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"  {reason:<40} {count:>7} ({pct:>5.1f}%) {bar}")


def main():
    parser = argparse.ArgumentParser(description="Run SMC backtest suite.")
    parser.add_argument("--workers", type=int, default=6, help="Process workers for suite (default: 6)")
    args = parser.parse_args()
    max_workers = max(1, int(args.workers))

    print("=" * 80)
    print("SMC BACKTEST SUITE - R:R VALIDATION (extended period)")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # --- Configuration ---
    instruments = ["EUR_USD", "GBP_USD"]
    cross_asset_instruments = ["XAU_USD"]
    start_date = datetime(2025, 8, 1)   # Extended back for more data
    end_date = datetime(2026, 2, 7)
    initial_capital = 50000

    # Optimize limit entry: max_bars, midpoint entry, breakeven off
    # Format: (label_suffix, confidence, rr, regime_on, session_on, session_hours,
    #          isi_seq, isi_xa, isi_cal, partial_tp, limit_entry, breakeven_sl,
    #          limit_max_bars, limit_midpoint)
    config_grid = [
        # Baseline: old market entry
        ("OLD Market",    70, 2.0, True,  True,  [(7, 17)], False, False, False, False, False, False, 6, False),
        # Limit 6 bars (current best for GBP)
        ("Lim6",          70, 2.0, True,  True,  [(7, 17)], False, False, False, False, True,  False, 6, False),
        # Limit 12 bars (1 hour to fill)
        ("Lim12",         70, 2.0, True,  True,  [(7, 17)], False, False, False, False, True,  False, 12, False),
        # Limit 18 bars (1.5 hours)
        ("Lim18",         70, 2.0, True,  True,  [(7, 17)], False, False, False, False, True,  False, 18, False),
        # Limit 6 bars + midpoint entry (deeper in zone)
        ("Lim6 Mid",      70, 2.0, True,  True,  [(7, 17)], False, False, False, False, True,  False, 6, True),
        # Limit 12 bars + midpoint entry
        ("Lim12 Mid",     70, 2.0, True,  True,  [(7, 17)], False, False, False, False, True,  False, 12, True),
        # Best limit + no regime (more trades)
        ("Lim12 NoReg",   70, 2.0, False, True,  [(7, 17)], False, False, False, False, True,  False, 12, False),
        # Best limit + lower confidence
        ("Lim12 Conf60",  60, 2.0, True,  True,  [(7, 17)], False, False, False, False, True,  False, 12, False),
    ]

    total_configs = len(instruments) * len(config_grid)
    print(f"\nPeriod: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Instruments: {instruments}")
    print(f"Cross-asset ref: {cross_asset_instruments}")
    print(f"Initial Capital: {initial_capital:,.0f} EUR")
    print(f"Total Configurations: {total_configs}")
    print(f"Signal interval: 6 (every 30 min)")
    print(f"Max workers: {max_workers}")

    # --- Load Data (main process only, MT5 singleton) ---
    print("\n--- LOADING DATA ---")
    from src.backtesting.data_loader import DataLoader
    loader = DataLoader()
    data = {}

    for inst in instruments + cross_asset_instruments:
        print(f"\n{inst}:")
        try:
            print(f"  Loading H4...", end=" ", flush=True)
            h4 = loader.load_simple(inst, "H4", start_date, end_date)
            print(f"{h4.total_bars} bars")

            print(f"  Loading H1...", end=" ", flush=True)
            h1 = loader.load_simple(inst, "H1", start_date, end_date)
            print(f"{h1.total_bars} bars")

            print(f"  Loading M5...", end=" ", flush=True)
            m5 = loader.load_simple(inst, "M5", start_date, end_date)
            print(f"{m5.total_bars} bars")

            data[inst] = (h4.candles, h1.candles, m5.candles)
        except Exception as e:
            print(f"  ERROR: {e}")

    if not any(inst in data for inst in instruments):
        print("\nNo trading instrument data loaded! Exiting.")
        return

    # Build cross-asset M5 data dict
    all_m5_data = {}
    for inst in data:
        all_m5_data[inst] = data[inst][2]  # m5 candles

    # --- Build job list ---
    jobs = []
    for inst in instruments:
        if inst not in data:
            continue

        h4_candles, h1_candles, m5_candles = data[inst]
        inst_short = inst.replace("_USD", "").replace("_", "")

        # Cross-asset data for this instrument (exclude self)
        cross_asset_for_inst = {k: v for k, v in all_m5_data.items() if k != inst}

        spread = 1.2 if "EUR" in inst else 1.8

        for (name, conf, rr, regime_on, sess_on, sess_hours,
             isi_seq, isi_xa, isi_cal, partial_tp,
             limit_entry, breakeven_sl,
             limit_max_bars, limit_midpoint) in config_grid:

            label = f"{inst_short} {name}"

            config_dict = {
                "instrument": inst,
                "timeframe": "M5",
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": initial_capital,
                "min_confidence": conf,
                "min_grade": "B",
                "target_rr": rr,
                "max_sl_pips": 15.0,
                "max_positions": 1,
                "spread_pips": spread,
                "slippage_pips": 0.2,
                "commission_per_lot": 7.0,
                "risk_percent": 0.003,
                "check_regime": regime_on,
                "check_session": sess_on,
                "session_hours": sess_hours,
                "signal_interval": 6,  # Every 6th M5 bar = 30 min
                "htf_lookback": 100,
                "ltf_lookback": 100,
                "partial_tp_enabled": partial_tp,
                "trailing_stop_enabled": partial_tp,
                "limit_entry_enabled": limit_entry,
                "limit_entry_max_bars": limit_max_bars,
                "limit_entry_midpoint": limit_midpoint,
                "breakeven_sl_enabled": breakeven_sl,
                "isi_sequence_tracker": isi_seq,
                "isi_cross_asset": isi_xa,
                "isi_calibrator": isi_cal,
            }

            xa_data = cross_asset_for_inst if isi_xa else None

            jobs.append((
                label, inst,
                h4_candles, h1_candles, m5_candles,
                config_dict, xa_data,
            ))

    # --- Run Backtests (multiprocessing) ---
    print(f"\n--- RUNNING {len(jobs)} BACKTESTS ({max_workers} workers) ---")
    suite_start = time.time()
    results = []
    used_sequential_fallback = False
    try:
        if max_workers == 1:
            raise PermissionError("Sequential mode requested (workers=1).")
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_label = {}
            for job in jobs:
                future = executor.submit(run_single_backtest, job)
                future_to_label[future] = job[0]  # label

            for future in as_completed(future_to_label):
                label = future_to_label[future]
                try:
                    summary = future.result()
                    results.append(summary)
                    if "error" in summary:
                        print(f"  {label}: ERROR - {summary['error']}")
                    else:
                        print(
                            f"  {label}: {summary['trades']} trades, "
                            f"WR={summary['win_rate']:.0f}%, "
                            f"Ret={summary['return_pct']:+.2f}%, "
                            f"{summary['run_time']:.0f}s"
                        )
                except Exception as e:
                    print(f"  {label}: WORKER ERROR - {e}")
                    results.append({"label": label, "error": str(e)})
    except PermissionError:
        used_sequential_fallback = True
        print("  ProcessPool unavailable -> running sequential fallback...")
        for job in jobs:
            label = job[0]
            try:
                summary = run_single_backtest(job)
                results.append(summary)
                if "error" in summary:
                    print(f"  {label}: ERROR - {summary['error']}")
                else:
                    print(
                        f"  {label}: {summary['trades']} trades, "
                        f"WR={summary['win_rate']:.0f}%, "
                        f"Ret={summary['return_pct']:+.2f}%, "
                        f"{summary['run_time']:.0f}s"
                    )
            except Exception as e:
                print(f"  {label}: WORKER ERROR - {e}")
                results.append({"label": label, "error": str(e)})

    suite_elapsed = time.time() - suite_start
    print(f"\nAll backtests completed in {suite_elapsed:.1f}s")
    if used_sequential_fallback:
        print("Mode: sequential fallback")

    # Sort results by instrument then label for consistent output
    results.sort(key=lambda x: x.get("label", ""))

    # --- Results ---
    print_summary_table(results)
    print_best_configs(results)
    print_isi_comparison(results)
    print_skip_analysis(results)

    # --- Save Results ---
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_results")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"suite_{timestamp}.json")

    serializable = []
    for r in results:
        sr = {}
        for k, v in r.items():
            if isinstance(v, float) and (v != v):  # NaN check
                sr[k] = None
            else:
                sr[k] = v
        serializable.append(sr)

    with open(output_file, "w") as f:
        json.dump({
            "run_date": datetime.now().isoformat(),
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "initial_capital": initial_capital,
            "total_configs": total_configs,
            "total_time_seconds": suite_elapsed,
            "isi_options": ["noISI", "Seq+XA+Cal"],
            "results": serializable,
        }, f, indent=2, default=str)

    print(f"\nResults saved to: {output_file}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
