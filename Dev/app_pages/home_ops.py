"""Home (Ops) page - operational command center."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st
import pandas as pd

from src.utils.database import db
from src.core.auto_config import load_auto_config, save_auto_config
from app_pages.shared import (
    get_ops_snapshot,
    snapshot_configs,
    run_manual_mt5_sync,
    get_open_trades_snapshot,
    restart_auto_trading_runtime,
    restart_streamlit_runtime,
)


def _set_runtime_enabled(enabled: bool) -> None:
    cfg = load_auto_config()
    cfg.enabled = enabled
    save_auto_config(cfg)
    stop_file = Path(__file__).parent.parent / "data" / ".stop_service"
    if enabled:
        if stop_file.exists():
            stop_file.unlink()
    else:
        stop_file.touch()


def render() -> None:
    st.title("Home (Ops)")
    snap = get_ops_snapshot()
    auto_cfg = snap["auto_cfg"]
    account = snap["account"]
    service = snap["service"]
    day_stats = snap["day_stats"]
    gate_stats = snap["gate_stats"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Service", service["state"])
    c2.metric("Mode", account.get("mode", "N/A"))
    c3.metric("Trades Today", day_stats.get("total_auto_trades", 0))
    c4.metric("Signals Today", day_stats.get("total_signals", 0))

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("Run", use_container_width=True, type="primary"):
            snapshot_configs("before_run")
            _set_runtime_enabled(True)
            st.success("Auto-trading enabled.")
    with c2:
        if st.button("Pause", use_container_width=True):
            snapshot_configs("before_pause")
            _set_runtime_enabled(False)
            st.warning("Auto-trading paused.")
    with c3:
        st.caption(
            f"Config enabled={auto_cfg.enabled} | "
            f"Last activity={service.get('last_activity') or 'N/A'}"
        )

    st.subheader("Runtime Controls")
    rc1, rc2 = st.columns(2)
    with rc1:
        if st.button("Restart Auto Trading", use_container_width=True):
            snapshot_configs("before_restart_auto_trading")
            restart_res = restart_auto_trading_runtime()
            if restart_res.get("ok"):
                db.log_activity(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "activity_type": "RUNTIME_RESTART",
                        "decision": "AUTO_TRADING_RESTART",
                        "reasoning": "Restart requested from Home (Ops).",
                        "details": restart_res,
                    }
                )
                st.success(
                    "Auto-trading restart requested. "
                    f"Waited {restart_res.get('waited_seconds', 0)}s, "
                    f"processes now: {restart_res.get('active_processes_after', 'N/A')}"
                )
            else:
                st.error(f"Auto-trading restart failed: {restart_res.get('error', 'unknown error')}")
    with rc2:
        if st.button("Restart Streamlit", use_container_width=True):
            snapshot_configs("before_restart_streamlit")
            result = restart_streamlit_runtime()
            if result.get("ok"):
                db.log_activity(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "activity_type": "RUNTIME_RESTART",
                        "decision": "STREAMLIT_RESTART",
                        "reasoning": "Restart requested from Home (Ops).",
                        "details": result,
                    }
                )
                st.warning("New dashboard instance started. This tab will close connection in 2 seconds.")
                time.sleep(2)
                os._exit(0)
            st.error(f"Streamlit restart failed: {result.get('error', 'unknown error')}")

    st.divider()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Daily PnL", f"{snap['daily_pnl']:+.2f}")
    k2.metric("Weekly PnL", f"{snap['weekly_pnl']:+.2f}")
    k3.metric("Win Rate (All)", f"{snap['perf'].get('win_rate', 0):.1f}%")
    k4.metric("30d Max DD", f"{snap['drawdown'].get('max_drawdown_pct', 0):.2f}%")

    pending_recon = db.get_pending_recon_count(days=7)
    if pending_recon > 0:
        st.warning(f"Pending MT5 Recon (7d): {pending_recon} closed trade(s) awaiting MT5 PnL confirmation.")
    c_sync1, c_sync2 = st.columns([1, 3])
    with c_sync1:
        if st.button("Force MT5 Sync", use_container_width=True):
            sync_res = run_manual_mt5_sync(days=30)
            if sync_res.get("ok"):
                r = sync_res.get("result", {})
                st.success(
                    "MT5 sync done | "
                    f"history={sync_res.get('history_rows', 0)}, "
                    f"pending_reconciled={r.get('pending_reconciled', 0)}, "
                    f"closed_with_pnl={r.get('closed_with_pnl', 0)}"
                )
                st.rerun()
            else:
                st.error(f"MT5 sync failed: {sync_res.get('error', 'unknown error')}")

    st.subheader("Last 10 Closed Trades")
    recent_closed = db.get_recent_trades(days=30)
    if recent_closed:
        closed_df = pd.DataFrame(recent_closed)
        closed_df = closed_df.sort_values("closed_at", ascending=False).head(10)
        if "pnl" in closed_df.columns:
            closed_df["pnl"] = closed_df["pnl"].apply(
                lambda v: "PENDING_RECON" if pd.isna(v) else float(v)
            )
        if "pnl_percent" in closed_df.columns:
            closed_df["pnl_percent"] = closed_df["pnl_percent"].apply(
                lambda v: "PENDING_RECON" if pd.isna(v) else float(v)
            )
        keep_cols = [
            "closed_at",
            "trade_id",
            "instrument",
            "direction",
            "pnl",
            "pnl_percent",
            "close_reason",
            "trade_source",
        ]
        keep_cols = [c for c in keep_cols if c in closed_df.columns]
        st.dataframe(closed_df[keep_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No closed trades yet.")

    st.subheader("Open Trades (Live)")
    open_rows = get_open_trades_snapshot()
    if open_rows:
        open_df = pd.DataFrame(open_rows)
        keep_cols = [
            "trade_id",
            "instrument",
            "direction",
            "opened_at",
            "entry_price",
            "current_price",
            "stop_loss",
            "take_profit",
            "units",
            "mt5_volume",
            "unrealized_pl",
            "sync_status",
        ]
        keep_cols = [c for c in keep_cols if c in open_df.columns]
        st.dataframe(open_df[keep_cols], use_container_width=True, hide_index=True)
    else:
        st.caption("No open trades/positions.")

    st.subheader("Gate Health (24h)")
    gate_view = []
    for key in ["within_killzone", "htf_poi_gate", "rr_pass", "sl_cap_pass", "choch_or_bos"]:
        g = gate_stats.get(key, {})
        gate_view.append(
            {
                "gate": key,
                "pass_rate_pct": f"{float(g.get('pass_rate', 0.0)):.1f}%",
                "samples": int(g.get("total", 0) or 0),
                "pass_count": int(g.get("pass_count", 0) or 0),
                "fail_count": int(g.get("fail_count", 0) or 0),
            }
        )
    gate_df = pd.DataFrame(gate_view)
    st.dataframe(gate_df, use_container_width=True, hide_index=True)

    top_blocks = snap["smc_shadow"].get("top_block_reasons", [])
    st.subheader("Top Block Reasons (24h)")
    if top_blocks:
        st.dataframe(pd.DataFrame(top_blocks), use_container_width=True, hide_index=True)
    else:
        st.info("No block reasons yet.")

    st.subheader("Last Runtime Events")
    activities = db.get_recent_activities(limit=15)
    rows = []
    for a in activities:
        rows.append(
            {
                "timestamp": a.get("timestamp"),
                "type": a.get("activity_type"),
                "instrument": a.get("instrument"),
                "decision": a.get("decision"),
                "reason": a.get("reasoning"),
            }
        )
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No runtime activity found.")
