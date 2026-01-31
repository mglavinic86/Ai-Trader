"""
AI Trader - Dashboard Page

Account overview and daily performance.
"""

import streamlit as st
from datetime import datetime
import sys
from pathlib import Path

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.utils.config import config
from src.utils.database import db
from src.trading.mt5_client import MT5Client, MT5Error
from components.tooltips import metric_with_tooltip, simple_explanation_section, ICONS, tooltip_text
from components.suggested_actions import render_suggested_actions, is_forex_market_open, get_market_session
from components.status_bar import render_status_bar, get_status_bar_data
from components.notifications import check_notifications, render_notifications
from components.skill_buttons import render_skill_buttons_grid, get_available_pairs
from components.mt5_session import get_client, is_connected, reset_connection

st.set_page_config(page_title="Dashboard - AI Trader", page_icon="", layout="wide")


def main():
    st.title("Dashboard")

    client = get_client()

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

        # Header metrics
        st.subheader(f"Account Overview ({mode})")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            metric_with_tooltip(
                "Balance",
                f"{account['currency']} {account['balance']:,.2f}",
                "balance"
            )

        with col2:
            metric_with_tooltip(
                "Equity",
                f"{account['currency']} {account['nav']:,.2f}",
                "equity",
                delta=f"{account['unrealized_pl']:+,.2f}"
            )

        with col3:
            daily_pnl_pct = (daily_pnl / account['balance'] * 100) if account['balance'] > 0 else 0
            metric_with_tooltip(
                "Today's P/L",
                f"{account['currency']} {daily_pnl:+,.2f}",
                "daily_pnl",
                delta=f"{daily_pnl_pct:+.2f}%"
            )

        with col4:
            metric_with_tooltip(
                "Open Positions",
                f"{account['open_position_count']} / {config.MAX_CONCURRENT_POSITIONS}",
                "position_limit"
            )

        st.divider()

        # Two columns layout
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.subheader("Account Details")

            # Account info table
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
            st.subheader("Performance")

            # Performance metrics with tooltips
            metric_with_tooltip("Total Trades", stats["total_trades"], "total_trades",
                               help_text="Total number of trades you've taken.")
            metric_with_tooltip("Win Rate", f"{stats['win_rate']:.1f}%", "win_rate")
            metric_with_tooltip("Total P/L", f"${stats['total_pnl']:+,.2f}", "total_return",
                               help_text="Total profit or loss from all closed trades.")
            metric_with_tooltip("Profit Factor", f"{stats['profit_factor']:.2f}", "profit_factor")

        st.divider()

        # Risk status
        st.subheader("Risk Management Status")

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

        # Quick actions
        st.divider()
        st.subheader("Quick Actions")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("Analyze EUR/USD", use_container_width=True):
                st.switch_page("pages/2_Chat.py")

        with col2:
            if st.button("View Positions", use_container_width=True):
                st.switch_page("pages/4_Positions.py")

        with col3:
            if st.button("Trade History", use_container_width=True):
                st.switch_page("pages/5_History.py")

        with col4:
            if st.button("Settings", use_container_width=True):
                st.switch_page("pages/6_Settings.py")

        # Suggested Actions section
        st.divider()

        render_suggested_actions(
            account=account,
            positions=positions,
            stats=stats,
            daily_pnl=daily_pnl,
            config={
                "max_positions": config.MAX_CONCURRENT_POSITIONS,
                "max_daily_drawdown": config.MAX_DAILY_DRAWDOWN
            },
            max_actions=4
        )

        # Trading Strategies section
        st.divider()
        st.subheader("Trading Strategies")
        st.caption("Click a strategy to analyze with AI")

        # Pair selector for strategy analysis
        strategy_pair = st.selectbox(
            "Select pair for analysis",
            get_available_pairs(),
            format_func=lambda x: x.replace("_", "/"),
            key="dashboard_strategy_pair"
        )

        # Render 6 skill cards in 3x2 grid
        clicked_command = render_skill_buttons_grid(
            pair=strategy_pair,
            key_prefix="dashboard_",
            columns=3
        )

        if clicked_command:
            # Store command and navigate to Chat
            st.session_state.pending_command = clicked_command
            st.switch_page("pages/2_Chat.py")

        # "What do these mean?" section
        st.divider()
        simple_explanation_section(
            metrics={
                "win_rate": stats["win_rate"],
                "profit_factor": stats["profit_factor"],
                "margin_level": margin_level,
            },
            title="Need help understanding these metrics?"
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
