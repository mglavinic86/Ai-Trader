"""
Help Resources component for AI Trader dashboard.

Provides:
- Floating help button with popover
- Quick links to documentation
- Chat commands reference
- Keyboard shortcuts
- Report a problem link
"""

import streamlit as st
from typing import List, Tuple

from components.tooltips import ICONS

# =============================================================================
# CONTENT DATA
# =============================================================================

# Chat commands reference
CHAT_COMMANDS = [
    ("analyze [pair]", "Analyze a currency pair (e.g., analyze EUR/USD)"),
    ("price [pair]", "Get current price for a pair"),
    ("positions", "Show all open positions"),
    ("account", "Show account information"),
    ("close [pair]", "Close position for a pair"),
    ("emergency", "Close ALL positions immediately"),
    ("help", "Show available commands"),
]

# Keyboard shortcuts
KEYBOARD_SHORTCUTS = [
    ("Ctrl + Enter", "Submit chat message"),
    ("Escape", "Close dialogs/popups"),
    ("Tab", "Navigate between fields"),
    ("Ctrl + R", "Refresh page"),
]

# Quick links
QUICK_LINKS = [
    ("Dashboard", "pages/1_Dashboard.py", "Account overview"),
    ("Chat", "pages/2_Chat.py", "AI analysis"),
    ("Analysis", "pages/3_Analysis.py", "Technical charts"),
    ("Positions", "pages/4_Positions.py", "Manage trades"),
    ("History", "pages/5_History.py", "Past trades"),
    ("Backtest", "pages/8_Backtest.py", "Strategy testing"),
    ("Performance", "pages/10_Performance.py", "Performance analytics"),
]

# FAQ items
FAQ_ITEMS = [
    ("Why can't I connect to MT5?", "Make sure MetaTrader 5 is running and you're logged in. Check Tools > Options > Expert Advisors and enable 'Allow algorithmic trading'."),
    ("What is confidence score?", "A 0-100 score showing how confident the AI is about a trade. Above 70% = can trade, below 50% = don't trade."),
    ("Why did my trade close?", "Trades close when hitting stop loss, take profit, or manually. Check History page for details."),
    ("How is risk calculated?", "Based on confidence: 90-100% = 3% risk, 70-89% = 2%, 50-69% = 1%. Below 50% = no trade."),
    ("What pairs can I trade?", "Major forex pairs like EUR/USD, GBP/USD, USD/JPY. Use the .pro suffix in MT5 (e.g., EURUSD.pro)."),
]


# =============================================================================
# RENDER FUNCTIONS
# =============================================================================

def render_chat_commands():
    """Render chat commands reference."""
    st.markdown("**Chat Commands:**")
    for cmd, desc in CHAT_COMMANDS:
        st.markdown(f"`{cmd}` - {desc}")


def render_keyboard_shortcuts():
    """Render keyboard shortcuts list."""
    st.markdown("**Keyboard Shortcuts:**")
    for shortcut, action in KEYBOARD_SHORTCUTS:
        st.markdown(f"**{shortcut}** - {action}")


def render_quick_links():
    """Render quick navigation links."""
    st.markdown("**Quick Links:**")
    for name, page, desc in QUICK_LINKS:
        if st.button(f"{name}", key=f"help_link_{name}", use_container_width=True):
            st.switch_page(page)
        st.caption(desc)


def render_faq():
    """Render FAQ section."""
    st.markdown("**Frequently Asked Questions:**")
    for question, answer in FAQ_ITEMS:
        with st.expander(question):
            st.write(answer)


def render_report_problem():
    """Render report a problem section."""
    st.markdown("---")
    st.markdown("**Need More Help?**")
    st.markdown("""
    If you're experiencing issues:

    1. Check MT5 is running and connected
    2. Verify your internet connection
    3. Try refreshing the page (Ctrl + R)

    For technical support, contact your administrator.
    """)


# =============================================================================
# MAIN HELP BUTTON
# =============================================================================

def render_help_button():
    """
    Render a floating help button in the sidebar.

    Uses st.popover for a clean overlay experience.
    """
    with st.sidebar:
        st.divider()

        with st.popover(f"{ICONS['question']} Help & Resources", use_container_width=True):
            st.markdown("## AI Trader Help")

            # Tabs for different help sections
            tab1, tab2, tab3 = st.tabs(["Commands", "FAQ", "Shortcuts"])

            with tab1:
                render_chat_commands()

            with tab2:
                render_faq()

            with tab3:
                render_keyboard_shortcuts()
                st.divider()
                render_report_problem()


def render_help_sidebar():
    """
    Render a comprehensive help section in the sidebar.

    Alternative to popover for pages that need persistent help.
    """
    with st.sidebar:
        st.divider()
        with st.expander(f"{ICONS['question']} Help & Resources"):
            # Chat commands
            st.markdown("**Quick Commands:**")
            st.code("analyze EUR/USD", language=None)
            st.code("positions", language=None)
            st.code("account", language=None)

            st.divider()

            # Shortcuts
            st.markdown("**Shortcuts:**")
            st.caption("Ctrl+Enter - Send message")
            st.caption("Ctrl+R - Refresh page")

            st.divider()

            # Links
            st.markdown("**Resources:**")
            cols = st.columns(2)
            with cols[0]:
                if st.button("FAQ", key="help_faq_btn"):
                    st.session_state.show_help_faq = True
            with cols[1]:
                if st.button("Tutorial", key="help_tutorial_btn"):
                    st.session_state.show_wizard = True
                    st.session_state.wizard_step = 0


def render_context_help(topic: str):
    """
    Render context-sensitive help for a specific topic.

    Args:
        topic: Topic key for help content
    """
    help_content = {
        "confidence": """
        **Confidence Score (0-100)**

        - 70-100: High confidence, can trade with 2-3% risk
        - 50-69: Low confidence, trade with max 1% risk
        - Below 50: Do not trade, wait for better setup
        """,
        "positions": """
        **Managing Positions**

        - Green P/L = profit, Red = loss
        - SL = Stop Loss, TP = Take Profit
        - Click "Close Position" to exit a trade
        """,
        "analysis": """
        **Technical Analysis**

        - RSI > 70 = Overbought (may fall)
        - RSI < 30 = Oversold (may rise)
        - MACD crossing up = Bullish signal
        """,
        "risk": """
        **Risk Management**

        - Max 3 positions at once
        - Max 3% daily drawdown
        - Always use stop losses
        """,
    }

    content = help_content.get(topic, "Help topic not found.")
    st.info(content)


def render_inline_help(text: str, help_text: str):
    """
    Render text with inline help tooltip.

    Args:
        text: Main text to display
        help_text: Help text for tooltip
    """
    st.markdown(f"{text} {ICONS['question']}", help=help_text)


# =============================================================================
# TOOLTIP HELPERS
# =============================================================================

def get_field_help(field_name: str) -> str:
    """
    Get help text for a specific field.

    Args:
        field_name: Name of the field

    Returns:
        Help text string
    """
    field_help = {
        "pair": "Currency pair to analyze (e.g., EUR/USD, GBP/USD)",
        "volume": "Trade size in lots. 0.01 = micro, 0.1 = mini, 1.0 = standard",
        "stop_loss": "Price at which to close trade if losing",
        "take_profit": "Price at which to close trade with profit",
        "confidence": "AI confidence score (0-100). Higher = more certain",
        "risk_percent": "Percentage of account to risk on this trade",
    }
    return field_help.get(field_name, "")


# =============================================================================
# ONBOARDING INTEGRATION
# =============================================================================

def render_first_time_hints():
    """
    Render helpful hints for first-time users.

    Shows only if user hasn't dismissed them.
    """
    if st.session_state.get("hints_dismissed", False):
        return

    st.info(f"""
    {ICONS['info']} **First time here?** Here are some tips:

    1. Start by typing `analyze EUR/USD` in the Chat
    2. Check the Confidence Score before trading
    3. Never trade below 50% confidence

    Click the Help button in the sidebar for more.
    """)

    if st.button("Got it, don't show again", key="dismiss_hints"):
        st.session_state.hints_dismissed = True
        st.rerun()


def render_page_intro(page_name: str):
    """
    Render a brief introduction for a page.

    Args:
        page_name: Name of the current page
    """
    intros = {
        "dashboard": "Your account overview with key metrics and suggested actions.",
        "chat": "Talk to the AI to analyze pairs and get trade recommendations.",
        "analysis": "View technical analysis charts and indicators for any pair.",
        "positions": "Monitor and manage your open trades.",
        "history": "Review your past trades and performance statistics.",
        "settings": "Configure risk limits, preferences, and account settings.",
        "backtest": "Test trading strategies on historical data.",
    }

    intro = intros.get(page_name.lower(), "")
    if intro:
        st.caption(intro)
