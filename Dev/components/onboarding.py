"""
Welcome Wizard / Onboarding component for AI Trader dashboard.

Provides an interactive onboarding experience for new users with:
- 5-step wizard: Welcome, What is AI Trader, MT5 Setup, Confidence Score, Quick Tour
- Progress indicator
- "Don't show again" persistence (session state + file marker)
"""

import streamlit as st
from pathlib import Path
from typing import Optional

from components.tooltips import ICONS

# =============================================================================
# CONFIGURATION
# =============================================================================

# File marker for persistent "don't show again"
ONBOARDING_MARKER_FILE = Path(__file__).parent.parent / ".onboarding_complete"

# Wizard steps configuration
WIZARD_STEPS = [
    {
        "id": "welcome",
        "title": "Welcome to AI Trader",
        "icon": "[*]",
    },
    {
        "id": "what_is",
        "title": "What is AI Trader?",
        "icon": "[?]",
    },
    {
        "id": "mt5_setup",
        "title": "MT5 Setup",
        "icon": "[T]",
    },
    {
        "id": "confidence",
        "title": "Understanding Confidence",
        "icon": "[~]",
    },
    {
        "id": "quick_tour",
        "title": "Quick Tour",
        "icon": "[i]",
    },
]


# =============================================================================
# PERSISTENCE FUNCTIONS
# =============================================================================

def has_completed_onboarding() -> bool:
    """
    Check if user has completed onboarding.

    Returns:
        True if onboarding should be skipped
    """
    # Check session state first (for current session)
    if st.session_state.get("onboarding_complete", False):
        return True

    # Check file marker (persistent across sessions)
    if ONBOARDING_MARKER_FILE.exists():
        st.session_state.onboarding_complete = True
        return True

    return False


def mark_onboarding_complete(dont_show_again: bool = False):
    """
    Mark onboarding as complete.

    Args:
        dont_show_again: If True, create persistent file marker
    """
    st.session_state.onboarding_complete = True
    st.session_state.show_wizard = False

    if dont_show_again:
        try:
            ONBOARDING_MARKER_FILE.touch()
        except Exception:
            pass  # Silently fail if can't create file


def reset_onboarding():
    """Reset onboarding state (for testing)."""
    st.session_state.onboarding_complete = False
    st.session_state.show_wizard = True
    st.session_state.wizard_step = 0

    if ONBOARDING_MARKER_FILE.exists():
        try:
            ONBOARDING_MARKER_FILE.unlink()
        except Exception:
            pass


# =============================================================================
# STEP CONTENT RENDERERS
# =============================================================================

def render_step_welcome():
    """Render welcome step content."""
    st.markdown("""
    ### Welcome, Trader!

    We're excited to have you here. **AI Trader** is your intelligent assistant
    for forex trading, combining artificial intelligence with proven technical analysis.

    This quick wizard will help you get started in just a few steps.

    ---

    **What you'll learn:**

    - [+] What AI Trader does and how it helps you trade
    - [+] How to set up MetaTrader 5 connection
    - [+] Understanding the Confidence Score system
    - [+] Quick tour of the dashboard features

    **Time required:** About 2 minutes
    """)


def render_step_what_is():
    """Render 'What is AI Trader' step content."""
    st.markdown("""
    ### What is AI Trader?

    AI Trader is an **automated forex analysis system** that uses:

    ---

    **Claude AI** - Advanced language model for market analysis
    """)
    st.info("The AI analyzes market conditions, news sentiment, and technical indicators to provide trading recommendations.")

    st.markdown("""
    **Technical Indicators** - EMA, RSI, MACD, ATR, Support/Resistance
    """)
    st.info("These proven indicators help identify trends, momentum, and key price levels.")

    st.markdown("""
    **Bull vs Bear Analysis** - Adversarial reasoning
    """)
    st.info("The AI argues both sides (bullish and bearish) before making a final recommendation.")

    st.markdown("""
    ---

    **Important:** AI Trader provides analysis and recommendations, but YOU make the final decision.
    Always use proper risk management.
    """)


def render_step_mt5_setup():
    """Render MT5 setup step content."""
    st.markdown("""
    ### MetaTrader 5 Setup

    AI Trader connects to **MetaTrader 5** for live market data and trade execution.

    ---

    **Prerequisites:**

    1. **Download MT5** from your broker (OANDA, etc.)
    2. **Login** to your trading account
    3. **Keep MT5 running** while using AI Trader

    ---

    **Required MT5 Settings:**

    Go to **Tools > Options > Expert Advisors** and enable:
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.success("[ok] Allow algorithmic trading")
    with col2:
        st.success("[ok] Allow DLL imports")

    st.markdown("""
    ---

    **Connection Status:**
    """)

    if st.session_state.get("connected", False):
        st.success("[+] MT5 is connected and ready!")
    else:
        st.warning("[!] MT5 is not connected. Make sure the terminal is running.")


def render_step_confidence():
    """Render confidence score explanation step."""
    st.markdown("""
    ### Understanding the Confidence Score

    Every analysis produces a **Confidence Score** from 0-100 that determines:

    ---
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**High Confidence (70-100)**")
        st.markdown("""
        <div style="background: #1e2530; padding: 15px; border-radius: 8px; border-left: 4px solid #10b981;">
            <strong style="color: #10b981;">CAN TRADE</strong><br>
            <span style="color: #9ca3af;">Risk: 2-3% per trade</span>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("**Low Confidence (Below 50)**")
        st.markdown("""
        <div style="background: #1e2530; padding: 15px; border-radius: 8px; border-left: 4px solid #ef4444;">
            <strong style="color: #ef4444;">DO NOT TRADE</strong><br>
            <span style="color: #9ca3af;">Wait for better setup</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    ---

    **Risk Tiers (Hard-Coded for Safety):**

    | Confidence | Risk Per Trade | Action |
    |------------|---------------|--------|
    | 90-100% | Max 3% | Strong trade |
    | 70-89% | Max 2% | Normal trade |
    | 50-69% | Max 1% | Small position |
    | Below 50% | 0% | Do not trade |

    ---

    **Why this matters:** The AI only recommends trades when multiple factors align.
    Low confidence means there's too much uncertainty - wait for a clearer setup.
    """)


def render_step_quick_tour():
    """Render quick tour step content."""
    st.markdown("""
    ### Quick Tour of AI Trader

    Here's what you'll find in each section:

    ---
    """)

    features = [
        ("Dashboard", "Account overview, daily P/L, suggested actions"),
        ("Chat", "Talk to the AI - analyze pairs, get recommendations"),
        ("Analysis", "Technical analysis charts and indicators"),
        ("Positions", "View and manage open trades"),
        ("History", "Review past trades and performance"),
        ("Settings", "Configure risk limits and preferences"),
        ("Skills", "View and edit AI knowledge base"),
        ("Backtest", "Test strategies on historical data"),
        ("Learn", "Educational content for forex beginners"),
        ("Performance", "Detailed performance analytics and charts"),
    ]

    for name, desc in features:
        st.markdown(f"**{name}** - {desc}")

    st.markdown("""
    ---

    **Quick Start Tip:**

    Go to the **Chat** page and type:
    ```
    analyze EUR/USD
    ```

    The AI will analyze the pair and provide a recommendation with confidence score.

    ---

    **You're all set!** Click "Finish" to start trading.
    """)


# =============================================================================
# MAIN WIZARD RENDERER
# =============================================================================

def render_progress_indicator(current_step: int, total_steps: int):
    """
    Render a progress indicator for the wizard.

    Args:
        current_step: Current step index (0-based)
        total_steps: Total number of steps
    """
    # Progress bar
    progress = (current_step + 1) / total_steps
    st.progress(progress)

    # Step indicators
    cols = st.columns(total_steps)
    for i, (col, step) in enumerate(zip(cols, WIZARD_STEPS)):
        with col:
            if i < current_step:
                # Completed
                st.markdown(f"<div style='text-align: center; color: #10b981;'>[ok]</div>", unsafe_allow_html=True)
            elif i == current_step:
                # Current
                st.markdown(f"<div style='text-align: center; color: #3b82f6; font-weight: bold;'>{step['icon']}</div>", unsafe_allow_html=True)
            else:
                # Upcoming
                st.markdown(f"<div style='text-align: center; color: #6b7280;'>{i + 1}</div>", unsafe_allow_html=True)

    # Step title
    st.markdown(f"<div style='text-align: center; color: #9ca3af; margin-bottom: 20px;'>Step {current_step + 1} of {total_steps}: {WIZARD_STEPS[current_step]['title']}</div>", unsafe_allow_html=True)


def render_wizard_content(step: int):
    """
    Render content for a specific wizard step.

    Args:
        step: Step index (0-based)
    """
    step_renderers = {
        0: render_step_welcome,
        1: render_step_what_is,
        2: render_step_mt5_setup,
        3: render_step_confidence,
        4: render_step_quick_tour,
    }

    renderer = step_renderers.get(step, render_step_welcome)
    renderer()


def render_welcome_wizard():
    """
    Render the welcome wizard modal/dialog.

    Call this at the start of dashboard.py to show onboarding for new users.
    """
    # Initialize wizard state
    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 0
    if "show_wizard" not in st.session_state:
        st.session_state.show_wizard = not has_completed_onboarding()

    # Don't show if completed
    if not st.session_state.show_wizard:
        return

    # Wizard container with styling
    st.markdown("""
    <style>
    .wizard-container {
        background-color: #1a1d24;
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="wizard-container">', unsafe_allow_html=True)

        current_step = st.session_state.wizard_step
        total_steps = len(WIZARD_STEPS)

        # Progress indicator
        render_progress_indicator(current_step, total_steps)

        st.divider()

        # Step content
        render_wizard_content(current_step)

        st.divider()

        # Navigation buttons
        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            if current_step > 0:
                if st.button("< Back", use_container_width=True):
                    st.session_state.wizard_step -= 1
                    st.rerun()
            else:
                # Skip button on first step
                if st.button("Skip Tour", use_container_width=True):
                    mark_onboarding_complete(dont_show_again=False)
                    st.rerun()

        with col3:
            if current_step < total_steps - 1:
                if st.button("Next >", type="primary", use_container_width=True):
                    st.session_state.wizard_step += 1
                    st.rerun()
            else:
                # Last step - finish button
                if st.button("Finish", type="primary", use_container_width=True):
                    mark_onboarding_complete(dont_show_again=st.session_state.get("wizard_dont_show", False))
                    st.rerun()

        # Don't show again checkbox (only on last step)
        if current_step == total_steps - 1:
            st.session_state.wizard_dont_show = st.checkbox(
                "Don't show this wizard again",
                value=st.session_state.get("wizard_dont_show", False),
                key="wizard_dont_show_checkbox"
            )

        st.markdown('</div>', unsafe_allow_html=True)


def render_welcome_wizard_sidebar_trigger():
    """
    Render a small button in sidebar to re-open the wizard.

    Useful for users who want to see the onboarding again.
    """
    with st.sidebar:
        if st.button(f"{ICONS['question']} Show Tutorial", use_container_width=True):
            st.session_state.show_wizard = True
            st.session_state.wizard_step = 0
            st.rerun()


def should_show_wizard() -> bool:
    """
    Check if wizard should be displayed.

    Returns:
        True if wizard should be shown
    """
    return st.session_state.get("show_wizard", False) and not has_completed_onboarding()
