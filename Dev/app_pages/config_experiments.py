"""Config and Experiments page."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st
import pandas as pd

from src.core.auto_config import AutoTradingConfig, load_auto_config, save_auto_config
from src.utils.instrument_profiles import get_profile, set_instrument_sessions
from src.utils.database import db
from app_pages.shared import snapshot_configs, update_auto_trading_experiment

QUICK_TUNING_PRESETS = {
    "CONSERVATIVE": {
        "qt_a_plus_only": True,
        "qt_ai_validation": True,
        "qt_strict_sweep": True,
        "qt_strict_fvg": True,
        "qt_htf_poi_gate": True,
        "qt_killzone_gate": True,
        "qt_min_rr_a_plus": 2.8,
        "qt_min_rr_a": 2.4,
        "qt_min_rr_b": 2.2,
        "qt_max_daily_trades": 3,
        "qt_min_conf_a_plus": 60,
        "qt_min_conf_a": 65,
        "qt_max_per_instrument": 1,
    },
    "BALANCED": {
        "qt_a_plus_only": False,
        "qt_ai_validation": True,
        "qt_strict_sweep": True,
        "qt_strict_fvg": True,
        "qt_htf_poi_gate": True,
        "qt_killzone_gate": True,
        "qt_min_rr_a_plus": 2.5,
        "qt_min_rr_a": 2.0,
        "qt_min_rr_b": 2.0,
        "qt_max_daily_trades": 6,
        "qt_min_conf_a_plus": 45,
        "qt_min_conf_a": 55,
        "qt_max_per_instrument": 3,
    },
    "AGGRESSIVE": {
        "qt_a_plus_only": False,
        "qt_ai_validation": True,
        "qt_strict_sweep": False,
        "qt_strict_fvg": False,
        "qt_htf_poi_gate": False,
        "qt_killzone_gate": True,
        "qt_min_rr_a_plus": 2.0,
        "qt_min_rr_a": 1.6,
        "qt_min_rr_b": 1.4,
        "qt_max_daily_trades": 10,
        "qt_min_conf_a_plus": 40,
        "qt_min_conf_a": 50,
        "qt_max_per_instrument": 5,
    },
}

QUICK_TUNING_FIELD_LABELS = {
    "qt_a_plus_only": "A+ only live",
    "qt_ai_validation": "AI validation",
    "qt_strict_sweep": "Strict sweep",
    "qt_strict_fvg": "Strict FVG",
    "qt_htf_poi_gate": "HTF POI gate",
    "qt_killzone_gate": "Killzone gate",
    "qt_min_rr_a_plus": "Min RR A+",
    "qt_min_rr_a": "Min RR A",
    "qt_min_rr_b": "Min RR B",
    "qt_max_daily_trades": "Max daily trades",
    "qt_min_conf_a_plus": "Min conf A+",
    "qt_min_conf_a": "Min conf A",
    "qt_max_per_instrument": "Max trades / instrument",
}

QUICK_TUNING_CONTROL_GUIDE = [
    {"control": "A+ only live", "what_it_does": "Only A+ setups can execute live.", "impact": "Reduces frequency, usually higher selectivity."},
    {"control": "AI validation", "what_it_does": "Runs AI review before final execution.", "impact": "Adds extra filtering; slightly slower decisions."},
    {"control": "Strict sweep", "what_it_does": "Requires stronger sweep validation.", "impact": "Fewer but cleaner entries."},
    {"control": "Strict FVG", "what_it_does": "Requires stricter FVG quality.", "impact": "Reduces weak imbalance entries."},
    {"control": "HTF POI gate", "what_it_does": "Requires HTF location/POI alignment.", "impact": "Blocks many counter-location setups."},
    {"control": "Killzone gate", "what_it_does": "Restricts entries to allowed killzones.", "impact": "Avoids low-liquidity hours."},
    {"control": "Min RR A+/A/B", "what_it_does": "Minimum risk-reward by grade.", "impact": "Higher values = fewer but better geometry trades."},
    {"control": "Min conf A+/A", "what_it_does": "Minimum confidence score by grade.", "impact": "Higher values = stricter execution."},
    {"control": "Max daily trades", "what_it_does": "Global day cap.", "impact": "Controls overtrading and exposure."},
    {"control": "Max trades / instrument", "what_it_does": "Per-instrument daily cap.", "impact": "Prevents concentration in one pair."},
]


def _state_for_value(current, default) -> str:
    if isinstance(current, bool):
        return "ENABLED" if current else "DISABLED"
    if isinstance(current, (int, float)) and isinstance(default, (int, float)):
        if current == default:
            return "DEFAULT"
        if current < default:
            return "REDUCED"
        return "INCREASED"
    return "CUSTOM" if current != default else "DEFAULT"


def _fmt_value(value) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return "NONE"
    return str(value)


def _parse_session_window(raw: str) -> tuple[int, int] | None:
    try:
        start_text, end_text = str(raw).split("-")
        return int(start_text), int(end_text)
    except Exception:
        return None


def _format_session_window(start: int, end: int) -> str:
    return f"{int(start):02d}-{int(end):02d}"


def _set_quick_tuning_preset(preset: str) -> None:
    """Seed widget session-state keys for quick tuning presets."""
    for key, value in QUICK_TUNING_PRESETS[preset].items():
        st.session_state[key] = value


def _is_critical_tuning_change(payload: dict) -> bool:
    """Detect risky control combinations that require explicit confirmation."""
    return any(
        [
            not payload["ai_validation"],
            not payload["strict_sweep"],
            not payload["strict_fvg"],
            not payload["htf_poi_gate"],
            not payload["killzone_gate"],
            payload["min_rr_a_plus"] < 2.0,
            payload["min_rr_a"] < 1.8,
            payload["min_rr_b"] < 1.6,
            payload["min_conf_a_plus"] < 45,
            payload["min_conf_a"] < 55,
            payload["max_daily_trades"] > 8,
            payload["max_trades_per_instrument"] > 4,
        ]
    )


def _get_cfg_rows(cfg, base_cfg) -> list[dict]:
    # label, current, default, description
    items = [
        ("smc_v2.enabled", cfg.smc_v2.enabled, base_cfg.smc_v2.enabled, "Master switch for SMC v2 pipeline."),
        ("smc_v2.shadow_mode", cfg.smc_v2.shadow_mode, base_cfg.smc_v2.shadow_mode, "Logs/evaluates SMC v2 decisions for audit and tuning."),
        ("smc_v2.grade_execution.enabled", cfg.smc_v2.grade_execution.enabled, base_cfg.smc_v2.grade_execution.enabled, "Enforces grade-based live execution rules."),
        ("smc_v2.grade_execution.a_plus_only_live", cfg.smc_v2.grade_execution.a_plus_only_live, base_cfg.smc_v2.grade_execution.a_plus_only_live, "If true, only A+ setups are live-eligible."),
        ("smc_v2.grade_execution.enforce_live_hard_gates", cfg.smc_v2.grade_execution.enforce_live_hard_gates, base_cfg.smc_v2.grade_execution.enforce_live_hard_gates, "Forces hard gates (killzone/POI/etc.) in live decisions."),
        ("smc_v2.grade_execution.min_confidence_a_plus", cfg.smc_v2.grade_execution.min_confidence_a_plus, base_cfg.smc_v2.grade_execution.min_confidence_a_plus, "Minimum confidence required for A+ setups."),
        ("smc_v2.grade_execution.min_confidence_a", cfg.smc_v2.grade_execution.min_confidence_a, base_cfg.smc_v2.grade_execution.min_confidence_a, "Minimum confidence required for A setups."),
        ("smc_v2.strict_sweep.enabled", cfg.smc_v2.strict_sweep.enabled, base_cfg.smc_v2.strict_sweep.enabled, "Requires strict liquidity sweep validation."),
        ("smc_v2.strict_fvg.enabled", cfg.smc_v2.strict_fvg.enabled, base_cfg.smc_v2.strict_fvg.enabled, "Requires strict FVG validation."),
        ("smc_v2.htf_poi_gate.enabled", cfg.smc_v2.htf_poi_gate.enabled, base_cfg.smc_v2.htf_poi_gate.enabled, "Blocks trades outside HTF POI/range criteria."),
        ("smc_v2.killzone_gate.enabled", cfg.smc_v2.killzone_gate.enabled, base_cfg.smc_v2.killzone_gate.enabled, "Restricts entries to configured killzones."),
        ("smc_v2.killzone_gate.always_true", cfg.smc_v2.killzone_gate.always_true, base_cfg.smc_v2.killzone_gate.always_true, "Bypasses killzone blocking when set to true (demo relax)."),
        ("smc_v2.news_gate.enabled", cfg.smc_v2.news_gate.enabled, base_cfg.smc_v2.news_gate.enabled, "Blocks entries around high-impact news windows."),
        ("smc_v2.news_gate.block_minutes", cfg.smc_v2.news_gate.block_minutes, base_cfg.smc_v2.news_gate.block_minutes, "News gate window size in minutes."),
        ("smc_v2.risk.min_rr.A+", cfg.smc_v2.risk.min_rr.get("A+", 0), base_cfg.smc_v2.risk.min_rr.get("A+", 0), "Minimum RR for A+ setups."),
        ("smc_v2.risk.min_rr.A", cfg.smc_v2.risk.min_rr.get("A", 0), base_cfg.smc_v2.risk.min_rr.get("A", 0), "Minimum RR for A setups."),
        ("smc_v2.risk.min_rr.B", cfg.smc_v2.risk.min_rr.get("B", 0), base_cfg.smc_v2.risk.min_rr.get("B", 0), "Minimum RR for B setups."),
        ("smc_v2.risk.fx_sl_caps.min_pips", cfg.smc_v2.risk.fx_sl_caps.get("min_pips", 0), base_cfg.smc_v2.risk.fx_sl_caps.get("min_pips", 0), "Minimum FX SL distance in pips."),
        ("smc_v2.risk.fx_sl_caps.max_pips", cfg.smc_v2.risk.fx_sl_caps.get("max_pips", 0), base_cfg.smc_v2.risk.fx_sl_caps.get("max_pips", 0), "Maximum FX SL distance in pips."),
        ("smc_v2.risk.xau_sl_caps.min_points", cfg.smc_v2.risk.xau_sl_caps.get("min_points", 0), base_cfg.smc_v2.risk.xau_sl_caps.get("min_points", 0), "Minimum XAU SL distance in points."),
        ("smc_v2.risk.xau_sl_caps.max_points", cfg.smc_v2.risk.xau_sl_caps.get("max_points", 0), base_cfg.smc_v2.risk.xau_sl_caps.get("max_points", 0), "Maximum XAU SL distance in points."),
        ("limit_entry.enabled", cfg.limit_entry.enabled, base_cfg.limit_entry.enabled, "Enables limit-entry path (zone retrace entries)."),
        ("limit_entry.midpoint_entry", cfg.limit_entry.midpoint_entry, base_cfg.limit_entry.midpoint_entry, "Uses midpoint of entry zone instead of edge."),
        ("limit_entry.allow_market_fallback", cfg.limit_entry.allow_market_fallback, base_cfg.limit_entry.allow_market_fallback, "Allows market-order fallback if limit path is unavailable."),
        ("limit_entry.expiry_minutes", cfg.limit_entry.expiry_minutes, base_cfg.limit_entry.expiry_minutes, "Pending order expiry timeout."),
        ("limit_entry.max_pending_per_instrument", cfg.limit_entry.max_pending_per_instrument, base_cfg.limit_entry.max_pending_per_instrument, "Maximum simultaneous pending orders per instrument."),
        ("ai_validation.enabled", cfg.ai_validation.enabled, base_cfg.ai_validation.enabled, "Enables AI validation before execution."),
        ("ai_validation.skip_in_learning_mode", cfg.ai_validation.skip_in_learning_mode, base_cfg.ai_validation.skip_in_learning_mode, "Skips AI validation while in learning mode."),
        ("max_daily_trades", cfg.max_daily_trades, base_cfg.max_daily_trades, "Global max trades per day."),
        ("max_trades_per_instrument", cfg.max_trades_per_instrument, base_cfg.max_trades_per_instrument, "Max trades per instrument per day."),
        ("learning_mode.enabled", cfg.learning_mode.enabled, base_cfg.learning_mode.enabled, "Uses adaptive/aggressive settings while collecting data."),
        ("learning_mode.current_trades", cfg.learning_mode.current_trades, base_cfg.learning_mode.current_trades, "Current progress in learning cycle."),
        ("learning_mode.target_trades", cfg.learning_mode.target_trades, base_cfg.learning_mode.target_trades, "Target number of trades before graduation."),
        ("learning_mode.aggressive_settings.max_daily_trades", cfg.learning_mode.aggressive_settings.get("max_daily_trades"), base_cfg.learning_mode.aggressive_settings.get("max_daily_trades"), "Active daily cap when learning mode is ON."),
        ("learning_mode.aggressive_settings.max_trades_per_instrument", cfg.learning_mode.aggressive_settings.get("max_trades_per_instrument"), base_cfg.learning_mode.aggressive_settings.get("max_trades_per_instrument"), "Active per-instrument cap when learning mode is ON."),
        ("learning_mode.production_settings.max_daily_trades", cfg.learning_mode.production_settings.get("max_daily_trades"), base_cfg.learning_mode.production_settings.get("max_daily_trades"), "Daily cap after learning mode graduation."),
        ("learning_mode.production_settings.max_trades_per_instrument", cfg.learning_mode.production_settings.get("max_trades_per_instrument"), base_cfg.learning_mode.production_settings.get("max_trades_per_instrument"), "Per-instrument cap after learning mode graduation."),
    ]

    rows = []
    for label, cur, default, desc in items:
        rows.append(
            {
                "parameter": label,
                "value": _fmt_value(cur),
                "state": _state_for_value(cur, default),
                "default": _fmt_value(default),
                "description": desc,
            }
        )
    return rows


def render() -> None:
    st.title("Config & Experiments")
    cfg = load_auto_config()
    base_cfg = AutoTradingConfig()

    st.subheader("Active SMC v2 Runtime Config")
    c1, c2, c3 = st.columns(3)
    c1.metric("smc_v2.enabled", str(cfg.smc_v2.enabled).lower())
    c2.metric("grade_execution.enabled", str(cfg.smc_v2.grade_execution.enabled).lower())
    c3.metric("market_fallback", str(cfg.limit_entry.allow_market_fallback).lower())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("A+ min conf", cfg.smc_v2.grade_execution.min_confidence_a_plus)
    c2.metric("A min conf", cfg.smc_v2.grade_execution.min_confidence_a)
    c3.metric("XAU SL max (pts)", cfg.smc_v2.risk.xau_sl_caps.get("max_points", 0))
    c4.metric("A min RR", cfg.smc_v2.risk.min_rr.get("A", 0))

    st.divider()
    st.subheader("All Runtime Parameters (Enabled / Reduced / Disabled)")
    st.caption("Status is relative to system defaults. Each row includes what it does and how it affects execution.")
    param_rows = _get_cfg_rows(cfg, base_cfg)
    df_params = pd.DataFrame(param_rows)
    st.dataframe(df_params, width="stretch", hide_index=True)

    st.divider()
    st.subheader("Safe Demo Experiment Controls")
    st.caption("One change at a time. Snapshot is always saved before apply.")

    new_a_conf = st.slider(
        "A min confidence",
        min_value=50,
        max_value=70,
        value=int(cfg.smc_v2.grade_execution.min_confidence_a),
        step=1,
    )
    new_xau_sl = st.slider(
        "XAU SL cap max (points)",
        min_value=450,
        max_value=1000,
        value=int(cfg.smc_v2.risk.xau_sl_caps.get("max_points", 600)),
        step=10,
    )

    if st.button("Apply Experiment Settings", type="primary"):
        path = snapshot_configs("before_experiment_apply")
        update_auto_trading_experiment(new_xau_sl, new_a_conf)
        st.success(f"Applied. Snapshot saved: {path.name}")
        st.rerun()

    st.divider()
    st.subheader("Trading Time Windows (UTC)")
    st.caption("Set allowed trading windows per instrument with hour pickers.")

    instrument_sessions: dict[str, list[str]] = {}
    hour_options = list(range(0, 25))
    for instrument in cfg.instruments:
        profile = get_profile(instrument)
        current_sessions = profile.get("sessions", [])
        st.markdown(f"**{instrument}**")

        all_day_default = len(current_sessions) == 1 and str(current_sessions[0]).strip() in {"00-24", "0-24"}
        all_day_key = f"sessions_all_day_{instrument}"
        all_day = st.checkbox(
            "All day (00-24)",
            value=all_day_default,
            key=all_day_key,
            help="When enabled, trading is allowed the whole day (UTC).",
        )

        sessions_for_instrument: list[str] = []
        if all_day:
            sessions_for_instrument = ["00-24"]
        else:
            for idx in range(2):
                existing = _parse_session_window(current_sessions[idx]) if idx < len(current_sessions) else None
                enabled_default = existing is not None
                enabled_key = f"sessions_enabled_{instrument}_{idx}"
                enabled = st.checkbox(
                    f"Window {idx + 1}",
                    value=enabled_default,
                    key=enabled_key,
                )
                if enabled:
                    c1, c2 = st.columns(2)
                    default_start = existing[0] if existing else (7 if idx == 0 else 12)
                    default_end = existing[1] if existing else (17 if idx == 0 else 21)
                    with c1:
                        start_hour = st.selectbox(
                            f"{instrument} W{idx + 1} Start",
                            options=hour_options,
                            index=hour_options.index(default_start),
                            key=f"sessions_start_{instrument}_{idx}",
                        )
                    with c2:
                        end_hour = st.selectbox(
                            f"{instrument} W{idx + 1} End",
                            options=hour_options,
                            index=hour_options.index(default_end),
                            key=f"sessions_end_{instrument}_{idx}",
                        )
                    sessions_for_instrument.append(_format_session_window(start_hour, end_hour))

        instrument_sessions[instrument] = sessions_for_instrument
        st.caption(
            "Active: " + (", ".join(sessions_for_instrument) if sessions_for_instrument else "none")
        )
        st.divider()

    if st.button("Apply Trading Time Windows"):
        try:
            changed = []
            for instrument in cfg.instruments:
                normalized = set_instrument_sessions(instrument, instrument_sessions.get(instrument, []))
                changed.append((instrument, ", ".join(normalized) if normalized else "ALL DAY"))
            path = snapshot_configs("before_session_windows_apply")
            db.log_activity(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "activity_type": "TUNING_CHANGE",
                    "decision": "SESSION_WINDOWS_APPLY",
                    "reasoning": "Updated instrument trading session windows from dashboard.",
                    "details": {"snapshot": path.name, "changes": changed},
                }
            )
            st.success(f"Saved trading windows. Snapshot: {path.name}")
            for instrument, session_text in changed:
                st.caption(f"{instrument}: {session_text}")
        except ValueError as e:
            st.error(str(e))

    st.divider()
    st.subheader("Quick Tuning Console")
    st.caption("Fast controls for filters and rules used most during live tuning.")

    p1, p2, p3 = st.columns(3)
    with p1:
        if st.button("Preset: Conservative"):
            _set_quick_tuning_preset("CONSERVATIVE")
            st.rerun()
    with p2:
        if st.button("Preset: Balanced"):
            _set_quick_tuning_preset("BALANCED")
            st.rerun()
    with p3:
        if st.button("Preset: Aggressive"):
            _set_quick_tuning_preset("AGGRESSIVE")
            st.rerun()

    with st.expander("Control Guide (What each quick-tuning control does)", expanded=False):
        st.dataframe(pd.DataFrame(QUICK_TUNING_CONTROL_GUIDE), width="stretch", hide_index=True)

    with st.expander("Preset Matrix (All preset settings)", expanded=False):
        rows = []
        for preset_name, values in QUICK_TUNING_PRESETS.items():
            row = {"preset": preset_name.title()}
            for key, label in QUICK_TUNING_FIELD_LABELS.items():
                row[label] = values.get(key)
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    q1, q2, q3 = st.columns(3)
    with q1:
        q_a_plus_only = st.checkbox(
            "A+ only live",
            value=bool(st.session_state.get("qt_a_plus_only", cfg.smc_v2.grade_execution.a_plus_only_live)),
            key="qt_a_plus_only",
            help="If ON, only A+ setups can execute live.",
        )
        q_ai_validation = st.checkbox(
            "AI validation",
            value=bool(st.session_state.get("qt_ai_validation", cfg.ai_validation.enabled)),
            key="qt_ai_validation",
            help="Enable/disable AI validation layer before execution.",
        )
    with q2:
        q_strict_sweep = st.checkbox(
            "Strict sweep",
            value=bool(st.session_state.get("qt_strict_sweep", cfg.smc_v2.strict_sweep.enabled)),
            key="qt_strict_sweep",
        )
        q_strict_fvg = st.checkbox(
            "Strict FVG",
            value=bool(st.session_state.get("qt_strict_fvg", cfg.smc_v2.strict_fvg.enabled)),
            key="qt_strict_fvg",
        )
    with q3:
        q_htf_poi_gate = st.checkbox(
            "HTF POI gate",
            value=bool(st.session_state.get("qt_htf_poi_gate", cfg.smc_v2.htf_poi_gate.enabled)),
            key="qt_htf_poi_gate",
        )
        q_killzone_gate = st.checkbox(
            "Killzone gate",
            value=bool(st.session_state.get("qt_killzone_gate", cfg.smc_v2.killzone_gate.enabled)),
            key="qt_killzone_gate",
        )

    r1, r2, r3, r4 = st.columns(4)
    with r1:
        q_min_rr_a_plus = st.number_input(
            "Min RR A+",
            min_value=0.5,
            max_value=8.0,
            step=0.1,
            value=float(st.session_state.get("qt_min_rr_a_plus", cfg.smc_v2.risk.min_rr.get("A+", 2.5))),
            key="qt_min_rr_a_plus",
        )
    with r2:
        q_min_rr_a = st.number_input(
            "Min RR A",
            min_value=0.5,
            max_value=8.0,
            step=0.1,
            value=float(st.session_state.get("qt_min_rr_a", cfg.smc_v2.risk.min_rr.get("A", 2.0))),
            key="qt_min_rr_a",
        )
    with r3:
        q_min_rr_b = st.number_input(
            "Min RR B",
            min_value=0.5,
            max_value=8.0,
            step=0.1,
            value=float(st.session_state.get("qt_min_rr_b", cfg.smc_v2.risk.min_rr.get("B", 2.0))),
            key="qt_min_rr_b",
        )
    with r4:
        q_max_daily_trades = st.number_input(
            "Max daily trades",
            min_value=1,
            max_value=30,
            step=1,
            value=int(st.session_state.get("qt_max_daily_trades", cfg.max_daily_trades)),
            key="qt_max_daily_trades",
        )

    s1, s2, s3 = st.columns(3)
    with s1:
        q_min_conf_a_plus = st.number_input(
            "Min conf A+",
            min_value=0,
            max_value=100,
            step=1,
            value=int(st.session_state.get("qt_min_conf_a_plus", cfg.smc_v2.grade_execution.min_confidence_a_plus)),
            key="qt_min_conf_a_plus",
        )
    with s2:
        q_min_conf_a = st.number_input(
            "Min conf A",
            min_value=0,
            max_value=100,
            step=1,
            value=int(st.session_state.get("qt_min_conf_a", cfg.smc_v2.grade_execution.min_confidence_a)),
            key="qt_min_conf_a",
        )
    with s3:
        q_max_per_instrument = st.number_input(
            "Max trades / instrument",
            min_value=1,
            max_value=15,
            step=1,
            value=int(st.session_state.get("qt_max_per_instrument", cfg.max_trades_per_instrument)),
            key="qt_max_per_instrument",
        )

    tuning_payload = {
        "a_plus_only_live": bool(q_a_plus_only),
        "ai_validation": bool(q_ai_validation),
        "strict_sweep": bool(q_strict_sweep),
        "strict_fvg": bool(q_strict_fvg),
        "htf_poi_gate": bool(q_htf_poi_gate),
        "killzone_gate": bool(q_killzone_gate),
        "min_rr_a_plus": float(q_min_rr_a_plus),
        "min_rr_a": float(q_min_rr_a),
        "min_rr_b": float(q_min_rr_b),
        "max_daily_trades": int(q_max_daily_trades),
        "min_conf_a_plus": int(q_min_conf_a_plus),
        "min_conf_a": int(q_min_conf_a),
        "max_trades_per_instrument": int(q_max_per_instrument),
    }
    critical = _is_critical_tuning_change(tuning_payload)
    if critical:
        st.warning("Critical/risky combination detected. Explicit confirmation is required.")
    critical_confirm = st.checkbox(
        "I confirm applying critical tuning changes",
        value=False,
        key="qt_critical_confirm",
        disabled=not critical,
    )

    if st.button("Apply Quick Tuning", type="primary"):
        if critical and not critical_confirm:
            st.error("Critical tuning confirmation required.")
            return
        snap = snapshot_configs("before_quick_tuning_apply")
        cfg = load_auto_config()
        cfg.smc_v2.grade_execution.a_plus_only_live = bool(q_a_plus_only)
        cfg.ai_validation.enabled = bool(q_ai_validation)
        cfg.smc_v2.strict_sweep.enabled = bool(q_strict_sweep)
        cfg.smc_v2.strict_fvg.enabled = bool(q_strict_fvg)
        cfg.smc_v2.htf_poi_gate.enabled = bool(q_htf_poi_gate)
        cfg.smc_v2.killzone_gate.enabled = bool(q_killzone_gate)
        cfg.smc_v2.risk.min_rr["A+"] = float(q_min_rr_a_plus)
        cfg.smc_v2.risk.min_rr["A"] = float(q_min_rr_a)
        cfg.smc_v2.risk.min_rr["B"] = float(q_min_rr_b)
        cfg.max_daily_trades = int(q_max_daily_trades)
        cfg.smc_v2.grade_execution.min_confidence_a_plus = int(q_min_conf_a_plus)
        cfg.smc_v2.grade_execution.min_confidence_a = int(q_min_conf_a)
        cfg.max_trades_per_instrument = int(q_max_per_instrument)
        save_auto_config(cfg)
        db.log_activity(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "activity_type": "TUNING_CHANGE",
                "instrument": None,
                "direction": None,
                "decision": "QUICK_TUNING_APPLY",
                "reasoning": "Dashboard quick tuning applied.",
                "details": {
                    "critical": critical,
                    "snapshot": snap.name,
                    "payload": tuning_payload,
                },
            }
        )
        st.success(f"Quick tuning applied. Snapshot: {snap.name}")
        st.rerun()

    st.divider()
    st.subheader("Recent Tuning Changes")
    tune_logs = db.get_recent_activities(limit=30, activity_types=["TUNING_CHANGE", "RUNTIME_RESTART"])
    if tune_logs:
        rows = []
        for item in tune_logs:
            details = item.get("details")
            details_text = details if isinstance(details, str) else json.dumps(details)
            rows.append(
                {
                    "timestamp": item.get("timestamp"),
                    "type": item.get("activity_type"),
                    "action": item.get("decision"),
                    "reason": item.get("reasoning"),
                    "details": details_text,
                }
            )
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.caption("No tuning/restart changes logged yet.")

    st.divider()
    st.subheader("Config Snapshot History")
    snap_dir = Path(__file__).parent.parent / "settings" / "snapshots"
    if not snap_dir.exists():
        st.info("No snapshots yet.")
        return
    files = sorted([p for p in snap_dir.glob("*.json")], reverse=True)
    if not files:
        st.info("No snapshots yet.")
        return
    rows = []
    for p in files[:100]:
        rows.append({"file": p.name, "size_kb": round(p.stat().st_size / 1024, 1), "modified": p.stat().st_mtime})
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)
