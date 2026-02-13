"""Shared helpers for redesigned dashboard pages."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import streamlit as st

from src.core.auto_config import load_auto_config, save_auto_config
from src.utils.database import db
from src.trading.mt5_client import MT5Client
from src.utils.config import config as app_config


DEV_DIR = Path(__file__).parent.parent
SETTINGS_PATH = DEV_DIR / "settings" / "config.json"
ENV_PATH = DEV_DIR / ".env"
SNAPSHOT_DIR = DEV_DIR / "settings" / "snapshots"


def ensure_session_state() -> None:
    if "mt5_client" not in st.session_state:
        st.session_state.mt5_client = None
    if "connected" not in st.session_state:
        st.session_state.connected = False


def get_mt5_client() -> MT5Client | None:
    ensure_session_state()
    if st.session_state.mt5_client is None:
        try:
            client = MT5Client()
            if client.is_connected():
                st.session_state.mt5_client = client
                st.session_state.connected = True
        except Exception:
            st.session_state.mt5_client = None
            st.session_state.connected = False
    return st.session_state.mt5_client


def get_account_summary() -> dict[str, Any]:
    client = get_mt5_client()
    if not client:
        return {"connected": False}
    try:
        acc = client.get_account()
        return {
            "connected": True,
            "id": acc.get("id"),
            "currency": acc.get("currency", ""),
            "balance": acc.get("balance", 0.0),
            "equity": acc.get("nav", 0.0),
            "unrealized_pl": acc.get("unrealized_pl", 0.0),
            "open_positions": acc.get("open_position_count", 0),
            "mode": "DEMO" if app_config.is_demo() else "LIVE",
        }
    except Exception:
        return {"connected": False}


def get_service_status() -> dict[str, Any]:
    """Infer runtime status from recent activity timestamps."""
    now = datetime.now(timezone.utc)
    activities = db.get_recent_activities(limit=1)
    if not activities:
        return {"running": False, "last_activity": None, "state": "STOPPED"}
    ts = activities[0].get("timestamp")
    last_dt = None
    if ts:
        try:
            ts_clean = ts.replace("Z", "+00:00")
            last_dt = datetime.fromisoformat(ts_clean)
            if last_dt.tzinfo is None:
                # Activity log often stores naive local timestamps; treat them as local time.
                local_tz = datetime.now().astimezone().tzinfo or timezone.utc
                last_dt = last_dt.replace(tzinfo=local_tz).astimezone(timezone.utc)
            else:
                last_dt = last_dt.astimezone(timezone.utc)
        except Exception:
            last_dt = None
    running = False
    if last_dt:
        running = (now - last_dt) <= timedelta(minutes=2)
    return {
        "running": running,
        "last_activity": last_dt.isoformat() if last_dt else ts,
        "state": "RUNNING" if running else "STOPPED",
    }


def get_ops_snapshot() -> dict[str, Any]:
    fast_sync_with_mt5()

    auto_cfg = load_auto_config()
    day_stats = db.get_auto_trading_stats(days=1)
    perf = db.get_performance_stats(days=30)
    drawdown = db.get_drawdown_stats(days=30)
    # Ops dashboard tracks bot performance; scope PnL to AUTO_* trades only.
    daily_pnl = db.get_daily_pnl(auto_only=True)
    weekly_pnl = db.get_weekly_pnl(auto_only=True)
    service = get_service_status()
    account = get_account_summary()
    smc_shadow = db.get_smc_v2_shadow_stats(hours=24)
    gate_stats = db.get_smc_v2_gate_stats(hours=24)
    return {
        "auto_cfg": auto_cfg,
        "day_stats": day_stats,
        "perf": perf,
        "drawdown": drawdown,
        "daily_pnl": daily_pnl,
        "weekly_pnl": weekly_pnl,
        "service": service,
        "account": account,
        "smc_shadow": smc_shadow,
        "gate_stats": gate_stats,
    }


def fast_sync_with_mt5() -> None:
    """Best-effort dashboard-side sync so displayed metrics track MT5 state."""
    try:
        client = get_mt5_client()
        if client and client.is_connected():
            mt5_positions = client.get_positions()
            mt5_history = client.get_history(days=30)
            db.sync_trades_with_mt5(mt5_positions, mt5_history, mt5_client=client)
    except Exception:
        # Dashboard must remain resilient even if sync fails.
        pass


def run_manual_mt5_sync(days: int = 30) -> dict[str, Any]:
    """Run an explicit MT5 sync/reconcile cycle from dashboard action."""
    try:
        client = get_mt5_client()
        if not client or not client.is_connected():
            return {"ok": False, "error": "MT5 is not connected."}

        mt5_positions = client.get_positions()
        mt5_history = client.get_history(days=days)
        result = db.sync_trades_with_mt5(mt5_positions, mt5_history, mt5_client=client)
        return {
            "ok": True,
            "positions": len(mt5_positions or []),
            "history_rows": len(mt5_history or []),
            "result": result or {},
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_open_trades_snapshot() -> list[dict[str, Any]]:
    """
    Return current open trades/positions merged from DB and MT5 with sync status.
    """
    rows: list[dict[str, Any]] = []
    db_open = db.get_open_trades()
    db_map = {str(t.get("trade_id")): t for t in db_open if t.get("trade_id") is not None}

    mt5_positions = []
    client = get_mt5_client()
    if client and client.is_connected():
        try:
            mt5_positions = client.get_positions()
        except Exception:
            mt5_positions = []

    mt5_map = {str(p.get("ticket")): p for p in mt5_positions if p.get("ticket") is not None}
    all_ids = set(db_map.keys()) | set(mt5_map.keys())

    for trade_id in sorted(all_ids, reverse=True):
        d = db_map.get(trade_id)
        m = mt5_map.get(trade_id)
        if d and m:
            sync_status = "OPEN_SYNCED"
        elif d and not m:
            sync_status = "DB_OPEN_MT5_MISSING"
        else:
            sync_status = "MT5_OPEN_DB_MISSING"

        rows.append(
            {
                "trade_id": trade_id,
                "instrument": (d or {}).get("instrument") or (m or {}).get("instrument"),
                "direction": (d or {}).get("direction") or (m or {}).get("direction"),
                "opened_at": (d or {}).get("timestamp"),
                "entry_price": (d or {}).get("entry_price") or (m or {}).get("price_open"),
                "current_price": (m or {}).get("price_current"),
                "stop_loss": (d or {}).get("stop_loss") or (m or {}).get("sl"),
                "take_profit": (d or {}).get("take_profit") or (m or {}).get("tp"),
                "units": (d or {}).get("units"),
                "mt5_volume": (m or {}).get("volume"),
                "unrealized_pl": (m or {}).get("unrealized_pl"),
                "sync_status": sync_status,
            }
        )

    return rows


def load_main_config() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_main_config(cfg: dict[str, Any]) -> None:
    SETTINGS_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def upsert_env_var(key: str, value: str) -> None:
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    prefix = f"{key}="
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = f"{key}={value}"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    os.environ[key] = value


def snapshot_configs(label: str) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SNAPSHOT_DIR / f"{ts}_{label}.json"
    instrument_profiles_path = DEV_DIR / "settings" / "instrument_profiles.json"
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "auto_trading": json.loads((DEV_DIR / "settings" / "auto_trading.json").read_text(encoding="utf-8")),
        "settings_config": load_main_config(),
        "instrument_profiles": (
            json.loads(instrument_profiles_path.read_text(encoding="utf-8"))
            if instrument_profiles_path.exists()
            else {}
        ),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def update_auto_trading_experiment(xau_sl_cap_max: int, min_conf_a: int) -> None:
    cfg = load_auto_config()
    cfg.smc_v2.risk.xau_sl_caps["max_points"] = int(xau_sl_cap_max)
    cfg.smc_v2.grade_execution.min_confidence_a = int(min_conf_a)
    save_auto_config(cfg)


def _count_python_script_processes(script_name: str) -> int:
    """Return number of python processes containing the given script name in command line."""
    if os.name != "nt":
        return 0
    try:
        cmd = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*"
            + script_name
            + "*' } | Measure-Object | Select-Object -ExpandProperty Count"
        )
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", cmd],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return int(out) if out else 0
    except Exception:
        return 0


def restart_auto_trading_runtime(timeout_seconds: int = 25) -> dict[str, Any]:
    """
    Request graceful auto-trading restart and spawn a fresh runtime process.
    """
    stop_file = DEV_DIR / "data" / ".stop_service"
    stop_file.parent.mkdir(parents=True, exist_ok=True)
    stop_file.touch()

    start = time.time()
    while time.time() - start < timeout_seconds:
        if _count_python_script_processes("run_auto_trading.py") == 0:
            break
        time.sleep(1)

    # Open a visible terminal window so operator can watch live scan/log output.
    ps_cmd = (
        "$wd = '"
        + str(DEV_DIR).replace("'", "''")
        + "'; "
        "$py = '"
        + str(sys.executable).replace("'", "''")
        + "'; "
        "$args = '/k cd /d \"' + $wd + '\" && \"' + $py + '\" run_auto_trading.py'; "
        "Start-Process -FilePath 'cmd.exe' -ArgumentList $args -WorkingDirectory $wd -WindowStyle Normal"
    )
    subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_cmd], cwd=str(DEV_DIR))
    return {
        "ok": True,
        "waited_seconds": int(time.time() - start),
        "active_processes_after": _count_python_script_processes("run_auto_trading.py"),
    }


def restart_streamlit_runtime() -> dict[str, Any]:
    """
    Start a new Streamlit dashboard instance in background.
    Caller should terminate current process after this call.
    """
    vbs_path = DEV_DIR / "start_dashboard_hidden.vbs"
    bat_path = DEV_DIR / "start_dashboard.bat"
    if vbs_path.exists():
        subprocess.Popen(["wscript", str(vbs_path)], cwd=str(DEV_DIR))
        return {"ok": True, "launcher": str(vbs_path)}
    if bat_path.exists():
        subprocess.Popen(["cmd", "/c", "start", "", str(bat_path)], cwd=str(DEV_DIR))
        return {"ok": True, "launcher": str(bat_path)}
    return {"ok": False, "error": "No Streamlit launcher found."}
