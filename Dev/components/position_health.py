"""
Position Health Indicators for AI Trader dashboard.

Calculates and displays the "health" of each position based on:
- Current profit/loss
- Distance to stop loss
- Risk level
"""

import streamlit as st
from typing import Dict, Any, Optional, Tuple
from enum import Enum


class HealthStatus(Enum):
    """Position health status levels."""
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    NEUTRAL = "NEUTRAL"
    WARNING = "WARNING"
    DANGER = "DANGER"


# Health status configuration
HEALTH_CONFIG = {
    HealthStatus.EXCELLENT: {
        "color": "green",
        "icon": "[++]",
        "label": "EXCELLENT",
        "description": "In profit, far from stop loss"
    },
    HealthStatus.GOOD: {
        "color": "green",
        "icon": "[+]",
        "label": "GOOD",
        "description": "In small profit"
    },
    HealthStatus.NEUTRAL: {
        "color": "gray",
        "icon": "[=]",
        "label": "NEUTRAL",
        "description": "Around entry price"
    },
    HealthStatus.WARNING: {
        "color": "orange",
        "icon": "[!]",
        "label": "WARNING",
        "description": "Close to stop loss"
    },
    HealthStatus.DANGER: {
        "color": "red",
        "icon": "[!!]",
        "label": "DANGER",
        "description": "Very close to stop loss"
    }
}


def calculate_distance_to_sl_pct(
    current_price: float,
    entry_price: float,
    stop_loss: float,
    direction: str
) -> float:
    """
    Calculate distance to stop loss as percentage of the move.

    Returns:
        Percentage where 0% = at SL, 100% = at entry, >100% = in profit territory
    """
    if stop_loss <= 0:
        return 100.0  # No SL set, consider neutral

    if direction.upper() == "LONG" or direction.upper() == "BUY":
        # For long: SL is below entry
        total_distance = entry_price - stop_loss
        if total_distance <= 0:
            return 100.0
        current_distance = current_price - stop_loss
        return (current_distance / total_distance) * 100
    else:
        # For short: SL is above entry
        total_distance = stop_loss - entry_price
        if total_distance <= 0:
            return 100.0
        current_distance = stop_loss - current_price
        return (current_distance / total_distance) * 100


def calculate_pnl_pips(
    current_price: float,
    entry_price: float,
    direction: str,
    instrument: str
) -> float:
    """Calculate P&L in pips."""
    pip_size = 0.01 if "JPY" in instrument.upper() else 0.0001

    if direction.upper() == "LONG" or direction.upper() == "BUY":
        return (current_price - entry_price) / pip_size
    else:
        return (entry_price - current_price) / pip_size


def get_position_health(
    position: Dict[str, Any],
    instrument: str = ""
) -> Tuple[HealthStatus, Dict[str, Any]]:
    """
    Calculate the health status of a position.

    Args:
        position: Position dict with keys:
            - price_open (entry price)
            - price_current (current price)
            - sl (stop loss)
            - direction ("LONG"/"SHORT" or "BUY"/"SELL")
            - unrealized_pl (current P/L)
        instrument: Trading instrument (for pip calculation)

    Returns:
        Tuple of (HealthStatus, details dict)
    """
    entry_price = position.get("price_open", 0)
    current_price = position.get("price_current", 0)
    stop_loss = position.get("sl", 0)
    direction = position.get("direction", "LONG")
    unrealized_pl = position.get("unrealized_pl", 0)
    instrument = instrument or position.get("instrument", "")

    # Calculate metrics
    distance_to_sl = calculate_distance_to_sl_pct(
        current_price, entry_price, stop_loss, direction
    )
    pnl_pips = calculate_pnl_pips(current_price, entry_price, direction, instrument)

    details = {
        "distance_to_sl_pct": distance_to_sl,
        "pnl_pips": pnl_pips,
        "unrealized_pl": unrealized_pl
    }

    # Determine health status
    # DANGER: Very close to SL (< 25% of distance remaining)
    if distance_to_sl < 25:
        return HealthStatus.DANGER, details

    # WARNING: Close to SL (25-50% of distance remaining)
    if distance_to_sl < 50:
        return HealthStatus.WARNING, details

    # NEUTRAL: Around entry (within 5 pips or 50-75% distance)
    if abs(pnl_pips) < 5:
        return HealthStatus.NEUTRAL, details

    # Check if in profit
    if unrealized_pl > 0 or pnl_pips > 0:
        # EXCELLENT: In good profit AND far from SL (> 100% = past entry)
        if distance_to_sl > 120 and pnl_pips > 20:
            return HealthStatus.EXCELLENT, details

        # GOOD: In profit
        return HealthStatus.GOOD, details

    # In loss but not near SL
    return HealthStatus.NEUTRAL, details


def render_health_indicator(
    health: HealthStatus,
    compact: bool = False
) -> None:
    """
    Render a health status indicator.

    Args:
        health: HealthStatus enum value
        compact: If True, show only icon
    """
    config = HEALTH_CONFIG[health]

    if compact:
        st.markdown(f":{config['color']}[{config['icon']}]")
    else:
        st.markdown(f":{config['color']}[{config['icon']} {config['label']}]")


def render_health_badge(
    health: HealthStatus,
    show_description: bool = False
) -> None:
    """
    Render a styled health badge.

    Args:
        health: HealthStatus enum value
        show_description: Whether to show description text
    """
    config = HEALTH_CONFIG[health]

    col1, col2 = st.columns([1, 4])

    with col1:
        st.markdown(f":{config['color']}[**{config['label']}**]")

    if show_description:
        with col2:
            st.caption(config['description'])


def render_position_with_health(
    position: Dict[str, Any],
    show_details: bool = True
) -> None:
    """
    Render a position with its health indicator.

    Args:
        position: Position dictionary
        show_details: Whether to show detailed metrics
    """
    instrument = position.get("instrument", "").replace("_", "/")
    direction = position.get("direction", "LONG")
    unrealized_pl = position.get("unrealized_pl", 0)

    # Calculate health
    health, details = get_position_health(position)
    config = HEALTH_CONFIG[health]

    # Header with health indicator
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        pnl_color = "green" if unrealized_pl >= 0 else "red"
        st.markdown(f"**{instrument}** {direction} | :{pnl_color}[{unrealized_pl:+.2f}]")

    with col2:
        st.markdown(f":{config['color']}[{config['icon']}]")

    with col3:
        st.markdown(f":{config['color']}[{config['label']}]")

    if show_details:
        # Progress bar showing distance to SL
        distance = details["distance_to_sl_pct"]
        progress_value = min(max(distance / 150, 0), 1.0)  # Normalize to 0-1

        st.progress(progress_value)
        st.caption(f"Distance to SL: {distance:.0f}% | P/L: {details['pnl_pips']:+.1f} pips")


def get_health_summary(positions: list) -> Dict[str, int]:
    """
    Get summary of position health across all positions.

    Args:
        positions: List of position dictionaries

    Returns:
        Dict with count of each health status
    """
    summary = {status.value: 0 for status in HealthStatus}

    for pos in positions:
        health, _ = get_position_health(pos)
        summary[health.value] += 1

    return summary


def render_health_summary(positions: list) -> None:
    """
    Render a summary of all position health statuses.

    Args:
        positions: List of position dictionaries
    """
    if not positions:
        st.info("No open positions")
        return

    summary = get_health_summary(positions)

    cols = st.columns(5)

    for i, status in enumerate(HealthStatus):
        config = HEALTH_CONFIG[status]
        count = summary[status.value]

        with cols[i]:
            if count > 0:
                st.markdown(f":{config['color']}[**{count}**] {config['label']}")
            else:
                st.caption(f"0 {config['label']}")


def get_portfolio_health_score(positions: list) -> Tuple[float, str]:
    """
    Calculate overall portfolio health score (0-100).

    Args:
        positions: List of position dictionaries

    Returns:
        Tuple of (score, description)
    """
    if not positions:
        return 100.0, "No positions"

    # Weight each health status
    weights = {
        HealthStatus.EXCELLENT: 100,
        HealthStatus.GOOD: 80,
        HealthStatus.NEUTRAL: 50,
        HealthStatus.WARNING: 25,
        HealthStatus.DANGER: 0
    }

    total_score = 0
    for pos in positions:
        health, _ = get_position_health(pos)
        total_score += weights[health]

    avg_score = total_score / len(positions)

    # Determine description
    if avg_score >= 80:
        description = "Excellent - All positions healthy"
    elif avg_score >= 60:
        description = "Good - Positions mostly healthy"
    elif avg_score >= 40:
        description = "Neutral - Mixed health"
    elif avg_score >= 20:
        description = "Warning - Some positions at risk"
    else:
        description = "Danger - Positions need attention"

    return avg_score, description


def render_portfolio_health_meter(positions: list) -> None:
    """
    Render a portfolio health meter.

    Args:
        positions: List of position dictionaries
    """
    score, description = get_portfolio_health_score(positions)

    # Determine color
    if score >= 80:
        color = "green"
    elif score >= 60:
        color = "green"
    elif score >= 40:
        color = "gray"
    elif score >= 20:
        color = "orange"
    else:
        color = "red"

    st.markdown(f"**Portfolio Health:** :{color}[{score:.0f}/100]")
    st.progress(score / 100)
    st.caption(description)
