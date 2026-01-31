"""
Reusable UI components for AI Trader dashboard.
"""

from components.sidebar import render_sidebar_account
from components.analysis_card import render_analysis_card, render_confidence_meter
from components.mt5_session import get_client, is_connected, reset_connection, get_client_with_retry
from components.styles import (
    THEME,
    GLOBAL_CSS,
    inject_global_styles,
    get_status_badge_html,
    get_pnl_color,
    get_pnl_class,
    card_style,
    get_confidence_color,
    get_confidence_class,
)
from components.empty_states import (
    render_no_positions,
    render_no_trades,
    render_no_connection,
    render_no_data,
    render_loading_error,
    render_empty_table,
    render_coming_soon,
    render_no_analysis,
    render_minimal_status,
)
from components.tooltips import (
    ICONS,
    METRIC_TOOLTIPS,
    metric_with_tooltip,
    tooltip_text,
    get_tooltip,
    simple_explanation_section,
    render_explanation_box,
    render_metric_explanation,
    get_icon,
)
from components.suggested_actions import (
    render_suggested_actions,
    render_quick_action_bar,
    generate_actions,
    is_forex_market_open,
    get_market_session,
)
from components.status_bar import (
    render_status_bar,
    render_compact_status_bar,
    get_status_bar_data,
    inject_status_bar_to_session,
    render_status_bar_from_session,
)
from components.position_health import (
    HealthStatus,
    get_position_health,
    render_health_indicator,
    render_health_badge,
    render_position_with_health,
    get_health_summary,
    render_health_summary,
    get_portfolio_health_score,
    render_portfolio_health_meter,
)
from components.onboarding import (
    render_welcome_wizard,
    render_welcome_wizard_sidebar_trigger,
    has_completed_onboarding,
    mark_onboarding_complete,
    reset_onboarding,
    should_show_wizard,
)
from components.notifications import (
    Notification,
    check_notifications,
    render_notifications,
    render_notifications_compact,
    render_notification_badge,
    get_notification_count,
    has_critical_notifications,
    clear_dismissed_notifications,
)
from components.help_resources import (
    render_help_button,
    render_help_sidebar,
    render_context_help,
    render_inline_help,
    render_first_time_hints,
    render_page_intro,
    get_field_help,
)

__all__ = [
    # Sidebar
    "render_sidebar_account",
    # Analysis cards
    "render_analysis_card",
    "render_confidence_meter",
    # MT5 Session
    "get_client",
    "is_connected",
    "reset_connection",
    "get_client_with_retry",
    # Styles
    "THEME",
    "GLOBAL_CSS",
    "inject_global_styles",
    "get_status_badge_html",
    "get_pnl_color",
    "get_pnl_class",
    "card_style",
    "get_confidence_color",
    "get_confidence_class",
    # Empty states
    "render_no_positions",
    "render_no_trades",
    "render_no_connection",
    "render_no_data",
    "render_loading_error",
    "render_empty_table",
    "render_coming_soon",
    "render_no_analysis",
    "render_minimal_status",
    # Tooltips
    "ICONS",
    "METRIC_TOOLTIPS",
    "metric_with_tooltip",
    "tooltip_text",
    "get_tooltip",
    "simple_explanation_section",
    "render_explanation_box",
    "render_metric_explanation",
    "get_icon",
    # Suggested actions
    "render_suggested_actions",
    "render_quick_action_bar",
    "generate_actions",
    "is_forex_market_open",
    "get_market_session",
    # Status bar
    "render_status_bar",
    "render_compact_status_bar",
    "get_status_bar_data",
    "inject_status_bar_to_session",
    "render_status_bar_from_session",
    # Position health
    "HealthStatus",
    "get_position_health",
    "render_health_indicator",
    "render_health_badge",
    "render_position_with_health",
    "get_health_summary",
    "render_health_summary",
    "get_portfolio_health_score",
    "render_portfolio_health_meter",
    # Onboarding
    "render_welcome_wizard",
    "render_welcome_wizard_sidebar_trigger",
    "has_completed_onboarding",
    "mark_onboarding_complete",
    "reset_onboarding",
    "should_show_wizard",
    # Notifications
    "Notification",
    "check_notifications",
    "render_notifications",
    "render_notifications_compact",
    "render_notification_badge",
    "get_notification_count",
    "has_critical_notifications",
    "clear_dismissed_notifications",
    # Help resources
    "render_help_button",
    "render_help_sidebar",
    "render_context_help",
    "render_inline_help",
    "render_first_time_hints",
    "render_page_intro",
    "get_field_help",
]
