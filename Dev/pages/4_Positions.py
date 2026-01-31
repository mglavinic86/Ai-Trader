"""
AI Trader - Positions Page

View and manage open positions.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.utils.config import config
from src.trading.mt5_client import MT5Client, MT5Error
from src.trading.orders import OrderManager
from src.trading.trade_lifecycle import trade_closed_handler
from components.position_health import (
    get_position_health,
    render_health_summary,
    render_portfolio_health_meter,
    HEALTH_CONFIG,
)
from components.status_bar import render_status_bar, get_status_bar_data
from components.notifications import check_notifications, render_notifications
from components.mt5_session import get_client, is_connected
from components.empty_states import render_no_positions
import MetaTrader5 as mt5

st.set_page_config(page_title="Positions - AI Trader", page_icon="", layout="wide")


def main():
    st.title("Open Positions")

    client = get_client()

    if not st.session_state.connected:
        st.error("Not connected to MT5")
        return

    # Refresh button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("Refresh", type="primary"):
            st.rerun()

    try:
        positions = client.get_positions()
        account = client.get_account()

        # Check and render notifications at top
        notifications = check_notifications(
            account=account,
            positions=positions,
            config={
                "max_daily_drawdown": config.MAX_DAILY_DRAWDOWN,
                "max_positions": config.MAX_CONCURRENT_POSITIONS
            }
        )
        render_notifications(notifications, max_display=2, key_suffix="_positions")

        # Summary metrics
        st.subheader("Summary")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Open Positions", f"{len(positions)}/{config.MAX_CONCURRENT_POSITIONS}")

        with col2:
            total_pl = sum(p["unrealized_pl"] for p in positions)
            st.metric("Total P/L", f"{account['currency']} {total_pl:+,.2f}")

        with col3:
            st.metric("Margin Used", f"{account['currency']} {account['margin_used']:,.2f}")

        with col4:
            st.metric("Margin Available", f"{account['currency']} {account['margin_available']:,.2f}")

        st.divider()

        # Positions table
        if not positions:
            st.info("No open positions")

            # Placeholder for when there's analysis
            if st.session_state.get("last_analysis"):
                analysis = st.session_state.last_analysis
                st.subheader("Last Analysis")
                st.write(f"**{analysis['instrument']}** - Confidence: {analysis['confidence'].confidence_score}%")
                if analysis['confidence'].can_trade:
                    st.success("Trade opportunity available!")
        else:
            st.subheader("Active Positions")

            # Portfolio health summary
            st.markdown("**Portfolio Health:**")
            render_health_summary(positions)
            render_portfolio_health_meter(positions)

            st.divider()

            # Convert to DataFrame for display with health indicators
            df_data = []
            for pos in positions:
                health, details = get_position_health(pos, pos.get("instrument", ""))
                health_config = HEALTH_CONFIG[health]

                df_data.append({
                    "Pair": pos["instrument"].replace("_", "/"),
                    "Direction": pos["direction"],
                    "Volume": pos["volume"],
                    "Entry": pos["price_open"],
                    "Current": pos["price_current"],
                    "P/L": pos["unrealized_pl"],
                    "Health": health.value,
                    "SL Dist": f"{details['distance_to_sl_pct']:.0f}%",
                    "SL": pos["sl"] if pos["sl"] > 0 else "-",
                    "TP": pos["tp"] if pos["tp"] > 0 else "-",
                    "Ticket": pos["ticket"]
                })

            df = pd.DataFrame(df_data)

            # Style the dataframe
            def color_pl(val):
                if isinstance(val, (int, float)):
                    color = 'green' if val >= 0 else 'red'
                    return f'color: {color}'
                return ''

            def color_health(val):
                health_colors = {
                    "EXCELLENT": "color: green; font-weight: bold;",
                    "GOOD": "color: green;",
                    "NEUTRAL": "color: gray;",
                    "WARNING": "color: orange; font-weight: bold;",
                    "DANGER": "color: red; font-weight: bold;"
                }
                return health_colors.get(val, '')

            styled_df = df.style.map(color_pl, subset=['P/L']).map(color_health, subset=['Health'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            # Individual position management
            st.divider()
            st.subheader("Position Management")

            for pos in positions:
                pair = pos["instrument"].replace("_", "/")
                with st.expander(f"{pair} - {pos['direction']} ({pos['unrealized_pl']:+.2f})"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.write(f"**Entry:** {pos['price_open']:.5f}")
                        st.write(f"**Current:** {pos['price_current']:.5f}")

                    with col2:
                        st.write(f"**Volume:** {pos['volume']}")
                        st.write(f"**Ticket:** {pos['ticket']}")

                    with col3:
                        sl_display = f"{pos['sl']:.5f}" if pos['sl'] > 0 else "Not set"
                        tp_display = f"{pos['tp']:.5f}" if pos['tp'] > 0 else "Not set"
                        st.write(f"**SL:** {sl_display}")
                        st.write(f"**TP:** {tp_display}")

                    # Close button
                    if st.button(f"Close Position", key=f"close_{pos['ticket']}"):
                        try:
                            # Capture position info before closing
                            entry_price = pos['price_open']
                            direction = pos['direction']
                            current_pnl = pos['unrealized_pl']
                            ticket = pos['ticket']

                            order_manager = OrderManager(client)
                            result = order_manager.close_position(pos["instrument"])
                            if result.success:
                                # Get account balance for pnl_percent calculation
                                account = client.get_account()
                                pnl_percent = (current_pnl / account['balance']) * 100 if account['balance'] > 0 else 0

                                # Trade lifecycle handler (already called in orders.py, but ensure it's logged)
                                st.success(f"Position closed successfully (P/L: {current_pnl:+.2f})")
                                st.rerun()
                            else:
                                st.error(f"Failed to close: {result.error}")
                        except Exception as e:
                            st.error(f"Error: {e}")

        # Emergency close all
        st.divider()
        st.subheader("Emergency Actions")

        col1, col2 = st.columns(2)

        with col1:
            if positions:
                if st.button("CLOSE ALL POSITIONS", type="secondary", use_container_width=True):
                    st.session_state.confirm_close_all = True

        with col2:
            if st.session_state.get("confirm_close_all"):
                st.warning("Are you sure you want to close ALL positions?")
                if st.button("YES, CLOSE ALL", type="primary"):
                    try:
                        order_manager = OrderManager(client)
                        results = order_manager.close_all_positions()
                        closed = sum(1 for r in results if r.success)
                        st.success(f"Closed {closed} position(s)")
                        st.session_state.confirm_close_all = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

                if st.button("Cancel"):
                    st.session_state.confirm_close_all = False
                    st.rerun()

        # Status bar at bottom
        status_data = get_status_bar_data(client, config)
        render_status_bar(**status_data)

    except MT5Error as e:
        st.error(f"Error fetching positions: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
