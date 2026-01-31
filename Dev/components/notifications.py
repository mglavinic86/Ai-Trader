"""
Notification System component for AI Trader dashboard.

Provides smart notifications based on account state, positions, and market conditions.
Displays alerts for:
- Drawdown approaching limit
- Positions in significant loss
- Low margin level
- Market closed status
"""

import streamlit as st
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from components.tooltips import ICONS
from components.suggested_actions import is_forex_market_open, get_market_session

# =============================================================================
# NOTIFICATION DATA STRUCTURES
# =============================================================================

@dataclass
class Notification:
    """Represents a notification to display to the user."""
    id: str
    type: str  # "info", "warning", "error", "success"
    title: str
    message: str
    dismissible: bool = True
    priority: int = 0  # Higher = more important


# =============================================================================
# NOTIFICATION GENERATORS
# =============================================================================

def check_notifications(
    account: dict,
    positions: list,
    config: dict = None
) -> List[Notification]:
    """
    Check current state and generate notifications.

    Args:
        account: Account data from MT5
        positions: List of open positions
        config: Configuration dict with limits

    Returns:
        List of Notification objects, sorted by priority
    """
    notifications = []
    config = config or {}

    balance = account.get("balance", 0)
    equity = account.get("nav", balance)
    margin_used = account.get("margin_used", 0)
    unrealized_pl = account.get("unrealized_pl", 0)

    max_daily_dd = config.get("max_daily_drawdown", 0.03)
    max_positions = config.get("max_positions", 3)

    # Get daily P/L if available
    daily_pnl = config.get("daily_pnl", unrealized_pl)

    # ===================
    # ERROR LEVEL (Critical)
    # ===================

    # Margin level critically low
    if margin_used > 0:
        margin_level = (equity / margin_used) * 100
        if margin_level < 100:
            notifications.append(Notification(
                id="margin_critical",
                type="error",
                title="MARGIN CALL RISK",
                message=f"Margin level at {margin_level:.0f}%. Close positions immediately to avoid liquidation.",
                dismissible=False,
                priority=100
            ))
        elif margin_level < 150:
            notifications.append(Notification(
                id="margin_danger",
                type="error",
                title="Margin Level Dangerously Low",
                message=f"Margin level at {margin_level:.0f}%. Consider reducing position sizes.",
                dismissible=True,
                priority=90
            ))

    # Daily drawdown exceeded
    if balance > 0:
        daily_dd_pct = (daily_pnl / balance) * 100
        if daily_dd_pct <= -(max_daily_dd * 100):
            notifications.append(Notification(
                id="drawdown_exceeded",
                type="error",
                title="Daily Loss Limit Reached",
                message=f"Today's loss ({daily_dd_pct:.1f}%) has reached the {max_daily_dd*100:.0f}% limit. Trading should pause.",
                dismissible=False,
                priority=95
            ))

    # ===================
    # WARNING LEVEL
    # ===================

    # Drawdown approaching limit (80% of max)
    if balance > 0:
        daily_dd_pct = (daily_pnl / balance) * 100
        warning_threshold = -(max_daily_dd * 100 * 0.8)
        if warning_threshold < daily_dd_pct <= -(max_daily_dd * 100 * 0.5):
            pass  # Not yet at warning level
        elif daily_dd_pct <= warning_threshold and daily_dd_pct > -(max_daily_dd * 100):
            notifications.append(Notification(
                id="drawdown_warning",
                type="warning",
                title="Approaching Daily Loss Limit",
                message=f"Today's loss is {abs(daily_dd_pct):.1f}%. Limit is {max_daily_dd*100:.0f}%. Trade carefully.",
                dismissible=True,
                priority=70
            ))

    # Margin level warning
    if margin_used > 0:
        margin_level = (equity / margin_used) * 100
        if 150 <= margin_level < 200:
            notifications.append(Notification(
                id="margin_warning",
                type="warning",
                title="Low Margin Level",
                message=f"Margin level at {margin_level:.0f}%. Avoid opening new positions.",
                dismissible=True,
                priority=65
            ))

    # Position in significant loss
    for pos in positions:
        pl = pos.get("unrealized_pl", 0)
        if pl < -200:  # More than $200 loss
            pair = pos.get("instrument", "").replace("_", "/")
            notifications.append(Notification(
                id=f"position_loss_{pos.get('ticket', 0)}",
                type="warning",
                title=f"{pair} Position in Loss",
                message=f"Position has {pl:.2f} unrealized loss. Review or consider closing.",
                dismissible=True,
                priority=60
            ))
            break  # Only show one

    # Position limit reached
    if len(positions) >= max_positions:
        notifications.append(Notification(
            id="position_limit_reached",
            type="warning",
            title="Position Limit Reached",
            message=f"You have {len(positions)}/{max_positions} positions. Close one to open new trades.",
            dismissible=True,
            priority=40
        ))

    # ===================
    # INFO LEVEL
    # ===================

    # Market closed
    if not is_forex_market_open():
        now = datetime.now()
        weekday = now.weekday()

        if weekday == 5:  # Saturday
            reopen = "Sunday evening"
        elif weekday == 6:  # Sunday
            if now.hour < 17:
                reopen = "later today (around 5 PM)"
            else:
                reopen = "now (market is opening)"
        else:
            reopen = "unknown"

        notifications.append(Notification(
            id="market_closed",
            type="info",
            title="Forex Market Closed",
            message=f"The market is closed for the weekend. It reopens {reopen}.",
            dismissible=True,
            priority=10
        ))

    # ===================
    # SUCCESS LEVEL
    # ===================

    # Position in significant profit
    for pos in positions:
        pl = pos.get("unrealized_pl", 0)
        if pl > 200:  # More than $200 profit
            pair = pos.get("instrument", "").replace("_", "/")
            notifications.append(Notification(
                id=f"position_profit_{pos.get('ticket', 0)}",
                type="success",
                title=f"{pair} in Profit",
                message=f"Position has +{pl:.2f} profit. Consider taking partial profits or moving SL to breakeven.",
                dismissible=True,
                priority=30
            ))
            break  # Only show one

    # Good daily performance
    if balance > 0:
        daily_dd_pct = (daily_pnl / balance) * 100
        if daily_dd_pct >= 1:  # More than 1% profit
            notifications.append(Notification(
                id="good_day",
                type="success",
                title="Good Trading Day",
                message=f"You're up {daily_dd_pct:.1f}% today. Nice work!",
                dismissible=True,
                priority=20
            ))

    # Sort by priority (highest first)
    notifications.sort(key=lambda x: x.priority, reverse=True)

    return notifications


# =============================================================================
# RENDER FUNCTIONS
# =============================================================================

def get_notification_style(notif_type: str) -> tuple:
    """
    Get styling for notification type.

    Args:
        notif_type: "info", "warning", "error", "success"

    Returns:
        Tuple of (background_color, border_color, icon)
    """
    styles = {
        "info": ("#1e3a5f", "#3b82f6", ICONS["info"]),
        "warning": ("#3d2f00", "#f59e0b", ICONS["warning"]),
        "error": ("#4a1515", "#ef4444", ICONS["error"]),
        "success": ("#1a3a1a", "#10b981", ICONS["success"]),
    }
    return styles.get(notif_type, styles["info"])


def render_notification(notification: Notification, key_suffix: str = ""):
    """
    Render a single notification.

    Args:
        notification: Notification to render
        key_suffix: Suffix for unique keys
    """
    bg_color, border_color, icon = get_notification_style(notification.type)

    # Check if dismissed in session state
    dismiss_key = f"dismissed_{notification.id}{key_suffix}"
    if st.session_state.get(dismiss_key, False):
        return

    # Container
    col1, col2 = st.columns([20, 1])

    with col1:
        st.markdown(f"""
        <div style="
            background-color: {bg_color};
            border-left: 4px solid {border_color};
            padding: 12px 16px;
            border-radius: 4px;
            margin-bottom: 8px;
        ">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="color: {border_color}; font-weight: bold;">{icon}</span>
                <strong style="color: #e5e7eb;">{notification.title}</strong>
            </div>
            <p style="color: #9ca3af; margin: 8px 0 0 0; font-size: 14px;">
                {notification.message}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        if notification.dismissible:
            if st.button("x", key=f"dismiss_{notification.id}{key_suffix}"):
                st.session_state[dismiss_key] = True
                st.rerun()


def render_notifications(
    notifications: List[Notification],
    max_display: int = 3,
    key_suffix: str = ""
):
    """
    Render all notifications at the top of the page.

    Args:
        notifications: List of notifications to render
        max_display: Maximum number to show before collapsing
        key_suffix: Suffix for unique keys (use page name)
    """
    if not notifications:
        return

    # Filter out dismissed notifications
    visible = []
    for notif in notifications:
        dismiss_key = f"dismissed_{notif.id}{key_suffix}"
        if not st.session_state.get(dismiss_key, False):
            visible.append(notif)

    if not visible:
        return

    # Show first max_display notifications
    for notif in visible[:max_display]:
        render_notification(notif, key_suffix)

    # Show expander for remaining
    if len(visible) > max_display:
        remaining = len(visible) - max_display
        with st.expander(f"Show {remaining} more notification(s)"):
            for notif in visible[max_display:]:
                render_notification(notif, key_suffix)


def render_notifications_compact(notifications: List[Notification]):
    """
    Render a compact notification bar (for sidebar).

    Args:
        notifications: List of notifications
    """
    if not notifications:
        return

    # Count by type
    counts = {"error": 0, "warning": 0, "info": 0, "success": 0}
    for notif in notifications:
        counts[notif.type] = counts.get(notif.type, 0) + 1

    # Compact display
    parts = []
    if counts["error"] > 0:
        parts.append(f"{ICONS['error']} {counts['error']}")
    if counts["warning"] > 0:
        parts.append(f"{ICONS['warning']} {counts['warning']}")
    if counts["info"] > 0:
        parts.append(f"{ICONS['info']} {counts['info']}")

    if parts:
        st.sidebar.caption("Alerts: " + " | ".join(parts))


def clear_dismissed_notifications(key_suffix: str = ""):
    """
    Clear all dismissed notifications for a page.

    Args:
        key_suffix: Page-specific suffix used when rendering
    """
    keys_to_remove = []
    for key in st.session_state:
        if key.startswith(f"dismissed_") and key_suffix in key:
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del st.session_state[key]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_notification_count(notifications: List[Notification]) -> dict:
    """
    Get count of notifications by type.

    Args:
        notifications: List of notifications

    Returns:
        Dict with counts per type
    """
    counts = {"error": 0, "warning": 0, "info": 0, "success": 0, "total": 0}
    for notif in notifications:
        counts[notif.type] = counts.get(notif.type, 0) + 1
        counts["total"] += 1
    return counts


def has_critical_notifications(notifications: List[Notification]) -> bool:
    """
    Check if there are any critical (error) notifications.

    Args:
        notifications: List of notifications

    Returns:
        True if there are error-level notifications
    """
    return any(n.type == "error" for n in notifications)


def render_notification_badge(notifications: List[Notification]):
    """
    Render a badge showing notification counts (for nav).

    Args:
        notifications: List of notifications
    """
    counts = get_notification_count(notifications)

    if counts["error"] > 0:
        st.markdown(f'<span style="background: #ef4444; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{counts["error"]} Alert(s)</span>', unsafe_allow_html=True)
    elif counts["warning"] > 0:
        st.markdown(f'<span style="background: #f59e0b; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{counts["warning"]} Warning(s)</span>', unsafe_allow_html=True)
