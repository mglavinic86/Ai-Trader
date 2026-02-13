"""Performance page - concise outcomes and instrument breakdown."""

from __future__ import annotations

import streamlit as st
import pandas as pd

from src.utils.database import db
from app_pages.shared import fast_sync_with_mt5


def render() -> None:
    fast_sync_with_mt5()
    st.title("Performance")

    perf = db.get_performance_stats(days=30)
    dd = db.get_drawdown_stats(days=30)
    auto_stats = db.get_auto_trading_stats(days=30)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Trades", perf.get("total_trades", 0))
    c2.metric("Win Rate", f"{perf.get('win_rate', 0):.1f}%")
    c3.metric("Profit Factor", f"{perf.get('profit_factor', 0):.2f}")
    c4.metric("Net PnL (30d)", f"{dd.get('net_pnl', 0):+.2f}")
    c5.metric("Max DD (30d)", f"{dd.get('max_drawdown_pct', 0):.2f}%")

    st.subheader("Auto Trading (30d)")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Auto Trades", auto_stats.get("total_auto_trades", 0))
    a2.metric("Auto PnL", f"{auto_stats.get('auto_pnl', 0):+.2f}")
    a3.metric("Signals", auto_stats.get("total_signals", 0))
    a4.metric("Execution Rate", f"{auto_stats.get('execution_rate', 0):.1f}%")

    st.subheader("By Instrument (Auto, 30d)")
    by_inst = db.get_auto_trades_by_instrument(days=30)
    if by_inst:
        rows = []
        for inst, data in by_inst.items():
            rows.append(
                {"instrument": inst, "trades": data.get("count", 0), "pnl": data.get("pnl", 0.0)}
            )
        df_inst = pd.DataFrame(rows).sort_values("trades", ascending=False)
        st.dataframe(df_inst, use_container_width=True, hide_index=True)
    else:
        st.info("No auto-trade instrument stats yet.")

    st.subheader("Recent Closed Trades")
    trades = db.get_recent_trades(days=30)
    if trades:
        df = pd.DataFrame(trades)
        keep_cols = [c for c in [
            "closed_at", "instrument", "direction", "pnl", "pnl_percent", "close_reason", "trade_source"
        ] if c in df.columns]
        st.dataframe(df[keep_cols].sort_values("closed_at", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No closed trades in selected window.")
