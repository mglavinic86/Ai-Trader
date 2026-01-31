"""
Global CSS styles and theme constants for AI Trader dashboard.

Provides centralized styling to ensure consistency across all pages.
"""

import streamlit as st


# ===================
# Theme Constants
# ===================

THEME = {
    # Background colors
    "bg_primary": "#0e1117",
    "bg_secondary": "#1a1d24",
    "bg_card": "#1e2530",

    # Border colors
    "border_default": "#2d3748",
    "border_active": "#374151",

    # Status colors
    "success": "#10b981",
    "error": "#ef4444",
    "warning": "#f59e0b",
    "info": "#3b82f6",

    # Trading colors
    "profit": "#10b981",
    "loss": "#ef4444",
    "neutral": "#6b7280",

    # Accent colors
    "primary": "#2563eb",
    "secondary": "#4b5563",

    # Text colors
    "text_primary": "#e5e7eb",
    "text_secondary": "#9ca3af",
    "text_muted": "#6b7280",
}


# ===================
# CSS Styles
# ===================

GLOBAL_CSS = f"""
<style>
    /* Dark theme overrides */
    .stApp {{
        background-color: {THEME['bg_primary']};
    }}

    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background-color: {THEME['bg_secondary']};
    }}

    /* Metric cards */
    [data-testid="stMetric"] {{
        background-color: {THEME['bg_card']};
        padding: 15px;
        border-radius: 10px;
        border: 1px solid {THEME['border_default']};
    }}

    /* Success/Error colors */
    .profit {{ color: {THEME['profit']} !important; }}
    .loss {{ color: {THEME['loss']} !important; }}

    /* Connection status badges */
    .status-connected {{
        background-color: {THEME['success']};
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }}

    .status-disconnected {{
        background-color: {THEME['error']};
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }}

    /* Chat messages */
    .chat-user {{
        background-color: {THEME['primary']};
        color: white;
        padding: 10px 15px;
        border-radius: 15px 15px 5px 15px;
        margin: 5px 0;
    }}

    .chat-assistant {{
        background-color: {THEME['bg_card']};
        color: {THEME['text_primary']};
        padding: 10px 15px;
        border-radius: 15px 15px 15px 5px;
        margin: 5px 0;
        border: 1px solid {THEME['border_active']};
    }}

    /* Analysis cards */
    .analysis-card {{
        background-color: {THEME['bg_card']};
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid {THEME['info']};
        margin: 10px 0;
    }}

    /* Confidence meter */
    .confidence-high {{ border-left-color: {THEME['success']}; }}
    .confidence-medium {{ border-left-color: {THEME['warning']}; }}
    .confidence-low {{ border-left-color: {THEME['error']}; }}

    /* Button styling */
    .stButton > button {{
        border-radius: 8px;
        font-weight: 500;
    }}

    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* Table styling */
    .dataframe {{
        background-color: {THEME['bg_card']} !important;
    }}
</style>
"""


# ===================
# Utility Functions
# ===================

def inject_global_styles():
    """Inject global CSS styles into the current page."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def get_status_badge_html(connected: bool) -> str:
    """
    Get HTML for a connection status badge.

    Args:
        connected: Whether the connection is active

    Returns:
        HTML string for the status badge
    """
    if connected:
        return '<span class="status-connected">CONNECTED</span>'
    else:
        return '<span class="status-disconnected">DISCONNECTED</span>'


def get_pnl_color(pnl: float) -> str:
    """
    Get the appropriate color for P/L display.

    Args:
        pnl: Profit/loss value

    Returns:
        Color name for Streamlit markdown
    """
    if pnl > 0:
        return "green"
    elif pnl < 0:
        return "red"
    else:
        return "gray"


def get_pnl_class(pnl: float) -> str:
    """
    Get the CSS class for P/L display.

    Args:
        pnl: Profit/loss value

    Returns:
        CSS class name
    """
    return "profit" if pnl >= 0 else "loss"


def card_style(border_color: str = None) -> str:
    """
    Generate inline style for a card element.

    Args:
        border_color: Optional left border color

    Returns:
        CSS style string
    """
    style = f"background: {THEME['bg_card']}; padding: 20px; border-radius: 10px;"
    if border_color:
        style += f" border-left: 4px solid {border_color};"
    return style


def get_confidence_color(confidence: int) -> str:
    """
    Get color based on confidence score.

    Args:
        confidence: Confidence score (0-100)

    Returns:
        Color name for Streamlit
    """
    if confidence >= 70:
        return "green"
    elif confidence >= 50:
        return "orange"
    else:
        return "red"


def get_confidence_class(confidence: int) -> str:
    """
    Get CSS class based on confidence score.

    Args:
        confidence: Confidence score (0-100)

    Returns:
        CSS class name
    """
    if confidence >= 70:
        return "confidence-high"
    elif confidence >= 50:
        return "confidence-medium"
    else:
        return "confidence-low"
