"""
Suggested Actions component for AI Trader dashboard.

Provides intelligent, context-aware action recommendations based on
current account state, positions, and market conditions.
"""

import streamlit as st
from typing import List, Optional
from datetime import datetime, time
from dataclasses import dataclass

from components.tooltips import ICONS


# =============================================================================
# ACTION DATA STRUCTURES
# =============================================================================

@dataclass
class SuggestedAction:
    """Represents a suggested action for the user."""
    id: str
    title: str
    description: str
    priority: str  # "high", "medium", "low"
    icon: str
    action_label: str
    page_link: Optional[str] = None
    category: str = "general"  # "opportunity", "warning", "alert", "info"


# =============================================================================
# MARKET HOURS CHECK
# =============================================================================

def is_forex_market_open() -> bool:
    """
    Check if forex market is currently open.

    Forex market is open 24/5 (Sunday 5 PM EST to Friday 5 PM EST).
    Returns True if within trading hours.
    """
    now = datetime.now()
    weekday = now.weekday()

    # Market closed on Saturday (5) and Sunday before 5 PM (6)
    if weekday == 5:  # Saturday
        return False
    if weekday == 6:  # Sunday - typically opens around 5 PM EST
        return now.hour >= 17

    # Friday closes around 5 PM EST
    if weekday == 4 and now.hour >= 17:
        return False

    return True


def get_market_session() -> str:
    """
    Get current market session name.

    Returns:
        Session name: "Asian", "European", "American", or "Closed"
    """
    now = datetime.now()
    hour = now.hour

    # Simplified session times (adjust based on your timezone)
    if 0 <= hour < 8:
        return "Asian"
    elif 8 <= hour < 14:
        return "European"
    elif 14 <= hour < 22:
        return "American"
    else:
        return "Asian"


# =============================================================================
# ACTION GENERATORS
# =============================================================================

def generate_actions(
    account: dict,
    positions: list,
    stats: dict,
    daily_pnl: float = 0,
    config: dict = None
) -> List[SuggestedAction]:
    """
    Generate suggested actions based on current state.

    Args:
        account: Account data from MT5
        positions: List of open positions
        stats: Performance statistics
        daily_pnl: Today's P/L
        config: Configuration settings

    Returns:
        List of SuggestedAction objects, sorted by priority
    """
    actions = []
    config = config or {}

    max_positions = config.get("max_positions", 3)
    max_daily_dd = config.get("max_daily_drawdown", 0.03)

    balance = account.get("balance", 0)
    equity = account.get("nav", balance)
    num_positions = len(positions)

    # Calculate daily drawdown
    daily_dd_pct = (daily_pnl / balance * 100) if balance > 0 else 0

    # ===================
    # ALERTS (Highest Priority)
    # ===================

    # Daily drawdown alert
    if daily_dd_pct < -(max_daily_dd * 100 * 0.8):  # 80% of limit
        actions.append(SuggestedAction(
            id="drawdown_alert",
            title="Drawdown Warning",
            description=f"Today's loss ({daily_dd_pct:.1f}%) is approaching the {max_daily_dd*100:.0f}% daily limit. Consider reducing exposure.",
            priority="high",
            icon=ICONS["alert"],
            action_label="View Positions",
            page_link="pages/4_Positions.py",
            category="alert"
        ))

    # Margin level warning
    margin_level = (equity / account.get("margin_used", 1) * 100) if account.get("margin_used", 0) > 0 else 9999
    if margin_level < 200:
        actions.append(SuggestedAction(
            id="margin_warning",
            title="Low Margin Level",
            description=f"Margin level at {margin_level:.0f}%. Risk of margin call if it falls below 100%.",
            priority="high",
            icon=ICONS["warning"],
            action_label="Manage Risk",
            page_link="pages/4_Positions.py",
            category="alert"
        ))

    # ===================
    # WARNINGS (Medium Priority)
    # ===================

    # Position has significant unrealized loss
    for pos in positions:
        pl = pos.get("unrealized_pl", 0)
        if pl < -100:  # More than $100 loss
            pair = pos.get("instrument", "").replace("_", "/")
            actions.append(SuggestedAction(
                id=f"losing_position_{pos.get('ticket', 0)}",
                title=f"Review {pair} Position",
                description=f"Position has unrealized loss of ${abs(pl):.2f}. Check if the trade thesis is still valid.",
                priority="medium",
                icon=ICONS["warning"],
                action_label="View Position",
                page_link="pages/4_Positions.py",
                category="warning"
            ))
            break  # Only show one losing position warning

    # Position has significant unrealized profit
    for pos in positions:
        pl = pos.get("unrealized_pl", 0)
        entry = pos.get("price_open", 0)
        if pl > 100:  # More than $100 profit
            pair = pos.get("instrument", "").replace("_", "/")
            actions.append(SuggestedAction(
                id=f"profit_position_{pos.get('ticket', 0)}",
                title=f"Consider Taking Profits on {pair}",
                description=f"Position has unrealized profit of +${pl:.2f}. Consider locking in some gains.",
                priority="medium",
                icon=ICONS["money"],
                action_label="Manage Position",
                page_link="pages/4_Positions.py",
                category="opportunity"
            ))
            break  # Only show one

    # Win rate declining
    win_rate = stats.get("win_rate", 50)
    if win_rate < 45:
        actions.append(SuggestedAction(
            id="declining_winrate",
            title="Review Trading Performance",
            description=f"Win rate is at {win_rate:.0f}%. Review recent trades to identify patterns in losses.",
            priority="medium",
            icon=ICONS["chart"],
            action_label="View History",
            page_link="pages/5_History.py",
            category="warning"
        ))

    # ===================
    # OPPORTUNITIES (Low Priority)
    # ===================

    # No positions and market is open
    if num_positions == 0 and is_forex_market_open():
        session = get_market_session()
        actions.append(SuggestedAction(
            id="analyze_pairs",
            title=f"Look for Opportunities ({session} Session)",
            description="You have no open positions. Analyze major pairs to find trade setups.",
            priority="low",
            icon=ICONS["chart"],
            action_label="Analyze Markets",
            page_link="pages/2_Chat.py",
            category="opportunity"
        ))

    # Room for more positions
    if 0 < num_positions < max_positions and is_forex_market_open():
        actions.append(SuggestedAction(
            id="more_positions",
            title=f"Room for {max_positions - num_positions} More Position(s)",
            description=f"You have {num_positions}/{max_positions} positions. You can diversify with more trades.",
            priority="low",
            icon=ICONS["trade"],
            action_label="Find Trades",
            page_link="pages/3_Analysis.py",
            category="info"
        ))

    # No trades recently (need to check last trade date)
    total_trades = stats.get("total_trades", 0)
    if total_trades == 0 and num_positions == 0:
        actions.append(SuggestedAction(
            id="first_trade",
            title="Ready to Start Trading?",
            description="No trades recorded yet. Start by analyzing a currency pair to get AI recommendations.",
            priority="low",
            icon=ICONS["info"],
            action_label="Get Started",
            page_link="pages/2_Chat.py",
            category="info"
        ))

    # Position limit reached
    if num_positions >= max_positions:
        actions.append(SuggestedAction(
            id="position_limit",
            title="Position Limit Reached",
            description=f"You have {num_positions}/{max_positions} positions. Close a trade to open new ones.",
            priority="low",
            icon=ICONS["info"],
            action_label="Manage Positions",
            page_link="pages/4_Positions.py",
            category="info"
        ))

    # Market closed
    if not is_forex_market_open():
        actions.append(SuggestedAction(
            id="market_closed",
            title="Forex Market is Closed",
            description="The market is currently closed (weekend). Use this time to review your strategy and past trades.",
            priority="low",
            icon=ICONS["info"],
            action_label="Review History",
            page_link="pages/5_History.py",
            category="info"
        ))

    # Backtest suggestion
    if total_trades < 10:
        actions.append(SuggestedAction(
            id="backtest_suggestion",
            title="Test Your Strategy",
            description="Run a backtest to see how the AI strategy performs on historical data.",
            priority="low",
            icon=ICONS["chart"],
            action_label="Run Backtest",
            page_link="pages/8_Backtest.py",
            category="info"
        ))

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    actions.sort(key=lambda x: priority_order.get(x.priority, 2))

    return actions


# =============================================================================
# RENDER FUNCTIONS
# =============================================================================

def get_card_color(category: str) -> str:
    """Get border color based on action category."""
    colors = {
        "alert": "#ef4444",      # Red
        "warning": "#f59e0b",    # Orange
        "opportunity": "#10b981", # Green
        "info": "#3b82f6",       # Blue
    }
    return colors.get(category, colors["info"])


def render_action_card(action: SuggestedAction):
    """
    Render a single action card.

    Args:
        action: SuggestedAction to render
    """
    color = get_card_color(action.category)

    # Card container
    st.markdown(f"""
    <div style="
        background-color: #1e2530;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid {color};
        margin-bottom: 10px;
    ">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 16px; color: {color};">{action.icon}</span>
            <strong style="color: #e5e7eb;">{action.title}</strong>
        </div>
        <p style="color: #9ca3af; margin: 10px 0 0 0; font-size: 14px;">
            {action.description}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Action button
    if action.page_link:
        if st.button(action.action_label, key=f"action_{action.id}", use_container_width=True):
            st.switch_page(action.page_link)


def render_suggested_actions(
    account: dict,
    positions: list,
    stats: dict,
    daily_pnl: float = 0,
    config: dict = None,
    max_actions: int = 4
):
    """
    Render the Suggested Actions section.

    Args:
        account: Account data
        positions: Open positions
        stats: Performance stats
        daily_pnl: Today's P/L
        config: Configuration dict
        max_actions: Maximum number of actions to display
    """
    st.subheader(f"{ICONS['info']} Suggested Actions")

    actions = generate_actions(
        account=account,
        positions=positions,
        stats=stats,
        daily_pnl=daily_pnl,
        config=config
    )

    if not actions:
        st.info("No suggested actions at this time. Your account looks healthy!")
        return

    # Limit to max_actions
    display_actions = actions[:max_actions]

    # Create columns for cards
    if len(display_actions) == 1:
        render_action_card(display_actions[0])
    elif len(display_actions) == 2:
        col1, col2 = st.columns(2)
        with col1:
            render_action_card(display_actions[0])
        with col2:
            render_action_card(display_actions[1])
    else:
        # Two rows of two
        col1, col2 = st.columns(2)
        for i, action in enumerate(display_actions):
            with col1 if i % 2 == 0 else col2:
                render_action_card(action)

    # Show more if there are hidden actions
    if len(actions) > max_actions:
        with st.expander(f"Show {len(actions) - max_actions} more suggestions"):
            for action in actions[max_actions:]:
                render_action_card(action)


def render_quick_action_bar(positions: list, num_positions: int, max_positions: int):
    """
    Render a compact action bar for the sidebar.

    Args:
        positions: Open positions list
        num_positions: Number of open positions
        max_positions: Maximum allowed positions
    """
    # Quick status
    if not is_forex_market_open():
        st.caption(f"{ICONS['info']} Market Closed")
    else:
        session = get_market_session()
        st.caption(f"{ICONS['success']} {session} Session Active")

    # Position slots
    st.caption(f"{ICONS['trade']} Positions: {num_positions}/{max_positions}")

    # Alert if any position in significant loss
    for pos in positions:
        if pos.get("unrealized_pl", 0) < -50:
            st.caption(f"{ICONS['warning']} Position needs attention")
            break
