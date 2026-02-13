"""Runtime Audit page - SMC v2 evaluation telemetry."""

from __future__ import annotations

import streamlit as st
import pandas as pd

from src.utils.database import db
from app_pages.shared import fast_sync_with_mt5


def _extract_eval_fields(item: dict) -> dict:
    details = item.get("details") if isinstance(item.get("details"), dict) else {}
    eval_details = details.get("eval_details", {}) if isinstance(details, dict) else {}
    gates = details.get("gates", {}) if isinstance(details, dict) else {}
    raw_details = details.get("raw_details", {}) if isinstance(details, dict) else {}
    raw_gates = raw_details.get("gates", {}) if isinstance(raw_details, dict) else {}
    gate_map = gates if isinstance(gates, dict) and gates else (raw_gates if isinstance(raw_gates, dict) else {})
    return {
        "timestamp": item.get("timestamp"),
        "instrument": item.get("instrument"),
        "setup_grade": item.get("setup_grade"),
        "confidence": item.get("confidence"),
        "risk_reward": item.get("risk_reward"),
        "allow_trade": bool(item.get("allow_trade")) if item.get("allow_trade") is not None else None,
        "within_killzone": item.get("within_killzone") if item.get("within_killzone") is not None else gate_map.get("within_killzone"),
        "htf_poi_gate": item.get("htf_poi_gate") if item.get("htf_poi_gate") is not None else gate_map.get("htf_poi_gate"),
        "sweep_valid": item.get("sweep_valid") if item.get("sweep_valid") is not None else gate_map.get("sweep_valid"),
        "choch_or_bos": item.get("choch_or_bos") if item.get("choch_or_bos") is not None else gate_map.get("choch_or_bos"),
        "rr_pass": item.get("rr_pass") if item.get("rr_pass") is not None else gate_map.get("rr_pass"),
        "sl_cap_pass": item.get("sl_cap_pass") if item.get("sl_cap_pass") is not None else gate_map.get("sl_cap_pass"),
        "htf_range_position": eval_details.get("htf_range_position"),
        "strict_fvg_count": eval_details.get("strict_fvg_count"),
        "min_rr_required": eval_details.get("min_rr_required"),
        "block_reason_primary": item.get("reason"),
        "gate_map": gate_map,
    }


def render() -> None:
    fast_sync_with_mt5()
    st.title("Runtime Audit")
    st.caption("Structured runtime validation view based on setup labels and gate telemetry.")

    labels = db.get_recent_setup_labels(limit=500)
    rows = [_extract_eval_fields(x) for x in labels]
    if not rows:
        st.info("No SMC v2 setup labels yet.")
        return

    df = pd.DataFrame(rows)
    instruments = ["ALL"] + sorted([i for i in df["instrument"].dropna().unique().tolist()])
    selected_instrument = st.selectbox("Instrument", instruments, index=0)
    only_blocked = st.checkbox("Only blocked", value=False)

    filtered = df.copy()
    if selected_instrument != "ALL":
        filtered = filtered[filtered["instrument"] == selected_instrument]
    if only_blocked:
        filtered = filtered[filtered["allow_trade"] == False]  # noqa: E712

    # Normalize display values for clearer audit readability.
    gate_cols = ["within_killzone", "htf_poi_gate", "sweep_valid", "choch_or_bos", "rr_pass", "sl_cap_pass", "allow_trade"]
    numeric_cols = ["confidence", "risk_reward", "min_rr_required", "htf_range_position", "strict_fvg_count"]

    for col in gate_cols:
        if col in filtered.columns:
            filtered[col] = filtered[col].apply(
                lambda v: 1 if v is True or v == 1 else (0 if v is False or v == 0 or v is None else v)
            )

    for col in numeric_cols:
        if col in filtered.columns:
            filtered[col] = filtered[col].apply(lambda v: "N/A" if v is None else v)

    col1, col2, col3 = st.columns(3)
    col1.metric("Rows", len(filtered))
    col2.metric("Allowed", int((filtered["allow_trade"] == True).sum()))  # noqa: E712
    col3.metric("Blocked", int((filtered["allow_trade"] == False).sum()))  # noqa: E712

    display_cols = [
        "timestamp",
        "instrument",
        "setup_grade",
        "confidence",
        "risk_reward",
        "min_rr_required",
        "within_killzone",
        "htf_poi_gate",
        "htf_range_position",
        "sweep_valid",
        "choch_or_bos",
        "rr_pass",
        "sl_cap_pass",
        "allow_trade",
        "block_reason_primary",
    ]
    st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)

    st.subheader("Block Reasons Frequency")
    reason_df = (
        filtered[filtered["allow_trade"] == False]  # noqa: E712
        .groupby("block_reason_primary")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    if not reason_df.empty:
        st.bar_chart(reason_df.set_index("block_reason_primary"))
    else:
        st.info("No blocked rows in current filter.")

    st.subheader("Gate Failure Counts")
    gate_fail_cols = ["within_killzone", "htf_poi_gate", "sweep_valid", "choch_or_bos", "rr_pass", "sl_cap_pass"]
    fail_rows = []
    for g in gate_fail_cols:
        fail_rows.append({"gate": g, "fail_count": int((filtered[g] == 0).sum())})
    fail_df = pd.DataFrame(fail_rows).sort_values("fail_count", ascending=False)
    st.dataframe(fail_df, hide_index=True, use_container_width=True)
