"""
AI Trader - Streamlit Web Dashboard

Main entry point for the web-based trading interface.

Usage:
    cd Dev
    python -m streamlit run dashboard.py

Opens browser at http://localhost:8501
"""

import streamlit as st
from pathlib import Path
import sys

# Add Dev to path for imports
DEV_DIR = Path(__file__).parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.utils.config import config
from src.utils.logger import logger
from src.trading.mt5_client import MT5Client, MT5Error
from components.onboarding import render_welcome_wizard, render_welcome_wizard_sidebar_trigger, has_completed_onboarding
from components.help_resources import render_help_button
from components.styles import inject_global_styles, THEME, get_status_badge_html

# ===================
# Page Configuration
# ===================

st.set_page_config(
    page_title="AI Trader",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "AI Trader - Forex Trading Assistant v1.0"
    }
)

# ===================
# Custom Dark Theme CSS
# ===================

# Inject global styles from centralized module
inject_global_styles()

# ===================
# Session State Init
# ===================

def init_session_state():
    """Initialize session state variables."""
    if "mt5_client" not in st.session_state:
        st.session_state.mt5_client = None
    if "connected" not in st.session_state:
        st.session_state.connected = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "last_analysis" not in st.session_state:
        st.session_state.last_analysis = None


def connect_mt5():
    """Connect to MT5 and store client in session state."""
    try:
        is_valid, error = config.validate()
        if not is_valid:
            return False, f"Configuration error: {error}"

        client = MT5Client()
        if client.is_connected():
            st.session_state.mt5_client = client
            st.session_state.connected = True
            return True, "Connected successfully"
        else:
            return False, "Could not connect to MT5. Is the terminal running?"
    except MT5Error as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"


def get_mt5_client() -> MT5Client:
    """Get MT5 client from session state."""
    return st.session_state.get("mt5_client")


# ===================
# Sidebar
# ===================

def render_sidebar():
    """Render the sidebar with account info and connection status."""
    with st.sidebar:
        st.title("AI Trader")
        st.caption("Forex Trading Assistant v1.0")

        st.divider()

        # Connection status
        if st.session_state.connected:
            st.markdown(get_status_badge_html(True), unsafe_allow_html=True)

            try:
                client = get_mt5_client()
                if client:
                    account = client.get_account()

                    # Account info
                    st.subheader("Account")
                    mode = "DEMO" if config.is_demo() else "LIVE"
                    st.caption(f"ID: {account['id']} ({mode})")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Balance", f"{account['currency']} {account['balance']:,.0f}")
                    with col2:
                        st.metric("Equity", f"{account['currency']} {account['nav']:,.0f}")

                    # Unrealized P/L
                    pl = account['unrealized_pl']
                    pl_color = "profit" if pl >= 0 else "loss"
                    st.markdown(f"Unrealized P/L: <span class='{pl_color}'>{account['currency']} {pl:+,.2f}</span>",
                               unsafe_allow_html=True)

                    # Positions
                    st.metric("Open Positions", f"{account['open_position_count']}/3")

            except Exception as e:
                st.error(f"Error fetching account: {e}")
                # Update connection status - MT5 is not actually connected
                st.session_state.connected = False
                st.session_state.mt5_client = None
        else:
            st.markdown(get_status_badge_html(False), unsafe_allow_html=True)
            st.caption("MT5 terminal not connected")

            if st.button("Connect to MT5", type="primary", use_container_width=True):
                with st.spinner("Connecting..."):
                    success, message = connect_mt5()
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

        st.divider()

        # Navigation info
        st.caption("Navigation")
        st.markdown("""
        - **Dashboard**: Account overview
        - **Chat**: AI conversation
        - **Analysis**: Technical analysis
        - **Positions**: Manage positions
        - **History**: Trade history
        - **Settings**: Configuration
        - **Skills**: Knowledge base
        - **Backtest**: Strategy testing
        - **Learn**: Forex education
        - **Performance**: Analytics
        """)

        st.divider()

        # Help button
        render_help_button()

        # Show tutorial trigger for returning users
        if has_completed_onboarding():
            render_welcome_wizard_sidebar_trigger()

        st.divider()

        # Footer
        st.caption("Sirius Grupa d.o.o.")
        st.caption("MT5 Terminal must be running")


# ===================
# Main App
# ===================

def main():
    """Main application entry point."""
    init_session_state()

    # Auto-connect on first load
    if not st.session_state.connected:
        success, _ = connect_mt5()

    # Render sidebar
    render_sidebar()

    # Show welcome wizard for new users
    if not has_completed_onboarding():
        render_welcome_wizard()
        # If wizard is showing, don't render the rest of the page
        if st.session_state.get("show_wizard", True):
            return

    # Main content - redirect to Dashboard
    st.title("Welcome to AI Trader")

    st.markdown("""
    ### Getting Started

    Use the sidebar navigation to access different features:

    1. **Dashboard** - View your account overview and daily P/L
    2. **Chat** - Interact with the AI trading assistant
    3. **Analysis** - Run technical analysis on currency pairs
    4. **Positions** - View and manage open positions
    5. **History** - Review your trade history
    6. **Settings** - Configure the application
    7. **Skills** - Browse trading skills and knowledge

    ---

    **Quick Actions:**
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Analyze EUR/USD", use_container_width=True):
            st.switch_page("pages/2_Chat.py")

    with col2:
        if st.button("View Positions", use_container_width=True):
            st.switch_page("pages/4_Positions.py")

    with col3:
        if st.button("Account Status", use_container_width=True):
            st.switch_page("pages/1_Dashboard.py")

    # Show connection warning if not connected
    if not st.session_state.connected:
        st.warning("""
        **Not connected to MT5**

        Please ensure:
        1. MT5 terminal is running
        2. You are logged into your account
        3. Algorithmic trading is enabled (Tools > Options > Expert Advisors)

        Click "Connect to MT5" in the sidebar when ready.
        """)


if __name__ == "__main__":
    main()
