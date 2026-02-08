"""
Walk-Forward Validation Runner

Runs walk-forward analysis for EUR_USD, GBP_USD, and XAU_USD.
Compares ISI vs noISI configurations with Monte Carlo simulation.

Usage:
    cd Dev
    python run_walk_forward.py
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_data_for_instrument(loader, instrument, start, end):
    """Load H4/H1/M5 data for an instrument."""
    print(f"  H4...", end=" ", flush=True)
    h4 = loader.load_simple(instrument, "H4", start, end)
    print(f"{h4.total_bars} bars")

    print(f"  H1...", end=" ", flush=True)
    h1 = loader.load_simple(instrument, "H1", start, end)
    print(f"{h1.total_bars} bars")

    print(f"  M5...", end=" ", flush=True)
    m5 = loader.load_simple(instrument, "M5", start, end)
    print(f"{m5.total_bars} bars")

    return h4.candles, h1.candles, m5.candles


def run_wf_for_instrument(
    instrument, h4, h1, m5, cross_asset_data, isi_enabled, wf_params
):
    """Run walk-forward for one instrument + ISI configuration."""
    from src.backtesting.walk_forward import WalkForwardValidator, WalkForwardConfig

    spread = 1.2
    if "GBP" in instrument:
        spread = 1.8
    if "XAU" in instrument:
        spread = 3.0

    wf_config = WalkForwardConfig(
        instrument=instrument,
        train_days=wf_params["train_days"],
        test_days=wf_params["test_days"],
        windows=wf_params["windows"],
        initial_capital=50000.0,
        min_confidence=70,
        min_grade="B",
        target_rr=2.0,
        max_sl_pips=15.0,
        spread_pips=spread,
        slippage_pips=0.2,
        commission_per_lot=7.0,
        risk_percent=0.003,
        check_regime=True,
        check_session=True,
        session_hours=[(7, 17)],
        signal_interval=6,
        isi_sequence_tracker=isi_enabled,
        isi_cross_asset=isi_enabled,
        isi_calibrator=isi_enabled,
        monte_carlo_iterations=1000,
        monte_carlo_seed=42,
    )

    xa = cross_asset_data if isi_enabled else None

    validator = WalkForwardValidator()
    return validator.run(wf_config, h4, h1, m5, xa)


def print_window_details(result):
    """Print per-window details."""
    for w in result.windows:
        print(
            f"  Window {w.window_id}: "
            f"Train({w.train_start.date()}-{w.train_end.date()}) "
            f"{w.train_trades}t WR={w.train_win_rate:.1f}% | "
            f"Test({w.test_start.date()}-{w.test_end.date()}) "
            f"{w.test_trades}t WR={w.test_win_rate:.1f}% | "
            f"Decay={w.win_rate_decay:+.1f}%"
        )


def main():
    print("=" * 80)
    print("WALK-FORWARD VALIDATION RUNNER")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Configuration
    instruments = ["EUR_USD", "GBP_USD", "XAU_USD"]
    cross_asset_ref = ["XAU_USD"]  # Additional cross-asset data

    # Walk-forward parameters
    wf_params = {
        "train_days": 45,
        "test_days": 15,
        "windows": 4,
    }

    # Date range (need extra buffer for walk-forward windows)
    total_wf_days = wf_params["windows"] * (wf_params["train_days"] + wf_params["test_days"])
    buffer_days = 20  # Extra for lookback
    end_date = datetime(2026, 2, 7)
    start_date = end_date - timedelta(days=total_wf_days + buffer_days)

    print(f"\nPeriod: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Windows: {wf_params['windows']} ({wf_params['train_days']}d train / {wf_params['test_days']}d test)")
    print(f"Instruments: {instruments}")
    print(f"Monte Carlo: 1000 iterations")

    # --- Load Data ---
    print("\n--- LOADING DATA ---")
    from src.backtesting.data_loader import DataLoader
    loader = DataLoader()
    data = {}

    all_instruments = list(set(instruments + cross_asset_ref))
    for inst in all_instruments:
        print(f"\n{inst}:")
        try:
            h4, h1, m5 = load_data_for_instrument(loader, inst, start_date, end_date)
            data[inst] = (h4, h1, m5)
        except Exception as e:
            print(f"  ERROR: {e}")

    # Build cross-asset M5 data
    all_m5 = {}
    for inst in data:
        all_m5[inst] = data[inst][2]  # m5 candles

    # --- Run Walk-Forward ---
    print("\n--- RUNNING WALK-FORWARD VALIDATION ---")
    all_results = {}
    total_start = time.time()

    for inst in instruments:
        if inst not in data:
            print(f"\nSkipping {inst} - no data loaded")
            continue

        h4, h1, m5 = data[inst]
        cross_asset_for_inst = {k: v for k, v in all_m5.items() if k != inst}

        # Run without ISI
        print(f"\n{'='*60}")
        print(f"{inst} - noISI")
        print(f"{'='*60}")
        t0 = time.time()
        try:
            result_no_isi = run_wf_for_instrument(
                inst, h4, h1, m5, cross_asset_for_inst, False, wf_params
            )
            elapsed = time.time() - t0
            print_window_details(result_no_isi)
            print(result_no_isi.format_summary())
            print(f"  Time: {elapsed:.1f}s")
            all_results[f"{inst}_noISI"] = result_no_isi
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

        # Run with ISI
        print(f"\n{'='*60}")
        print(f"{inst} - ISI (Seq+XA+Cal)")
        print(f"{'='*60}")
        t0 = time.time()
        try:
            result_isi = run_wf_for_instrument(
                inst, h4, h1, m5, cross_asset_for_inst, True, wf_params
            )
            elapsed = time.time() - t0
            print_window_details(result_isi)
            print(result_isi.format_summary())
            print(f"  Time: {elapsed:.1f}s")
            all_results[f"{inst}_ISI"] = result_isi
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    total_elapsed = time.time() - total_start

    # --- Comparison Summary ---
    print("\n" + "=" * 80)
    print("WALK-FORWARD COMPARISON: ISI vs noISI")
    print("=" * 80)

    hdr = (
        f"{'Config':<25} {'OOS WR':>8} {'OOS P/L':>10} {'OOS Sharpe':>10} "
        f"{'Consist':>8} {'Robust':>8} {'P(Profit)':>10}"
    )
    print(hdr)
    print("-" * 80)

    for key, result in sorted(all_results.items()):
        mc_prob = f"{result.monte_carlo.prob_profit:.0%}" if result.monte_carlo else "N/A"
        row = (
            f"{key:<25} "
            f"{result.avg_test_win_rate:>7.1f}% "
            f"{result.total_test_pnl:>+9.2f} "
            f"{result.avg_test_sharpe:>9.2f} "
            f"{result.consistency_score:>7.0f}% "
            f"{result.robustness_score:>7.0f} "
            f"{mc_prob:>10}"
        )
        print(row)

    print("-" * 80)
    print(f"\nTotal time: {total_elapsed:.1f}s")

    # --- Save Results ---
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_results")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"walk_forward_{timestamp}.json")

    save_data = {
        "run_date": datetime.now().isoformat(),
        "wf_params": wf_params,
        "total_time_seconds": total_elapsed,
        "results": {},
    }
    for key, result in all_results.items():
        save_data["results"][key] = result.to_dict()

    with open(output_file, "w") as f:
        json.dump(save_data, f, indent=2, default=str)

    print(f"\nResults saved to: {output_file}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
