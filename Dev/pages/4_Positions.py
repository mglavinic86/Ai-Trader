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
from src.utils.helpers import get_pip_divisor
from src.trading.trade_lifecycle import trade_closed_handler
from components.position_health import (
    get_position_health,
    render_health_summary,
    render_portfolio_health_meter,
    HEALTH_CONFIG,
)
from components.status_bar import render_status_bar, get_status_bar_data
from components.notifications import check_notifications, render_notifications
from components.mt5_session import get_client, reset_connection
from components.empty_states import render_no_positions
from src.utils.database import db
import MetaTrader5 as mt5

st.set_page_config(page_title="Positions - AI Trader", page_icon="", layout="wide")


def get_trade_source(ticket: int) -> tuple[str, dict]:
    """
    Get trade source (AUTO/MANUAL) and AI reasoning for a position.

    Returns:
        (source, details) - source is "AUTO" or "MANUAL", details has reasoning info
    """
    # Try to find trade in database by ticket
    try:
        # Get open trades from database
        open_trades = db.get_open_trades()
        for trade in open_trades:
            trade_id = trade.get("trade_id", "")
            # Trade ID format is typically "ticket_timestamp"
            if str(ticket) in str(trade_id):
                source = trade.get("trade_source", "MANUAL") or "MANUAL"
                if source == "AUTO_SCALPING":
                    # Get latest activity for this instrument
                    activities = db.get_recent_activities(limit=20)
                    instrument = trade.get("instrument", "")

                    for a in activities:
                        if a.get("instrument") == instrument and a.get("activity_type") == "TRADE_EXECUTED":
                            return "AUTO", {
                                "confidence": trade.get("confidence_score"),
                                "bull_case": trade.get("bull_case", ""),
                                "bear_case": trade.get("bear_case", ""),
                                "reasoning": a.get("reasoning", ""),
                                "timestamp": a.get("timestamp", "")
                            }

                    return "AUTO", {
                        "confidence": trade.get("confidence_score"),
                        "bull_case": trade.get("bull_case", ""),
                        "bear_case": trade.get("bear_case", "")
                    }
                return "MANUAL", {}

        return "MANUAL", {}
    except Exception:
        return "MANUAL", {}


def get_latest_analysis(instrument: str) -> dict:
    """Get the latest AI analysis for an instrument."""
    try:
        activities = db.get_activities_for_instrument(instrument, limit=5)
        for a in activities:
            if a.get("activity_type") in ["ANALYZING", "SIGNAL_GENERATED", "TRADE_EXECUTED"]:
                return {
                    "timestamp": a.get("timestamp", "")[:19],
                    "confidence": a.get("confidence"),
                    "direction": a.get("direction"),
                    "reasoning": a.get("reasoning", ""),
                    "details": a.get("details", {})
                }
        return {}
    except Exception:
        return {}


def main():
    st.title("Open Positions")

    client = get_client()

    if not st.session_state.connected:
        st.error("Not connected to MT5")
        if st.button("Reconnect MT5"):
            reset_connection()
            st.rerun()
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
        # === QUICK TRADE SECTION ===
        st.subheader("Open New Position")

        with st.expander("Quick Trade", expanded=not positions):
            col1, col2 = st.columns(2)

            with col1:
                # Symbol selector
                symbols = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "BTC_USD"]
                selected_symbol = st.selectbox(
                    "Symbol",
                    symbols,
                    format_func=lambda x: x.replace("_", "/"),
                    key="quick_trade_symbol"
                )

                # Direction
                direction = st.radio(
                    "Direction",
                    ["BUY", "SELL"],
                    horizontal=True,
                    key="quick_trade_direction"
                )

            with col2:
                # Lot size
                lot_size = st.number_input(
                    "Lot Size",
                    min_value=0.01,
                    max_value=1.0,
                    value=0.1,
                    step=0.01,
                    key="quick_trade_lots"
                )

                # Risk percent (for info display)
                st.caption(f"Units: {int(lot_size * 100000):,}")

            # Get current price for SL/TP defaults
            try:
                current_price = client.get_price(selected_symbol)
                bid = current_price["bid"]
                ask = current_price["ask"]
                entry = ask if direction == "BUY" else bid

                pip_value = 0.0001 if "JPY" not in selected_symbol else 0.01
                default_sl_pips = 30
                default_tp_pips = 60

                if direction == "BUY":
                    default_sl = entry - (default_sl_pips * pip_value)
                    default_tp = entry + (default_tp_pips * pip_value)
                else:
                    default_sl = entry + (default_sl_pips * pip_value)
                    default_tp = entry - (default_tp_pips * pip_value)

                st.caption(f"Current: {bid:.5f} / {ask:.5f}")

                col3, col4 = st.columns(2)
                with col3:
                    sl_price = st.number_input(
                        "Stop Loss",
                        value=default_sl,
                        format="%.5f",
                        key="quick_trade_sl"
                    )
                with col4:
                    tp_price = st.number_input(
                        "Take Profit",
                        value=default_tp,
                        format="%.5f",
                        key="quick_trade_tp"
                    )

                # Execute button
                if st.button("OPEN POSITION", type="primary", use_container_width=True, key="quick_trade_execute"):
                    units = int(lot_size * 100000)
                    if direction == "SELL":
                        units = -units

                    # Calculate risk amount (approximate)
                    sl_distance = abs(entry - sl_price)
                    risk_amount = sl_distance * abs(units) / pip_value * 10  # Rough estimate

                    order_manager = OrderManager(client)
                    result = order_manager.open_position(
                        instrument=selected_symbol,
                        units=units,
                        stop_loss=sl_price,
                        take_profit=tp_price,
                        confidence=60,  # Manual trade default
                        risk_amount=min(risk_amount, 500)  # Cap for safety
                    )

                    if result.success:
                        st.success(f"Position opened: {direction} {lot_size} lots @ {result.price:.5f}")
                        st.rerun()
                    else:
                        st.error(f"Failed: {result.error}")

            except Exception as e:
                st.error(f"Could not get price: {e}")

        st.divider()

        if not positions:
            st.info("No open positions")
        else:
            st.subheader("Active Positions")

            # Portfolio health summary
            st.markdown("**Portfolio Health:**")
            render_health_summary(positions)
            render_portfolio_health_meter(positions)

            st.divider()

            # Convert to DataFrame for display with health indicators
            df_data = []
            position_sources = {}  # Store source info for later display

            for pos in positions:
                health, details = get_position_health(pos, pos.get("instrument", ""))
                health_config = HEALTH_CONFIG[health]

                # Get trade source (AUTO vs MANUAL)
                source, source_details = get_trade_source(pos["ticket"])
                position_sources[pos["ticket"]] = (source, source_details)

                df_data.append({
                    "Source": source,
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

            def color_source(val):
                if val == "AUTO":
                    return "color: blue; font-weight: bold;"
                return "color: gray;"

            styled_df = df.style.map(color_pl, subset=['P/L']).map(color_health, subset=['Health']).map(color_source, subset=['Source'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            # Individual position management
            st.divider()
            st.subheader("Position Management")

            for pos in positions:
                pair = pos["instrument"].replace("_", "/")
                source, source_details = position_sources.get(pos["ticket"], ("MANUAL", {}))
                source_badge = " [AUTO]" if source == "AUTO" else ""

                with st.expander(f"{pair} - {pos['direction']}{source_badge} ({pos['unrealized_pl']:+.2f})"):
                    # Source indicator
                    if source == "AUTO":
                        st.info("This position was opened automatically by AI")

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

                    # AI Reasoning section (for AUTO positions)
                    if source == "AUTO" and source_details:
                        st.markdown("---")
                        st.markdown("**AI Analysis:**")
                        if source_details.get("confidence"):
                            st.write(f"Confidence: {source_details['confidence']}%")
                        if source_details.get("reasoning"):
                            st.caption(source_details["reasoning"][:200])
                        if source_details.get("bull_case"):
                            st.caption(f"Bull: {source_details['bull_case'][:100]}...")
                        if source_details.get("bear_case"):
                            st.caption(f"Bear: {source_details['bear_case'][:100]}...")

                    # Latest analysis for this instrument
                    latest = get_latest_analysis(pos["instrument"])
                    if latest:
                        st.markdown("---")
                        st.markdown("**Latest AI Analysis:**")
                        cols = st.columns(3)
                        with cols[0]:
                            st.caption(f"Time: {latest.get('timestamp', 'N/A')}")
                        with cols[1]:
                            st.caption(f"Direction: {latest.get('direction', 'N/A')}")
                        with cols[2]:
                            st.caption(f"Conf: {latest.get('confidence', 'N/A')}%")
                        if latest.get("reasoning"):
                            st.caption(f"Note: {latest['reasoning'][:80]}")

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
