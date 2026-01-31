"""
Empty state components for AI Trader dashboard.

Provides consistent "no data" displays across all pages.
"""

import streamlit as st
from typing import Optional, Callable

from components.tooltips import ICONS


def render_no_positions(show_action: bool = True):
    """
    Render empty state for no open positions.

    Args:
        show_action: Whether to show a call-to-action button
    """
    st.info(f"{ICONS['info']} No open positions")

    if show_action:
        st.markdown("""
        **Ready to trade?**

        1. Go to **Analysis** to analyze a currency pair
        2. If the AI recommends a trade, you can execute it there
        3. Your positions will appear here once opened
        """)


def render_no_trades(show_placeholder: bool = True):
    """
    Render empty state for no trade history.

    Args:
        show_placeholder: Whether to show a placeholder message
    """
    st.info(f"{ICONS['info']} No trade history yet")

    if show_placeholder:
        st.markdown("""
        **What you'll see here:**

        - Complete history of all your trades
        - Entry and exit prices
        - Profit/loss for each trade
        - Performance statistics

        Start trading to build your history.
        """)


def render_no_connection(retry_callback: Optional[Callable] = None, show_help: bool = True):
    """
    Render empty state for MT5 disconnection.

    Args:
        retry_callback: Optional callback function for retry button
        show_help: Whether to show troubleshooting help
    """
    st.error(f"{ICONS['error']} Not connected to MT5")

    if show_help:
        st.markdown("""
        **Troubleshooting:**

        1. Ensure MT5 terminal is running
        2. Check that you're logged into your account
        3. Enable algorithmic trading (Tools > Options > Expert Advisors)
        """)

    if retry_callback is not None:
        if st.button("Retry Connection", type="primary"):
            retry_callback()
            st.rerun()


def render_no_data(
    title: str,
    description: str = "",
    icon: str = None,
    action_label: str = None,
    action_callback: Callable = None
):
    """
    Render a generic empty state component.

    Args:
        title: Main message to display
        description: Optional longer description
        icon: Optional icon to display (use ICONS constant)
        action_label: Optional button label
        action_callback: Optional callback for action button
    """
    icon_str = icon if icon else ICONS['info']
    st.info(f"{icon_str} {title}")

    if description:
        st.markdown(description)

    if action_label and action_callback:
        if st.button(action_label, type="primary"):
            action_callback()


def render_loading_error(error_message: str, show_retry: bool = True):
    """
    Render an error state with optional retry.

    Args:
        error_message: The error message to display
        show_retry: Whether to show retry button
    """
    st.error(f"{ICONS['error']} {error_message}")

    if show_retry:
        if st.button("Retry"):
            st.rerun()


def render_empty_table(table_name: str = "data", columns: list = None):
    """
    Render placeholder for an empty table.

    Args:
        table_name: Name of the data being displayed
        columns: Optional list of column names to show in header
    """
    st.info(f"No {table_name} to display")

    if columns:
        st.caption(f"Columns: {', '.join(columns)}")


def render_coming_soon(feature_name: str):
    """
    Render a coming soon placeholder.

    Args:
        feature_name: Name of the upcoming feature
    """
    st.info(f"{ICONS['pending']} {feature_name} - Coming Soon")
    st.caption("This feature is under development and will be available in a future update.")


def render_no_analysis():
    """Render empty state when no analysis has been run."""
    st.info(f"{ICONS['info']} No analysis available")

    st.markdown("""
    **To get started:**

    1. Select a currency pair from the dropdown
    2. Choose your preferred timeframe
    3. Click "Run Analysis" to get AI recommendations

    The AI will analyze:
    - Technical indicators (trend, RSI, MACD)
    - Market sentiment
    - Risk factors (adversarial analysis)
    """)


def render_minimal_status():
    """
    Render a minimal status bar for pages without MT5 connection.

    Used on pages like Settings, Skills, History that don't require live MT5 data.
    """
    st.markdown("---")
    st.caption(f"AI Trader v1.0 | {ICONS['info']} MT5 connection not required for this page")
