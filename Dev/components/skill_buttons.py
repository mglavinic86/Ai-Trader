"""
Skill Buttons Component for AI Trader.

Provides reusable skill activation buttons for Dashboard and Chat pages.
Clicking a skill button triggers a predefined AI analysis command.
"""

from typing import Optional
import streamlit as st


# Skill definitions with colors matching the dashboard theme
SKILL_DEFINITIONS = [
    {
        "id": "smc_trading",
        "name": "SMC",
        "full_name": "Smart Money Concepts",
        "description": "Institutional price action analysis",
        "icon": "[SMC]",
        "color": "#3b82f6",  # Blue
        "command": "SMC analiza za {pair}",
    },
    {
        "id": "fvg_strategy",
        "name": "FVG",
        "full_name": "Fair Value Gap",
        "description": "Imbalance zone trading",
        "icon": "[FVG]",
        "color": "#10b981",  # Green
        "command": "FVG analiza za {pair}",
    },
    {
        "id": "killzone_trading",
        "name": "Killzone",
        "full_name": "Session Trading",
        "description": "London/NY session strategies",
        "icon": "[KZ]",
        "color": "#f59e0b",  # Orange
        "command": "killzone analiza za {pair}",
    },
    {
        "id": "scalping",
        "name": "Scalping",
        "full_name": "Scalping",
        "description": "Quick M5/M15 trades",
        "icon": "[SC]",
        "color": "#ef4444",  # Red
        "command": "scalping analiza za {pair}",
    },
    {
        "id": "swing_trading",
        "name": "Swing",
        "full_name": "Swing Trading",
        "description": "Multi-day positions",
        "icon": "[SW]",
        "color": "#8b5cf6",  # Purple
        "command": "swing analiza za {pair}",
    },
    {
        "id": "news_trading",
        "name": "News",
        "full_name": "News Trading",
        "description": "Event-driven strategies",
        "icon": "[NW]",
        "color": "#ec4899",  # Pink
        "command": "news analiza za {pair}",
    },
]


def get_skill_by_id(skill_id: str) -> Optional[dict]:
    """Get skill definition by ID."""
    for skill in SKILL_DEFINITIONS:
        if skill["id"] == skill_id:
            return skill
    return None


def render_skill_card(skill: dict, pair: str = "EUR_USD", key_prefix: str = "") -> bool:
    """
    Render a skill card with description and action button.

    Args:
        skill: Skill definition dict
        pair: Currency pair for command
        key_prefix: Unique prefix for button key

    Returns:
        True if button was clicked
    """
    color = skill["color"]

    st.markdown(f"""
    <div style="
        background-color: #1e2530;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid {color};
        margin-bottom: 8px;
    ">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 14px; color: {color}; font-weight: bold;">{skill['icon']}</span>
            <strong style="color: #e5e7eb; font-size: 14px;">{skill['full_name']}</strong>
        </div>
        <p style="color: #9ca3af; margin: 6px 0 0 0; font-size: 12px;">
            {skill['description']}
        </p>
    </div>
    """, unsafe_allow_html=True)

    return st.button(
        f"Analyze with {skill['name']}",
        key=f"{key_prefix}skill_{skill['id']}",
        use_container_width=True
    )


def render_skill_buttons_grid(
    pair: str = "EUR_USD",
    skills: list[str] = None,
    key_prefix: str = "",
    columns: int = 3
) -> Optional[str]:
    """
    Render skill buttons in a grid layout.

    Args:
        pair: Currency pair for analysis command
        skills: List of skill IDs to show (None = all)
        key_prefix: Unique prefix for button keys
        columns: Number of columns in grid

    Returns:
        Command string if a skill was clicked, None otherwise
    """
    if skills is None:
        skills_to_show = SKILL_DEFINITIONS
    else:
        skills_to_show = [s for s in SKILL_DEFINITIONS if s["id"] in skills]

    clicked_command = None
    cols = st.columns(columns)

    for i, skill in enumerate(skills_to_show):
        with cols[i % columns]:
            if render_skill_card(skill, pair, key_prefix):
                clicked_command = skill["command"].format(pair=pair.replace("_", "/"))

    return clicked_command


def render_compact_skill_buttons(
    pair: str = "EUR_USD",
    key_prefix: str = "",
    process_command_func=None
) -> None:
    """
    Render compact skill buttons for sidebar (2 columns).

    Args:
        pair: Currency pair for analysis
        key_prefix: Unique prefix for button keys
        process_command_func: Function to process command (from Chat page)
    """
    st.caption("Strategy Analysis")

    # Row 1: SMC, FVG
    col1, col2 = st.columns(2)
    with col1:
        if st.button("SMC", key=f"{key_prefix}smc", use_container_width=True,
                     help="Smart Money Concepts"):
            _trigger_analysis("SMC analiza za", pair, process_command_func)
    with col2:
        if st.button("FVG", key=f"{key_prefix}fvg", use_container_width=True,
                     help="Fair Value Gap"):
            _trigger_analysis("FVG analiza za", pair, process_command_func)

    # Row 2: Killzone, Scalping
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Killzone", key=f"{key_prefix}kz", use_container_width=True,
                     help="Session trading"):
            _trigger_analysis("killzone analiza za", pair, process_command_func)
    with col2:
        if st.button("Scalping", key=f"{key_prefix}scalp", use_container_width=True):
            _trigger_analysis("scalping analiza za", pair, process_command_func)

    # Row 3: Swing, News
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Swing", key=f"{key_prefix}swing", use_container_width=True):
            _trigger_analysis("swing analiza za", pair, process_command_func)
    with col2:
        if st.button("News", key=f"{key_prefix}news", use_container_width=True):
            _trigger_analysis("news analiza za", pair, process_command_func)


def _trigger_analysis(command_prefix: str, pair: str, process_func) -> None:
    """Helper to trigger analysis and update chat."""
    pair_formatted = pair.replace("_", "/")
    cmd = f"{command_prefix} {pair_formatted}"

    if process_func and "chat_messages" in st.session_state:
        st.session_state.chat_messages.append({"role": "user", "content": cmd})
        response = process_func(cmd)
        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        st.rerun()


def get_available_pairs() -> list[str]:
    """Get list of available trading pairs including BTC."""
    return ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "BTC_USD"]
