"""
Shared sidebar component for AI Trader dashboard.
"""

import streamlit as st
from src.utils.config import config


def render_sidebar_account(client) -> dict:
    """
    Render account information in sidebar.

    Args:
        client: MT5Client instance

    Returns:
        Account data dict
    """
    if not client:
        st.sidebar.warning("Not connected")
        return {}

    try:
        account = client.get_account()

        with st.sidebar:
            st.subheader("Account")

            mode = "DEMO" if config.is_demo() else "LIVE"
            st.caption(f"ID: {account['id']} ({mode})")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Balance", f"{account['currency']} {account['balance']:,.0f}")
            with col2:
                st.metric("Equity", f"{account['currency']} {account['nav']:,.0f}")

            # Unrealized P/L with color
            pl = account['unrealized_pl']
            if pl >= 0:
                st.markdown(f"P/L: :green[{account['currency']} {pl:+,.2f}]")
            else:
                st.markdown(f"P/L: :red[{account['currency']} {pl:+,.2f}]")

            st.metric("Positions", f"{account['open_position_count']}/3")

        return account

    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        return {}


def render_connection_status(connected: bool):
    """Render connection status badge."""
    with st.sidebar:
        if connected:
            st.markdown('<span class="status-connected">CONNECTED</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-disconnected">DISCONNECTED</span>', unsafe_allow_html=True)


def render_quick_nav():
    """Render quick navigation links."""
    with st.sidebar:
        st.divider()
        st.caption("Quick Actions")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Analyze", use_container_width=True):
                st.switch_page("pages/2_Chat.py")
        with col2:
            if st.button("Trade", use_container_width=True):
                st.switch_page("pages/4_Positions.py")
