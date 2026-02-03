"""
AI Trader - Dashboard Page

Account overview and daily performance.
"""

import streamlit as st
import sys
from pathlib import Path

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.utils.config import config
from src.utils.database import db
from src.trading.mt5_client import MT5Client, MT5Error
from src.analysis.llm_engine import LLMEngine
from components.tooltips import metric_with_tooltip, simple_explanation_section, ICONS, tooltip_text
from components.suggested_actions import is_forex_market_open, get_market_session
from components.status_bar import render_status_bar, get_status_bar_data
from components.notifications import check_notifications, render_notifications
from components.mt5_session import get_client, reset_connection
from src.core.auto_config import load_auto_config
from src.trading.emergency import is_emergency_stopped

st.set_page_config(page_title="Dashboard - AI Trader", page_icon="", layout="wide")


def render_auto_trading_status():
    """Render auto-trading status indicator with stats."""
    try:
        auto_config = load_auto_config()
        auto_stats = db.get_auto_trading_stats(days=1)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if is_emergency_stopped():
                st.error("EMERGENCY STOPPED")
            elif auto_config.enabled:
                if auto_config.dry_run:
                    st.warning("DRY RUN")
                else:
                    st.success("ACTIVE")
            else:
                st.info("DISABLED")

        with col2:
            st.metric("Signals Today", auto_stats.get("total_signals", 0))

        with col3:
            st.metric("Trades Today", auto_stats.get("total_auto_trades", 0))

        with col4:
            pnl = auto_stats.get("auto_pnl", 0)
            st.metric("Auto P/L", f"{pnl:+.2f}")

    except Exception:
        pass


def render_ai_activity_feed(limit: int = 10):
    """Render AI Activity Feed showing recent AI decisions."""
    st.subheader("AI Activity Feed")

    try:
        activities = db.get_recent_activities(limit=limit)

        if not activities:
            st.info("No AI activity yet. Start auto-trading to see activity.")
            return

        # Activity type icons and colors
        activity_styles = {
            "SCAN_START": ("", "gray"),
            "SCAN_COMPLETE": ("", "gray"),
            "ANALYZING": ("", "blue"),
            "SIGNAL_GENERATED": ("", "green"),
            "SIGNAL_REJECTED": ("", "orange"),
            "TRADE_EXECUTED": ("", "green"),
            "TRADE_SKIPPED": ("", "red"),
            "COOLDOWN_START": ("", "yellow"),
            "COOLDOWN_END": ("", "blue"),
            "ERROR": ("", "red"),
            "EMERGENCY_STOP": ("", "red"),
        }

        for activity in activities:
            activity_type = activity.get("activity_type", "UNKNOWN")
            icon, _ = activity_styles.get(activity_type, ("", "gray"))
            instrument = activity.get("instrument") or ""
            direction = activity.get("direction") or ""
            confidence = activity.get("confidence")
            reasoning = activity.get("reasoning") or ""
            timestamp = activity.get("timestamp", "")[:19]  # Trim to seconds

            # Format based on activity type
            if activity_type == "TRADE_EXECUTED":
                st.success(f"{icon} **{timestamp}** | {instrument} {direction} | Conf: {confidence}% | {reasoning[:80]}")
            elif activity_type == "SIGNAL_GENERATED":
                st.info(f"{icon} **{timestamp}** | {instrument} {direction} | Conf: {confidence}% | Signal ready")
            elif activity_type in ["SIGNAL_REJECTED", "TRADE_SKIPPED"]:
                st.warning(f"{icon} **{timestamp}** | {instrument} | {reasoning[:80]}")
            elif activity_type in ["ERROR", "EMERGENCY_STOP"]:
                st.error(f"{icon} **{timestamp}** | {instrument} | {reasoning[:80]}")
            elif activity_type == "ANALYZING":
                conf_str = f"Conf: {confidence}%" if confidence else ""
                st.caption(f"{icon} {timestamp} | Analyzing {instrument} {direction} | {conf_str}")
            elif activity_type == "SCAN_COMPLETE":
                details = activity.get("details", {})
                signals = details.get("signals_found", 0) if isinstance(details, dict) else 0
                st.caption(f"{icon} {timestamp} | Scan complete: {signals} signals found")
            elif activity_type in ["COOLDOWN_START", "COOLDOWN_END"]:
                st.warning(f"{icon} **{timestamp}** | {reasoning}")
            else:
                st.caption(f"{icon} {timestamp} | {activity_type} | {reasoning[:50]}")

    except Exception as e:
        st.warning(f"Could not load activity feed: {e}")


def main():
    st.title("Dashboard")

    client = get_client()
    col_reset, _ = st.columns([1, 5])
    with col_reset:
        if st.button("Reset Dashboard", use_container_width=True):
            reset_connection()
            for key in ["pending_command", "last_analysis", "last_llm_result", "last_llm_decision_id"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    llm_engine = LLMEngine()
    llm_available, llm_reason = llm_engine.status()
    st.caption(f"LLM Status: {'Enabled' if llm_available else 'Disabled'} - {llm_reason}")

    # Connection status
    if not st.session_state.connected:
        st.error("Not connected to MT5. Please ensure the terminal is running.")
        if st.button("Retry Connection"):
            st.session_state.mt5_client = None
            st.rerun()
        return

    try:
        account = client.get_account()
        daily_pnl = db.get_daily_pnl()
        stats = db.get_performance_stats()
        mode = "DEMO" if config.is_demo() else "LIVE"

        # Get positions for notifications
        try:
            positions = client.get_positions() if client else []
        except MT5Error as e:
            st.warning(f"Could not fetch positions: {e}")
            positions = []
        except Exception as e:
            positions = []

        # Check and render notifications at top
        notifications = check_notifications(
            account=account,
            positions=positions,
            config={
                "max_daily_drawdown": config.MAX_DAILY_DRAWDOWN,
                "max_positions": config.MAX_CONCURRENT_POSITIONS,
                "daily_pnl": daily_pnl
            }
        )
        render_notifications(notifications, max_display=3, key_suffix="_dashboard")

        # Market status header
        market_open = is_forex_market_open()
        session = get_market_session() if market_open else "Closed"
        market_status = f"{ICONS['success']} Market Open ({session})" if market_open else f"{ICONS['info']} Market Closed"
        st.caption(market_status)

        # Auto-trading status (enhanced)
        st.subheader("Auto-Trading Status")
        render_auto_trading_status()

        st.divider()

        # AI Activity Feed (real-time view of AI decisions)
        render_ai_activity_feed(limit=8)

        st.divider()

        # Profit-focused KPI row (last 30d)
        st.subheader("Profit Focus (30d)")
        dd_stats = db.get_drawdown_stats(days=30)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Net P/L (30d)", f"{account['currency']} {dd_stats['net_pnl']:+,.2f}")
        with col2:
            st.metric("Max Drawdown (30d)", f"{dd_stats['max_drawdown_pct']:.2f}%")
        with col3:
            st.metric("Win Rate", f"{stats['win_rate']:.1f}%")

        st.divider()

        # Two columns layout (today + actions)
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.subheader("Today")
            st.markdown(
                f"- **Session:** {session}\n"
                f"- **Positions:** {account['open_position_count']}/{config.MAX_CONCURRENT_POSITIONS}\n"
                f"- **Unrealized P/L:** {account['currency']} {account['unrealized_pl']:+,.2f}\n"
                f"- **Daily P/L:** {account['currency']} {daily_pnl:+,.2f}\n"
            )

            with st.expander("Account Details"):
                account_data = {
                    "Property": [
                        "Account ID",
                        "Balance",
                        "Equity",
                        "Unrealized P/L",
                        "Margin Used",
                        "Margin Available",
                        "Open Positions",
                        "Account Mode"
                    ],
                    "Value": [
                        account['id'],
                        f"{account['currency']} {account['balance']:,.2f}",
                        f"{account['currency']} {account['nav']:,.2f}",
                        f"{account['currency']} {account['unrealized_pl']:+,.2f}",
                        f"{account['currency']} {account['margin_used']:,.2f}",
                        f"{account['currency']} {account['margin_available']:,.2f}",
                        f"{account['open_position_count']}/{config.MAX_CONCURRENT_POSITIONS}",
                        mode
                    ]
                }
                st.table(account_data)

        with col_right:
            st.subheader("Action Panel")
            if st.button("Analyze Now", use_container_width=True):
                st.switch_page("pages/3_Analysis.py")
            if st.button("Open Positions", use_container_width=True):
                st.switch_page("pages/4_Positions.py")
            if st.button("Emergency Close", use_container_width=True):
                st.switch_page("pages/4_Positions.py")

        st.divider()

        # Risk status (compact)
        st.subheader("Risk Status")

        col1, col2, col3 = st.columns(3)

        with col1:
            # Daily drawdown check
            if account['balance'] > 0:
                daily_dd = (daily_pnl / account['balance']) * 100
                if daily_dd < 0:
                    daily_dd_color = "inverse" if abs(daily_dd) > 2 else "normal"
                    metric_with_tooltip(
                        "Daily Drawdown",
                        f"{daily_dd:.2f}%",
                        "daily_drawdown",
                        delta=f"Max: {config.MAX_DAILY_DRAWDOWN * 100:.0f}%",
                        delta_color=daily_dd_color
                    )
                else:
                    metric_with_tooltip("Daily Drawdown", "0%", "daily_drawdown", delta="OK")

        with col2:
            metric_with_tooltip(
                "Position Limit",
                f"{account['open_position_count']}/{config.MAX_CONCURRENT_POSITIONS}",
                "position_limit",
                delta="OK" if account['open_position_count'] < config.MAX_CONCURRENT_POSITIONS else "FULL"
            )

        with col3:
            margin_level = (account['nav'] / account['margin_used'] * 100) if account['margin_used'] > 0 else 100
            metric_with_tooltip(
                "Margin Level",
                f"{margin_level:.0f}%" if margin_level < 10000 else ">9999%",
                "margin_level",
                delta="Safe" if margin_level > 200 else "Warning"
            )

        # Decision Log (last 5 LLM decisions)
        st.divider()
        st.subheader("LLM Decision Log (Last 5)")
        decisions = db.get_recent_llm_decisions(limit=5)
        if not decisions:
            st.info("No LLM decisions logged yet.")
        else:
            for d in decisions:
                status = "EXECUTED" if d.get("executed") else "APPROVED" if d.get("approved") else "PENDING"
                st.markdown(
                    f"- **{d.get('timestamp','')}** {d.get('instrument')} | "
                    f"{d.get('recommendation')} {d.get('direction')} | {status}"
                )

        # Suggested actions - simplified
        st.divider()
        st.subheader("Next Best Action")
        if account["open_position_count"] == 0:
            st.info("No open positions. Consider running analysis in Chat.")
            if st.button("Go to Chat", use_container_width=True):
                st.switch_page("pages/2_Chat.py")
        else:
            st.info("You have open positions. Review health in Positions page.")
            if st.button("Review Positions", use_container_width=True):
                st.switch_page("pages/4_Positions.py")

        # "What do these mean?" section (collapsed)
        with st.expander("Need help understanding these metrics?"):
            simple_explanation_section(
                metrics={
                    "win_rate": stats["win_rate"],
                    "profit_factor": stats["profit_factor"],
                    "margin_level": margin_level,
                },
                title="Metric Guide"
            )

        # Status bar at bottom
        status_data = get_status_bar_data(client, config)
        render_status_bar(**status_data)

    except MT5Error as e:
        st.error(f"Error fetching account data: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
