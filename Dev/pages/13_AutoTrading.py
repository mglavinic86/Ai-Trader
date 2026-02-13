"""
Auto-Trading Control Panel.

Provides UI for controlling automated scalping trading.
"""

import streamlit as st
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import json
import csv
import io

# Page config
st.set_page_config(
    page_title="Auto Trading - AI Trader",
    page_icon="robot_face",
    layout="wide"
)

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.auto_config import load_auto_config, save_auto_config, AutoTradingConfig, HardLimits, LearningModeConfig
from src.trading.emergency import emergency_controller, is_emergency_stopped
from src.utils.database import db


def get_service_status():
    """Get auto-trading service status by checking recent activity."""
    from datetime import datetime, timedelta

    try:
        # Check activity_log for recent scans (more reliable than singleton)
        with db._connection() as conn:
            cursor = conn.cursor()

            # Get last scan time
            cursor.execute("""
                SELECT timestamp FROM activity_log
                WHERE activity_type IN ('SCAN_COMPLETE', 'SCAN_START', 'ANALYZING')
                ORDER BY id DESC LIMIT 1
            """)
            row = cursor.fetchone()

            if row:
                last_scan_str = row[0]
                try:
                    # Parse timestamp - handle both with and without timezone
                    last_scan_str_clean = last_scan_str.replace('Z', '+00:00')
                    if '+' not in last_scan_str_clean and last_scan_str_clean.count(':') <= 2:
                        # Naive timestamp - use local time comparison
                        last_scan = datetime.fromisoformat(last_scan_str_clean.split('.')[0])
                        age = (datetime.now() - last_scan).total_seconds()
                    else:
                        last_scan = datetime.fromisoformat(last_scan_str_clean)
                        age = (datetime.now(last_scan.tzinfo) - last_scan).total_seconds()
                    # If last scan was within 60 seconds, service is running
                    is_running = age < 60
                except Exception as e:
                    last_scan = None
                    is_running = False
            else:
                last_scan = None
                is_running = False

            # Get stats
            cursor.execute("""
                SELECT COUNT(*) FROM activity_log
                WHERE activity_type = 'SCAN_COMPLETE'
                AND date(timestamp) = date('now')
            """)
            scans_today = cursor.fetchone()[0]

        # Also try to get from service instance if available
        try:
            from src.services.auto_trading_service import get_auto_trading_service
            service = get_auto_trading_service()
            service_status = service.get_status()
            # Merge with activity-based status
            service_status["running"] = is_running or service_status.get("running", False)
            if last_scan and not service_status.get("last_scan"):
                service_status["last_scan"] = last_scan.isoformat() if hasattr(last_scan, 'isoformat') else str(last_scan)
            return service_status
        except:
            pass

        return {
            "running": is_running,
            "enabled": True,
            "state": "RUNNING" if is_running else "STOPPED",
            "last_scan": last_scan.isoformat() if last_scan and hasattr(last_scan, 'isoformat') else str(last_scan) if last_scan else None,
            "scans_today": scans_today
        }
    except Exception as e:
        return {
            "running": False,
            "enabled": False,
            "state": "ERROR",
            "error": str(e)
        }


def start_service_background():
    """Start auto-trading service in background thread."""
    import threading

    # Clear stop signal first
    clear_stop_signal()

    # Enable in config
    from src.core.auto_config import load_auto_config, save_auto_config
    config = load_auto_config()
    config.enabled = True
    save_auto_config(config)

    def run_service():
        import asyncio
        from src.services.auto_trading_service import AutoTradingService

        # Create NEW service instance (not singleton) to get fresh config
        service = AutoTradingService()

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(service.start())
        except Exception as e:
            print(f"Service error: {e}")
        finally:
            loop.close()

    # Start in daemon thread
    thread = threading.Thread(target=run_service, daemon=True)
    thread.start()
    return thread


def stop_service():
    """Stop auto-trading service using file-based signal."""
    try:
        # Create stop signal file
        stop_file = Path(__file__).parent.parent / "data" / ".stop_service"
        stop_file.touch()

        # Also try to disable in config
        from src.core.auto_config import load_auto_config, save_auto_config
        config = load_auto_config()
        config.enabled = False
        save_auto_config(config)

        return True
    except Exception as e:
        print(f"Stop error: {e}")
        return False


def clear_stop_signal():
    """Clear the stop signal file."""
    stop_file = Path(__file__).parent.parent / "data" / ".stop_service"
    if stop_file.exists():
        stop_file.unlink()


# =============================================================================
# DAEMON MODE CONTROLS (24/7 with auto-restart)
# =============================================================================

def get_daemon_status():
    """Get daemon/watchdog status from heartbeat file."""
    from src.services.heartbeat import HeartbeatManager
    return HeartbeatManager.get_status()


def start_daemon():
    """Start daemon mode (watchdog + auto-trading) as detached subprocess."""
    import subprocess
    import os
    import sys

    daemon_script = Path(__file__).parent.parent / "run_daemon.py"

    if not daemon_script.exists():
        return False, "run_daemon.py not found"

    try:
        # Start as detached subprocess (survives Streamlit restart)
        if os.name == 'nt':  # Windows
            # CREATE_NEW_PROCESS_GROUP + DETACHED_PROCESS
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            DETACHED_PROCESS = 0x00000008
            process = subprocess.Popen(
                [sys.executable, str(daemon_script)],
                cwd=str(daemon_script.parent),
                creationflags=CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
        else:  # Linux/Mac
            process = subprocess.Popen(
                [sys.executable, str(daemon_script)],
                cwd=str(daemon_script.parent),
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )

        return True, f"Daemon started (PID: {process.pid})"
    except Exception as e:
        return False, str(e)


def stop_daemon():
    """Stop daemon mode by creating stop signal file."""
    try:
        from src.services.watchdog import create_stop_signal
        create_stop_signal()
        return True, "Stop signal sent"
    except Exception as e:
        return False, str(e)


def render_daemon_control():
    """Render daemon mode controls (24/7 with auto-restart)."""
    st.markdown("---")
    st.subheader("24/7 Daemon Mode")
    st.caption("Runs with watchdog - auto-restarts on crash, survives browser close")

    daemon_status = get_daemon_status()
    is_alive = daemon_status.get("alive", False)

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if is_alive:
            st.success("DAEMON RUNNING")
        else:
            st.warning("DAEMON STOPPED")

    with col2:
        if not is_alive:
            if st.button("START DAEMON", type="primary", use_container_width=True,
                        help="Start 24/7 mode with auto-restart"):
                success, msg = start_daemon()
                if success:
                    st.success(msg)
                    import time
                    time.sleep(2)  # Wait for daemon to start
                    st.rerun()
                else:
                    st.error(f"Failed: {msg}")
        else:
            if st.button("STOP DAEMON", type="secondary", use_container_width=True,
                        help="Gracefully stop daemon"):
                success, msg = stop_daemon()
                if success:
                    st.info("Stopping daemon... (may take 10-30s)")
                    st.rerun()
                else:
                    st.error(f"Failed: {msg}")

    with col3:
        if is_alive:
            uptime = daemon_status.get("uptime_human", "unknown")
            state = daemon_status.get("state", "unknown")
            scans = daemon_status.get("scans_today", 0)
            trades = daemon_status.get("trades_today", 0)
            memory = daemon_status.get("memory_mb", 0)
            st.caption(f"State: {state} | Uptime: {uptime}")
            st.caption(f"Scans: {scans} | Trades: {trades} | Memory: {memory:.0f}MB")
        else:
            st.caption("Daemon not running. Start for 24/7 operation.")

    # Show watchdog log preview
    if is_alive:
        with st.expander("Watchdog Log (last 10 lines)"):
            log_file = Path(__file__).parent.parent / "data" / "watchdog.log"
            if log_file.exists():
                try:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()[-10:]
                    st.code("".join(lines), language="text")
                except:
                    st.caption("Could not read log file")
            else:
                st.caption("No log file yet")


def render_service_control():
    """Render service start/stop controls."""
    # Check if service thread exists in session state
    is_running = "service_thread" in st.session_state and st.session_state.service_thread is not None

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if is_running:
            st.success("SERVICE RUNNING")
        else:
            st.error("SERVICE STOPPED")

    with col2:
        if not is_running:
            if st.button("START SERVICE", type="primary", use_container_width=True):
                # Clear stop signal and start
                clear_stop_signal()
                thread = start_service_background()
                st.session_state.service_thread = thread
                st.success("Service started!")
                st.rerun()
        else:
            if st.button("STOP SERVICE", type="secondary", use_container_width=True):
                stop_service()
                st.session_state.service_thread = None
                st.info("Service stopping...")
                st.rerun()

    with col3:
        status = get_service_status()
        state = status.get("state", "UNKNOWN")
        last_scan = status.get("last_scan")
        if last_scan:
            st.caption(f"State: {state} | Last scan: {str(last_scan)[:19]}")
        else:
            st.caption(f"State: {state} | No scans yet")


def render_emergency_stop():
    """Render emergency stop button."""
    col1, col2 = st.columns([1, 4])

    with col1:
        if is_emergency_stopped():
            st.error("EMERGENCY STOP ACTIVE")
            if st.button("Reset Emergency", type="secondary", use_container_width=True):
                if emergency_controller.reset("CONFIRM_RESET"):
                    st.success("Emergency stop reset!")
                    st.rerun()
        else:
            if st.button("EMERGENCY STOP", type="primary", use_container_width=True,
                        help="Immediately stop all auto-trading and close all positions"):
                emergency_controller.stop("User triggered emergency stop", close_positions=True)
                st.error("Emergency stop activated!")
                st.rerun()


def render_main_toggle(config: AutoTradingConfig):
    """Render main ON/OFF toggle."""
    col1, col2, col3 = st.columns([2, 1, 2])

    with col2:
        # Status indicator
        if is_emergency_stopped():
            st.markdown("### Status: :red[EMERGENCY STOPPED]")
        elif config.enabled:
            if config.dry_run:
                st.markdown("### Status: :orange[DRY RUN]")
            else:
                st.markdown("### Status: :green[ACTIVE]")
        else:
            st.markdown("### Status: :gray[DISABLED]")

        # Learning mode indicator
        if config.learning_mode.is_in_learning():
            progress = config.learning_mode.get_progress_percent()
            st.caption(f":blue[LEARNING MODE] {config.learning_mode.current_trades}/{config.learning_mode.target_trades} ({progress:.0f}%)")
        else:
            st.caption(":gray[PRODUCTION MODE]")

        # AI Validation indicator
        if config.ai_validation.enabled:
            st.caption(":green[AI VALIDATION ON] - Claude validates each trade")
        else:
            st.caption(":orange[AI VALIDATION OFF]")

    with col1:
        st.markdown("### Auto Trading")
        enabled = st.toggle(
            "Enable Auto Trading",
            value=config.enabled,
            disabled=is_emergency_stopped(),
            help="Turn auto-trading on or off"
        )

        if enabled != config.enabled:
            config.enabled = enabled
            if save_auto_config(config):
                st.success("Auto trading " + ("enabled" if enabled else "disabled"))
                st.rerun()

    with col3:
        st.markdown("### Mode")
        dry_run = st.toggle(
            "Dry Run Mode",
            value=config.dry_run,
            help="In dry run mode, signals are logged but no real trades are executed"
        )

        if dry_run != config.dry_run:
            config.dry_run = dry_run
            if save_auto_config(config):
                st.info("Dry run mode " + ("enabled" if dry_run else "disabled - REAL TRADES WILL BE EXECUTED"))
                st.rerun()


def render_learning_mode_panel(config: AutoTradingConfig):
    """Render Learning Mode status and controls panel."""
    learning = config.learning_mode

    # Header with toggle
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Learning Mode")
    with col2:
        mode_label = "LEARNING" if learning.is_in_learning() else "PRODUCTION"
        if learning.is_in_learning():
            st.success(f"**{mode_label}**")
        else:
            st.info(f"**{mode_label}**")

    # Progress bar
    progress = learning.get_progress_percent()
    st.progress(progress / 100, text=f"Progress: {learning.current_trades}/{learning.target_trades} trades ({progress:.0f}%)")

    # Current vs Production settings comparison
    col1, col2 = st.columns(2)

    active_settings = learning.get_active_settings()

    with col1:
        st.markdown("**Current Settings (Active):**")
        st.caption(f"Confidence Threshold: {active_settings.get('min_confidence_threshold', '-')}%")
        st.caption(f"Loss Streak Trigger: {active_settings.get('loss_streak_trigger', '-')}")
        st.caption(f"Cooldown: {active_settings.get('cooldown_minutes', '-')} min")
        st.caption(f"Max Trades/Day: {active_settings.get('max_daily_trades', '-')}")
        st.caption(f"Max Trades/Instrument: {active_settings.get('max_trades_per_instrument', '-')}")

    with col2:
        target_settings = learning.production_settings if learning.is_in_learning() else learning.aggressive_settings
        target_label = "Production (After Graduation)" if learning.is_in_learning() else "Learning (If Reset)"
        st.markdown(f"**{target_label}:**")
        st.caption(f"Confidence Threshold: {target_settings.get('min_confidence_threshold', '-')}%")
        st.caption(f"Loss Streak Trigger: {target_settings.get('loss_streak_trigger', '-')}")
        st.caption(f"Cooldown: {target_settings.get('cooldown_minutes', '-')} min")
        st.caption(f"Max Trades/Day: {target_settings.get('max_daily_trades', '-')}")
        st.caption(f"Max Trades/Instrument: {target_settings.get('max_trades_per_instrument', '-')}")

    # Control buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Reset Progress", help="Reset learning progress to 0"):
            config.learning_mode.current_trades = 0
            config.learning_mode.enabled = True
            if save_auto_config(config):
                st.success("Learning progress reset!")
                db.log_activity({
                    "activity_type": "LEARNING_RESET",
                    "reasoning": "User reset learning mode progress",
                    "details": {"target_trades": config.learning_mode.target_trades}
                })
                st.rerun()

    with col2:
        if learning.is_in_learning():
            if st.button("Graduate Now", help="Skip to production settings"):
                config.learning_mode.enabled = False
                if save_auto_config(config):
                    st.success("Graduated to production settings!")
                    db.log_activity({
                        "activity_type": "LEARNING_GRADUATED",
                        "reasoning": "User manually graduated to production",
                        "details": {"trades_at_graduation": config.learning_mode.current_trades}
                    })
                    st.rerun()
        else:
            if st.button("Return to Learning", help="Go back to aggressive settings"):
                config.learning_mode.enabled = True
                if save_auto_config(config):
                    st.info("Returned to learning mode")
                    st.rerun()

    with col3:
        new_target = st.number_input(
            "Target Trades",
            min_value=10,
            max_value=500,
            value=learning.target_trades,
            step=10,
            key="learning_target_trades"
        )
        if new_target != learning.target_trades:
            if st.button("Update Target"):
                config.learning_mode.target_trades = new_target
                if save_auto_config(config):
                    st.success(f"Target updated to {new_target} trades")
                    st.rerun()


def render_today_stats():
    """Render today's performance stats."""
    st.subheader("Today's Performance")

    stats = db.get_auto_trading_stats(days=1)
    daily_pnl = db.get_daily_pnl()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pnl_color = "green" if daily_pnl >= 0 else "red"
        st.metric(
            "Daily P/L",
            f"EUR {daily_pnl:+,.2f}",
            help="Total profit/loss today"
        )

    with col2:
        st.metric(
            "Trades Today",
            stats.get("total_auto_trades", 0),
            help="Number of auto trades executed today"
        )

    with col3:
        st.metric(
            "Signals Found",
            stats.get("total_signals", 0),
            help="Total signals detected today"
        )

    with col4:
        st.metric(
            "Execution Rate",
            f"{stats.get('execution_rate', 0):.1f}%",
            help="Percentage of signals that were executed"
        )


def render_configuration(config: AutoTradingConfig):
    """Render configuration section."""
    st.subheader("Configuration")

    # Warning about auto-refresh
    if st.session_state.get("auto_refresh_enabled", False):
        st.warning("Auto-refresh is ON. Turn it OFF before changing configuration to prevent losing changes.")

    with st.expander("Risk Settings", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            risk_percent = st.slider(
                "Risk per Trade (%)",
                min_value=0.5,
                max_value=float(HardLimits.MAX_RISK_PER_TRADE * 100),
                value=float(config.risk_per_trade_percent),
                step=0.5,
                help=f"Maximum {HardLimits.MAX_RISK_PER_TRADE * 100}% enforced",
                key="cfg_risk_percent"
            )

            min_confidence = st.slider(
                "Minimum Confidence (%)",
                min_value=int(HardLimits.MIN_CONFIDENCE),
                max_value=90,
                value=int(config.min_confidence_threshold),
                step=5,
                help=f"Minimum {HardLimits.MIN_CONFIDENCE}% required",
                key="cfg_min_confidence"
            )

        with col2:
            max_positions = st.slider(
                "Max Concurrent Positions",
                min_value=1,
                max_value=int(HardLimits.MAX_CONCURRENT_POSITIONS),
                value=int(config.max_concurrent_positions),
                help=f"Maximum {HardLimits.MAX_CONCURRENT_POSITIONS} enforced",
                key="cfg_max_positions"
            )

            max_trades_per_instrument = st.slider(
                "Max Trades per Instrument",
                min_value=1,
                max_value=5,
                value=int(config.max_trades_per_instrument),
                help="Maximum trades allowed for single instrument",
                key="cfg_max_trades_instrument"
            )

    with st.expander("Scanning Settings"):
        col1, col2 = st.columns(2)

        with col1:
            scan_interval = st.slider(
                "Scan Interval (seconds)",
                min_value=int(HardLimits.MIN_SCAN_INTERVAL),
                max_value=120,
                value=int(config.scan_interval_seconds),
                help="Time between market scans",
                key="cfg_scan_interval"
            )

            mode = st.selectbox(
                "Trading Mode",
                options=["scalping", "swing", "custom"],
                index=["scalping", "swing", "custom"].index(config.mode),
                help="Trading strategy mode",
                key="cfg_mode"
            )

        with col2:
            max_daily_trades = st.number_input(
                "Max Daily Trades (0 = unlimited)",
                min_value=0,
                max_value=100,
                value=config.max_daily_trades or 0,
                help="Leave 0 for unlimited trades",
                key="cfg_max_daily_trades"
            )

    with st.expander("Instruments"):
        # Use underscore format to match MT5Client expectations
        available_instruments = [
            "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD",
            "NZD_USD", "USD_CHF", "EUR_GBP", "EUR_JPY", "GBP_JPY", "BTC_USD"
        ]

        # Filter default to only include valid options
        valid_defaults = [i for i in config.instruments if i in available_instruments]

        selected_instruments = st.multiselect(
            "Select Instruments to Trade",
            options=available_instruments,
            default=valid_defaults,
            help="Choose which currency pairs to scan and trade",
            key="cfg_instruments"
        )

    with st.expander("Scalping Settings"):
        col1, col2 = st.columns(2)

        with col1:
            max_sl_pips = st.slider(
                "Max Stop Loss (pips)",
                min_value=5.0,
                max_value=30.0,
                value=float(config.scalping.max_sl_pips),
                step=1.0,
                key="cfg_max_sl_pips"
            )

            target_rr = st.slider(
                "Target Risk:Reward",
                min_value=1.0,
                max_value=3.0,
                value=float(config.scalping.target_rr),
                step=0.1,
                key="cfg_target_rr"
            )

        with col2:
            max_spread = st.slider(
                "Max Spread (pips)",
                min_value=0.5,
                max_value=5.0,
                value=float(config.scalping.max_spread_pips),
                step=0.5,
                key="cfg_max_spread"
            )

            min_atr = st.slider(
                "Min ATR (pips)",
                min_value=1.0,
                max_value=20.0,
                value=float(config.scalping.min_atr_pips),
                step=1.0,
                key="cfg_min_atr"
            )

    with st.expander("Cooldown Settings"):
        col1, col2 = st.columns(2)

        with col1:
            loss_streak_trigger = st.slider(
                "Loss Streak to Trigger Cooldown",
                min_value=2,
                max_value=10,
                value=int(config.cooldown.loss_streak_trigger),
                key="cfg_loss_streak"
            )

        with col2:
            cooldown_minutes = st.slider(
                "Cooldown Duration (minutes)",
                min_value=10,
                max_value=120,
                value=int(config.cooldown.cooldown_minutes),
                step=10,
                key="cfg_cooldown_min"
            )

    with st.expander("AI Validation (Claude)", expanded=True):
        st.markdown("**Claude AI validates each trade before execution**")

        col1, col2 = st.columns(2)

        with col1:
            ai_enabled = st.toggle(
                "Enable AI Validation",
                value=config.ai_validation.enabled,
                help="Claude will analyze and approve/reject each trade signal",
                key="cfg_ai_enabled"
            )

            ai_reject_on_failure = st.toggle(
                "Reject on API Failure",
                value=config.ai_validation.reject_on_failure,
                help="If AI call fails, reject the trade (safer)",
                key="cfg_ai_reject_fail"
            )

        with col2:
            ai_skip_learning = st.toggle(
                "Skip in Learning Mode",
                value=config.ai_validation.skip_in_learning_mode,
                help="Disable AI validation during learning phase (faster data collection)",
                key="cfg_ai_skip_learning"
            )

        # Show AI status
        try:
            from src.analysis.llm_engine import LLMEngine
            llm = LLMEngine()
            available, reason = llm.status()
            if available:
                st.success(f"AI Status: Available ({reason})")
            else:
                st.warning(f"AI Status: {reason}")
        except Exception as e:
            st.error(f"AI Status: Error - {e}")

    with st.expander("SMC v2 Rollout", expanded=True):
        st.caption("Shadow-first rollout controls for SMC v2 execution gates.")

        colr1, colr2, colr3 = st.columns(3)
        with colr1:
            if st.button("Preset: Shadow Only", use_container_width=True, key="smcv2_preset_shadow"):
                config.smc_v2.enabled = True
                config.smc_v2.shadow_mode = True
                config.smc_v2.grade_execution.enabled = False
                config.smc_v2.grade_execution.a_plus_only_live = False
                if save_auto_config(config):
                    st.success("Applied preset: Shadow Only")
                    st.rerun()
                st.error("Failed to apply preset")
        with colr2:
            if st.button("Preset: A+ Live", use_container_width=True, key="smcv2_preset_aplus"):
                config.smc_v2.enabled = True
                config.smc_v2.shadow_mode = True
                config.smc_v2.grade_execution.enabled = True
                config.smc_v2.grade_execution.a_plus_only_live = True
                config.smc_v2.grade_execution.min_confidence_a_plus = 45
                if save_auto_config(config):
                    st.success("Applied preset: A+ Live")
                    st.rerun()
                st.error("Failed to apply preset")
        with colr3:
            if st.button("Preset: A+ & A Live", use_container_width=True, key="smcv2_preset_aaplus"):
                config.smc_v2.enabled = True
                config.smc_v2.shadow_mode = True
                config.smc_v2.grade_execution.enabled = True
                config.smc_v2.grade_execution.a_plus_only_live = False
                config.smc_v2.grade_execution.min_confidence_a_plus = 45
                config.smc_v2.grade_execution.min_confidence_a = 60
                if save_auto_config(config):
                    st.success("Applied preset: A+ & A Live")
                    st.rerun()
                st.error("Failed to apply preset")

        col1, col2 = st.columns(2)
        with col1:
            smcv2_enabled = st.toggle(
                "Enable SMC v2",
                value=config.smc_v2.enabled,
                key="cfg_smcv2_enabled"
            )
            smcv2_shadow = st.toggle(
                "Shadow Mode",
                value=config.smc_v2.shadow_mode,
                key="cfg_smcv2_shadow"
            )
            smcv2_grade_exec = st.toggle(
                "Enable Grade Execution (Live Gate)",
                value=config.smc_v2.grade_execution.enabled,
                key="cfg_smcv2_grade_exec"
            )
            smcv2_aplus_only = st.toggle(
                "A+ Only Live",
                value=config.smc_v2.grade_execution.a_plus_only_live,
                key="cfg_smcv2_aplus_only"
            )

        with col2:
            smcv2_min_conf_aplus = st.slider(
                "Min Confidence A+",
                min_value=35,
                max_value=95,
                value=int(config.smc_v2.grade_execution.min_confidence_a_plus),
                key="cfg_smcv2_min_conf_aplus"
            )
            smcv2_min_conf_a = st.slider(
                "Min Confidence A",
                min_value=40,
                max_value=99,
                value=int(config.smc_v2.grade_execution.min_confidence_a),
                key="cfg_smcv2_min_conf_a"
            )
            smcv2_news_block_min = st.slider(
                "News Block Minutes",
                min_value=5,
                max_value=60,
                value=int(config.smc_v2.news_gate.block_minutes),
                key="cfg_smcv2_news_block_min"
            )

        colg1, colg2, colg3, colg4 = st.columns(4)
        with colg1:
            smcv2_strict_sweep = st.toggle(
                "Strict Sweep",
                value=config.smc_v2.strict_sweep.enabled,
                key="cfg_smcv2_strict_sweep"
            )
        with colg2:
            smcv2_strict_fvg = st.toggle(
                "Strict FVG",
                value=config.smc_v2.strict_fvg.enabled,
                key="cfg_smcv2_strict_fvg"
            )
        with colg3:
            smcv2_htf_poi = st.toggle(
                "HTF POI Gate",
                value=config.smc_v2.htf_poi_gate.enabled,
                key="cfg_smcv2_htf_poi"
            )
        with colg4:
            smcv2_killzone = st.toggle(
                "Killzone Gate",
                value=config.smc_v2.killzone_gate.enabled,
                key="cfg_smcv2_killzone"
            )
        smcv2_news_gate = st.toggle(
            "News Gate",
            value=config.smc_v2.news_gate.enabled,
            key="cfg_smcv2_news_gate"
        )

    # Save button
    if st.button("Save Configuration", type="primary", use_container_width=True):
        # Update config
        config.risk_per_trade_percent = risk_percent
        config.min_confidence_threshold = min_confidence
        config.max_concurrent_positions = max_positions
        config.max_trades_per_instrument = max_trades_per_instrument
        config.scan_interval_seconds = scan_interval
        config.mode = mode
        config.max_daily_trades = max_daily_trades if max_daily_trades > 0 else None
        config.instruments = selected_instruments

        config.scalping.max_sl_pips = max_sl_pips
        config.scalping.target_rr = target_rr
        config.scalping.max_spread_pips = max_spread
        config.scalping.min_atr_pips = min_atr

        config.cooldown.loss_streak_trigger = loss_streak_trigger
        config.cooldown.cooldown_minutes = cooldown_minutes

        config.ai_validation.enabled = ai_enabled
        config.ai_validation.reject_on_failure = ai_reject_on_failure
        config.ai_validation.skip_in_learning_mode = ai_skip_learning

        config.smc_v2.enabled = smcv2_enabled
        config.smc_v2.shadow_mode = smcv2_shadow
        config.smc_v2.grade_execution.enabled = smcv2_grade_exec
        config.smc_v2.grade_execution.a_plus_only_live = smcv2_aplus_only
        config.smc_v2.grade_execution.min_confidence_a_plus = smcv2_min_conf_aplus
        config.smc_v2.grade_execution.min_confidence_a = smcv2_min_conf_a
        config.smc_v2.strict_sweep.enabled = smcv2_strict_sweep
        config.smc_v2.strict_fvg.enabled = smcv2_strict_fvg
        config.smc_v2.htf_poi_gate.enabled = smcv2_htf_poi
        config.smc_v2.killzone_gate.enabled = smcv2_killzone
        config.smc_v2.news_gate.enabled = smcv2_news_gate
        config.smc_v2.news_gate.block_minutes = smcv2_news_block_min

        # Validate and save
        is_valid, errors = config.validate()
        if not is_valid:
            for error in errors:
                st.error(error)
        elif save_auto_config(config):
            st.success("Configuration saved!")
            st.rerun()
        else:
            st.error("Failed to save configuration")


def render_ai_thinking_panel():
    """Render AI Thinking panel showing what AI is currently doing."""
    st.subheader("AI Thinking - Live View")

    # Get recent activities
    activities = db.get_recent_activities(limit=15)

    if not activities:
        st.info("No AI activity yet. Enable auto-trading to see AI thinking in real-time.")
        return

    # Show latest status
    latest = activities[0] if activities else None
    if latest:
        activity_type = latest.get("activity_type", "")
        if activity_type == "SCAN_START":
            st.info("AI is starting a new market scan...")
        elif activity_type == "ANALYZING":
            inst = latest.get("instrument", "")
            st.info(f"AI is analyzing {inst}...")
        elif activity_type == "SCAN_COMPLETE":
            details = latest.get("details", {})
            signals = details.get("signals_found", 0) if isinstance(details, dict) else 0
            if signals > 0:
                st.success(f"Scan complete - Found {signals} trading opportunities!")
            else:
                st.caption("Scan complete - No opportunities found")

    # Activity feed with details
    st.markdown("---")
    st.markdown("**Recent AI Activity:**")

    for activity in activities:
        activity_type = activity.get("activity_type", "UNKNOWN")
        timestamp = activity.get("timestamp", "")[:19]
        instrument = activity.get("instrument") or ""
        direction = activity.get("direction") or ""
        confidence = activity.get("confidence")
        reasoning = activity.get("reasoning") or ""
        details = activity.get("details", {})

        # Format based on activity type
        if activity_type == "TRADE_EXECUTED":
            with st.container():
                st.success(f"**{timestamp}** - TRADE EXECUTED")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**{instrument}** {direction}")
                with col2:
                    st.write(f"Confidence: {confidence}%")
                with col3:
                    if isinstance(details, dict):
                        st.write(f"R:R: {details.get('risk_reward', 'N/A'):.2f}")
                st.caption(reasoning[:100])

        elif activity_type == "SIGNAL_GENERATED":
            with st.container():
                st.info(f"**{timestamp}** - SIGNAL GENERATED")
                col1, col2, col3 = st.columns(3)
                with col1:
                    dir_color = "green" if direction == "LONG" else "red"
                    st.markdown(f"**{instrument}** :{dir_color}[{direction}]")
                with col2:
                    st.write(f"Confidence: {confidence}%")
                with col3:
                    if isinstance(details, dict):
                        st.write(f"Entry: {details.get('entry_price', 'N/A')}")
                st.caption(reasoning[:100])

        elif activity_type == "SIGNAL_REJECTED":
            with st.expander(f"{timestamp} - {instrument} REJECTED", expanded=False):
                st.warning(reasoning)
                if isinstance(details, dict):
                    cols = st.columns(4)
                    with cols[0]:
                        st.caption(f"Trend: {details.get('trend', 'N/A')}")
                    with cols[1]:
                        st.caption(f"RSI: {details.get('rsi', 'N/A')}")
                    with cols[2]:
                        st.caption(f"Sent: {details.get('sentiment', 'N/A')}")
                    with cols[3]:
                        st.caption(f"Conf: {confidence or 'N/A'}%")

        elif activity_type == "TRADE_SKIPPED":
            with st.expander(f"{timestamp} - {instrument} {direction} SKIPPED", expanded=False):
                st.warning(reasoning)
                if isinstance(details, dict):
                    st.caption(f"Entry: {details.get('entry_price', 'N/A')} | "
                              f"SL: {details.get('stop_loss', 'N/A')} | "
                              f"TP: {details.get('take_profit', 'N/A')}")

        elif activity_type == "ANALYZING":
            with st.expander(f"{timestamp} - Analyzing {instrument}", expanded=False):
                if isinstance(details, dict):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.caption(f"Trend: {details.get('trend', 'N/A')}")
                    with col2:
                        st.caption(f"RSI: {details.get('rsi', 'N/A'):.1f}" if details.get('rsi') else "RSI: N/A")
                    with col3:
                        st.caption(f"Sent: {details.get('sentiment', 'N/A'):.2f}" if details.get('sentiment') else "Sent: N/A")
                    with col4:
                        st.caption(f"Conf: {confidence or 'N/A'}%")
                st.caption(reasoning[:80] if reasoning else "")

        elif activity_type == "COOLDOWN_START":
            st.error(f"**{timestamp}** - COOLDOWN STARTED: {reasoning}")

        elif activity_type == "COOLDOWN_END":
            st.success(f"**{timestamp}** - COOLDOWN ENDED: Trading resumed")

        elif activity_type == "SCAN_COMPLETE":
            details_dict = details if isinstance(details, dict) else {}
            signals = details_dict.get("signals_found", 0)
            scanned = details_dict.get("instruments_scanned", 0)
            st.caption(f"{timestamp} - Scan complete: {scanned} instruments, {signals} signals")

        elif activity_type == "AI_APPROVED":
            with st.container():
                st.success(f"**{timestamp}** - AI APPROVED")
                col1, col2, col3 = st.columns(3)
                with col1:
                    dir_color = "green" if direction == "LONG" else "red"
                    st.markdown(f"**{instrument}** :{dir_color}[{direction}]")
                with col2:
                    st.write(f"Confidence: {confidence}%")
                with col3:
                    if isinstance(details, dict):
                        st.write(f"Latency: {details.get('ai_latency_ms', 0)}ms")
                st.caption(f"AI: {reasoning[:150]}")

        elif activity_type == "AI_REJECTED":
            with st.container():
                st.error(f"**{timestamp}** - AI REJECTED")
                col1, col2, col3 = st.columns(3)
                with col1:
                    dir_color = "green" if direction == "LONG" else "red"
                    st.markdown(f"**{instrument}** :{dir_color}[{direction}]")
                with col2:
                    st.write(f"Confidence: {confidence}%")
                with col3:
                    if isinstance(details, dict):
                        st.write(f"Model: {details.get('ai_model', 'N/A')[:20]}")
                st.caption(f"AI: {reasoning[:150]}")

        elif activity_type == "ERROR":
            st.error(f"**{timestamp}** - ERROR: {reasoning[:80]}")


def render_decision_trail():
    """Render decision trail - detailed breakdown of each analysis."""
    st.subheader("Decision Trail")
    st.caption("Detailed breakdown of AI analysis for each instrument")

    # Get analyzing activities
    activities = db.get_recent_activities(limit=50, activity_types=[
        "ANALYZING", "SIGNAL_GENERATED", "SIGNAL_REJECTED", "TRADE_EXECUTED", "TRADE_SKIPPED"
    ])

    if not activities:
        st.info("No analysis data yet.")
        return

    # Group by instrument
    by_instrument = {}
    for a in activities:
        inst = a.get("instrument")
        if inst:
            if inst not in by_instrument:
                by_instrument[inst] = []
            by_instrument[inst].append(a)

    # Show each instrument
    for instrument, acts in by_instrument.items():
        with st.expander(f"{instrument} - {len(acts)} recent analyses"):
            for a in acts[:5]:  # Show last 5
                activity_type = a.get("activity_type")
                timestamp = a.get("timestamp", "")[:19]
                direction = a.get("direction") or "-"
                confidence = a.get("confidence") or "-"
                reasoning = a.get("reasoning") or ""
                details = a.get("details", {})

                # Status indicator
                if activity_type == "TRADE_EXECUTED":
                    status = ":green[EXECUTED]"
                elif activity_type == "SIGNAL_GENERATED":
                    status = ":blue[SIGNAL]"
                elif activity_type in ["SIGNAL_REJECTED", "TRADE_SKIPPED"]:
                    status = ":orange[SKIPPED]"
                else:
                    status = ":gray[ANALYSIS]"

                st.markdown(f"**{timestamp}** | {direction} | Conf: {confidence}% | {status}")

                if isinstance(details, dict):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.caption(f"Trend: {details.get('trend', '-')}")
                    with col2:
                        rsi = details.get('rsi')
                        st.caption(f"RSI: {rsi:.1f}" if rsi else "RSI: -")
                    with col3:
                        sent = details.get('sentiment')
                        st.caption(f"Sent: {sent:.2f}" if sent else "Sent: -")
                    with col4:
                        atr = details.get('atr_pips')
                        st.caption(f"ATR: {atr:.1f}" if atr else "ATR: -")

                    # Bull/Bear cases if available
                    if details.get('bull_case'):
                        st.caption(f"Bull: {details['bull_case'][:60]}...")
                    if details.get('bear_case'):
                        st.caption(f"Bear: {details['bear_case'][:60]}...")

                st.caption(f"Decision: {reasoning[:100]}")
                st.markdown("---")


def render_recent_signals():
    """Render recent signals log."""
    st.subheader("Recent Signals")

    signals = db.get_recent_auto_signals(limit=20)

    if not signals:
        st.info("No signals recorded yet. Enable auto-trading to start scanning.")
        return

    # Create a table
    for signal in signals:
        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 2, 3])

        with col1:
            st.write(signal.get("timestamp", "")[:19])

        with col2:
            direction = signal.get("direction", "")
            color = "green" if direction == "LONG" else "red"
            st.markdown(f"**{signal.get('instrument')}** :{color}[{direction}]")

        with col3:
            st.write(f"{signal.get('confidence', 0)}%")

        with col4:
            if signal.get("executed"):
                st.success("EXECUTED")
            else:
                st.warning("SKIPPED")

        with col5:
            if not signal.get("executed"):
                st.caption(signal.get("skip_reason", ""))


def render_smc_v2_shadow():
    """Render SMC v2 shadow evaluation stats and recent labels."""
    st.subheader("SMC v2 Shadow")

    shadow_stats = db.get_smc_v2_shadow_stats(hours=24)
    gate_stats = db.get_smc_v2_gate_stats(hours=24)
    by_instrument = db.get_smc_v2_by_instrument(hours=24)
    labels = db.get_recent_setup_labels(limit=20)
    export_labels = db.get_recent_setup_labels(limit=1000)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Evaluations (24h)", shadow_stats.get("total", 0))
    with col2:
        st.metric("Allow", shadow_stats.get("allow_count", 0))
    with col3:
        st.metric("Block", shadow_stats.get("block_count", 0))
    with col4:
        st.metric("Allow Rate", f"{shadow_stats.get('allow_rate', 0.0):.1f}%")

    by_grade = shadow_stats.get("by_grade", {})
    if by_grade:
        st.caption(
            "Grade distribution: " +
            ", ".join([f"{k}: {v}" for k, v in by_grade.items()])
        )

    top_block = shadow_stats.get("top_block_reasons", [])
    if top_block:
        st.markdown("**Top Block Reasons (24h)**")
        for item in top_block:
            st.caption(f"- {item.get('reason', 'N/A')} ({item.get('count', 0)})")

    st.markdown("---")
    st.markdown("**Gate Pass Rates (24h)**")
    gate_order = [
        "within_killzone",
        "news_clear",
        "htf_poi_gate",
        "sweep_valid",
        "fvg_valid",
        "direction_confirmed",
        "choch_or_bos",
        "rr_pass",
        "sl_cap_pass",
    ]
    gate_chunks = [gate_order[i:i+3] for i in range(0, len(gate_order), 3)]
    for chunk in gate_chunks:
        cols = st.columns(3)
        for idx, gate_name in enumerate(chunk):
            stat = gate_stats.get(gate_name, {})
            with cols[idx]:
                st.metric(
                    gate_name,
                    f"{stat.get('pass_rate', 0.0):.1f}%",
                    help=f"Pass {stat.get('pass_count', 0)} / {stat.get('total', 0)}"
                )

    st.markdown("---")
    st.markdown("**Instrument Breakdown (24h)**")
    if by_instrument:
        for row in by_instrument:
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
            with c1:
                st.caption(row.get("instrument"))
            with c2:
                st.caption(f"Eval: {row.get('total', 0)}")
            with c3:
                st.caption(f"Allow: {row.get('allow_count', 0)}")
            with c4:
                st.caption(f"Block: {row.get('block_count', 0)}")
            with c5:
                st.caption(f"Rate: {row.get('allow_rate', 0.0):.1f}%")
    else:
        st.caption("No instrument-level SMC v2 data in last 24h.")

    st.markdown("---")
    if export_labels:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "timestamp", "instrument", "direction", "setup_grade", "confidence",
            "risk_reward", "allow_trade", "reason", "within_killzone", "news_clear",
            "htf_poi_gate", "sweep_valid", "fvg_valid", "direction_confirmed",
            "choch_or_bos", "rr_pass", "sl_cap_pass", "details_json"
        ])
        for row in export_labels:
            details = row.get("details") if isinstance(row.get("details"), dict) else {}
            gates = details.get("gates", {}) if isinstance(details, dict) else {}
            writer.writerow([
                row.get("timestamp"),
                row.get("instrument"),
                row.get("direction"),
                row.get("setup_grade"),
                row.get("confidence"),
                row.get("risk_reward"),
                row.get("allow_trade"),
                row.get("reason"),
                row.get("within_killzone"),
                row.get("news_clear"),
                row.get("htf_poi_gate"),
                row.get("sweep_valid"),
                row.get("fvg_valid") if row.get("fvg_valid") is not None else gates.get("fvg_valid"),
                row.get("direction_confirmed"),
                row.get("choch_or_bos"),
                row.get("rr_pass"),
                row.get("sl_cap_pass"),
                json.dumps(details),
            ])
        st.download_button(
            label="Export Setup Labels CSV",
            data=output.getvalue(),
            file_name=f"setup_labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("---")
    st.markdown("**Recent Evaluations**")
    if not labels:
        st.info("No SMC v2 labels yet. Enable `smc_v2.enabled=true` + `shadow_mode=true` and run scanner.")
        return

    for row in labels:
        ts = str(row.get("timestamp", ""))[:19]
        instrument = row.get("instrument", "")
        direction = row.get("direction") or "-"
        grade = row.get("setup_grade") or "NO_TRADE"
        conf = row.get("confidence")
        rr = row.get("risk_reward")
        allow = bool(row.get("allow_trade"))
        reason = row.get("reason") or ""
        details = row.get("details") if isinstance(row.get("details"), dict) else {}
        gates = details.get("gates", {})
        gate_summary = ", ".join([
            f"{k}={'Y' if v is True else 'N' if v is False else '-'}"
            for k, v in gates.items()
        ]) if gates else ""

        c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 4])
        with c1:
            st.caption(ts)
        with c2:
            color = "green" if direction == "LONG" else "red" if direction == "SHORT" else "gray"
            st.markdown(f"**{instrument}** :{color}[{direction}]")
        with c3:
            st.caption(f"{grade} | {conf if conf is not None else '-'}%")
        with c4:
            st.success("ALLOW") if allow else st.warning("BLOCK")
        with c5:
            rr_text = f"RR={rr:.2f}" if isinstance(rr, (int, float)) else "RR=-"
            st.caption(f"{rr_text} | {reason}")
            if gate_summary:
                st.caption(gate_summary)


def render_hard_limits():
    """Render hard limits info."""
    st.subheader("Safety Limits")
    st.info("These are hard-coded safety limits that CANNOT be exceeded:")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Max Risk/Trade", f"{HardLimits.MAX_RISK_PER_TRADE * 100}%")
        st.metric("Max Daily Drawdown", f"{HardLimits.MAX_DAILY_DRAWDOWN * 100}%")

    with col2:
        st.metric("Max Weekly Drawdown", f"{HardLimits.MAX_WEEKLY_DRAWDOWN * 100}%")
        st.metric("Min Confidence", f"{HardLimits.MIN_CONFIDENCE}%")

    with col3:
        st.metric("Max Positions", HardLimits.MAX_CONCURRENT_POSITIONS)
        st.metric("Min Scan Interval", f"{HardLimits.MIN_SCAN_INTERVAL}s")


def main():
    st.title("Auto Trading Control Panel")

    # Auto-refresh option
    col_refresh, col_interval, _ = st.columns([1, 1, 3])
    with col_refresh:
        auto_refresh = st.checkbox("Auto-refresh", value=False, help="Automatically refresh every few seconds", key="auto_refresh_checkbox")
        st.session_state["auto_refresh_enabled"] = auto_refresh
    with col_interval:
        if auto_refresh:
            refresh_interval = st.selectbox("Interval", [5, 10, 30, 60], index=1, format_func=lambda x: f"{x}s")
            import time
            time.sleep(refresh_interval)
            st.rerun()

    # Load config
    config = load_auto_config()

    # Service control (START/STOP)
    render_service_control()

    # Daemon mode (24/7 with auto-restart)
    render_daemon_control()

    st.divider()

    # Emergency stop (always visible at top)
    render_emergency_stop()

    st.divider()

    # Main toggle
    render_main_toggle(config)

    st.divider()

    # Today's stats
    render_today_stats()

    st.divider()

    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Learning Mode",
        "AI Thinking",
        "Decision Trail",
        "Recent Signals",
        "SMC v2 Shadow",
        "Configuration",
        "Safety Limits"
    ])

    with tab1:
        render_learning_mode_panel(config)

    with tab2:
        render_ai_thinking_panel()

    with tab3:
        render_decision_trail()

    with tab4:
        render_recent_signals()

    with tab5:
        render_smc_v2_shadow()

    with tab6:
        render_configuration(config)

    with tab7:
        render_hard_limits()

    # Footer with service status
    st.divider()
    status = get_service_status()

    # Activity stats
    activity_stats = db.get_activity_stats(hours=24)
    scans = activity_stats.get("SCAN_COMPLETE", 0)
    signals = activity_stats.get("SIGNAL_GENERATED", 0)
    trades = activity_stats.get("TRADE_EXECUTED", 0)
    skipped = activity_stats.get("TRADE_SKIPPED", 0)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.caption(f"Scans (24h): {scans}")
    with col2:
        st.caption(f"Signals: {signals}")
    with col3:
        st.caption(f"Executed: {trades}")
    with col4:
        st.caption(f"Skipped: {skipped}")
    with col5:
        state = status.get('state', 'STOPPED')
        st.caption(f"State: {state}")


if __name__ == "__main__":
    main()
