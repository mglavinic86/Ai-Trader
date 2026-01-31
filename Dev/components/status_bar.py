"""
Global Status Bar Component for AI Trader dashboard.

Provides a persistent footer with key account status information.
"""

import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any


def get_connection_status_style(connected: bool) -> tuple:
    """Get styling for connection status."""
    if connected:
        return "[+] Connected", "color: green;"
    else:
        return "[x] Disconnected", "color: red;"


def format_balance(amount: float, currency: str = "EUR") -> str:
    """Format balance for display."""
    return f"{currency} {amount:,.2f}"


def render_status_bar(
    connected: bool = False,
    balance: float = 0.0,
    currency: str = "EUR",
    open_positions: int = 0,
    max_positions: int = 5,
    last_update: Optional[datetime] = None,
    unrealized_pnl: float = 0.0
):
    """
    Render a global status bar at the bottom of the page.

    Args:
        connected: Whether MT5 is connected
        balance: Account balance
        currency: Currency symbol
        open_positions: Number of open positions
        max_positions: Maximum allowed positions
        last_update: Last data update time
        unrealized_pnl: Unrealized profit/loss
    """
    # Add spacing before status bar
    st.markdown("<br><br>", unsafe_allow_html=True)

    # Create status bar container
    st.markdown("---")

    cols = st.columns([2, 2, 2, 2, 2])

    with cols[0]:
        # Connection status
        status_text, _ = get_connection_status_style(connected)
        if connected:
            st.markdown(f"**MT5:** :green[{status_text}]")
        else:
            st.markdown(f"**MT5:** :red[{status_text}]")

    with cols[1]:
        # Balance
        st.markdown(f"**Balance:** {format_balance(balance, currency)}")

    with cols[2]:
        # Positions
        position_color = "green" if open_positions < max_positions else "orange"
        st.markdown(f"**Positions:** :{position_color}[{open_positions}/{max_positions}]")

    with cols[3]:
        # Unrealized P&L
        pnl_color = "green" if unrealized_pnl >= 0 else "red"
        st.markdown(f"**P/L:** :{pnl_color}[{currency} {unrealized_pnl:+,.2f}]")

    with cols[4]:
        # Last update
        if last_update:
            time_str = last_update.strftime("%H:%M:%S")
            st.markdown(f"**Updated:** {time_str}")
        else:
            st.markdown("**Updated:** --:--:--")


def render_compact_status_bar(
    connected: bool = False,
    balance: float = 0.0,
    currency: str = "EUR",
    open_positions: int = 0,
    max_positions: int = 5,
):
    """
    Render a compact single-line status bar.

    Args:
        connected: Whether MT5 is connected
        balance: Account balance
        currency: Currency symbol
        open_positions: Number of open positions
        max_positions: Maximum allowed positions
    """
    status = "[+]" if connected else "[x]"
    status_color = "green" if connected else "red"
    pos_color = "green" if open_positions < max_positions else "orange"

    st.markdown(
        f":{status_color}[{status}] MT5 | "
        f"**{currency} {balance:,.2f}** | "
        f"Positions: :{pos_color}[{open_positions}/{max_positions}] | "
        f"{datetime.now().strftime('%H:%M')}"
    )


def get_status_bar_data(client=None, config=None) -> Dict[str, Any]:
    """
    Fetch data needed for status bar from MT5 client.

    Args:
        client: MT5Client instance
        config: Config object with MAX_CONCURRENT_POSITIONS

    Returns:
        Dict with status bar data
    """
    data = {
        "connected": False,
        "balance": 0.0,
        "currency": "EUR",
        "open_positions": 0,
        "max_positions": 5,
        "last_update": datetime.now(),
        "unrealized_pnl": 0.0
    }

    if config:
        data["max_positions"] = getattr(config, "MAX_CONCURRENT_POSITIONS", 5)

    if client:
        try:
            # Actually try to fetch account data - this is the real connection test
            account = client.get_account()
            if account and account.get("balance", 0) > 0:
                data["connected"] = True
                data["balance"] = account.get("balance", 0.0)
                data["currency"] = account.get("currency", "EUR")
                data["open_positions"] = account.get("open_position_count", 0)
                data["unrealized_pnl"] = account.get("unrealized_pl", 0.0)
                data["last_update"] = datetime.now()
            else:
                data["connected"] = False
        except Exception:
            # If we can't get account data, we're not really connected
            data["connected"] = False

    return data


def inject_status_bar_to_session(client=None, config=None):
    """
    Inject status bar data into session state for use across pages.

    Args:
        client: MT5Client instance
        config: Config object
    """
    st.session_state.status_bar_data = get_status_bar_data(client, config)


def render_status_bar_from_session():
    """
    Render status bar using data from session state.
    """
    data = st.session_state.get("status_bar_data", {})

    if data:
        render_status_bar(
            connected=data.get("connected", False),
            balance=data.get("balance", 0.0),
            currency=data.get("currency", "EUR"),
            open_positions=data.get("open_positions", 0),
            max_positions=data.get("max_positions", 5),
            last_update=data.get("last_update"),
            unrealized_pnl=data.get("unrealized_pnl", 0.0)
        )
    else:
        render_status_bar()
