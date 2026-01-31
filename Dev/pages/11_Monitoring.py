"""
AI Trader - Monitoring Page

System health monitoring, error tracking, and alert management.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.utils.config import config
from src.utils.monitoring import (
    ErrorTracker,
    AlertManager,
    AlertLevel,
    ErrorCategory,
    check_system_health
)
from components.tooltips import ICONS, metric_with_tooltip
from components.status_bar import render_status_bar, get_status_bar_data
from components.mt5_session import get_client, is_connected

st.set_page_config(page_title="Monitoring - AI Trader", page_icon="", layout="wide")


def render_health_status(health: dict):
    """Render system health status."""
    st.subheader(f"{ICONS['health']} System Health")

    # Overall status
    if health['healthy']:
        st.success(f"{ICONS['success']} System is healthy")
    else:
        st.error(f"{ICONS['error']} System has issues")

    # Component status
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status = ICONS['success'] if health['mt5_connected'] else ICONS['error']
        color = "green" if health['mt5_connected'] else "red"
        st.markdown(f"**MT5 Connection**")
        st.markdown(f":{color}[{status} {'Connected' if health['mt5_connected'] else 'Disconnected'}]")

    with col2:
        status = ICONS['success'] if health['database_ok'] else ICONS['error']
        color = "green" if health['database_ok'] else "red"
        st.markdown(f"**Database**")
        st.markdown(f":{color}[{status} {'OK' if health['database_ok'] else 'Error'}]")

    with col3:
        st.markdown(f"**Last Check**")
        try:
            check_time = datetime.fromisoformat(health['last_check'])
            st.markdown(f"{check_time.strftime('%H:%M:%S')}")
        except (ValueError, TypeError, KeyError):
            st.markdown(f"{health.get('last_check', '--:--:--')}")

    with col4:
        issue_count = len(health.get('issues', []))
        warning_count = len(health.get('warnings', []))
        st.markdown(f"**Issues**")
        if issue_count > 0:
            st.markdown(f":red[{issue_count} critical]")
        elif warning_count > 0:
            st.markdown(f":orange[{warning_count} warnings]")
        else:
            st.markdown(f":green[None]")

    # Show issues and warnings
    if health.get('issues'):
        st.markdown("**Critical Issues:**")
        for issue in health['issues']:
            st.error(f"{ICONS['error']} {issue}")

    if health.get('warnings'):
        st.markdown("**Warnings:**")
        for warning in health['warnings']:
            st.warning(f"{ICONS['warning']} {warning}")


def render_error_summary(tracker: ErrorTracker):
    """Render error statistics."""
    st.subheader(f"{ICONS['error']} Error Summary")

    summary = tracker.get_error_summary()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Errors", summary['total'])

    with col2:
        st.metric("Unresolved", summary['unresolved'])

    with col3:
        st.metric("Last 24h", summary['last_24h'])

    with col4:
        st.metric("Last Hour", summary['last_hour'])

    # Errors by category chart
    if summary['by_category']:
        st.markdown("**Errors by Category:**")

        categories = list(summary['by_category'].keys())
        counts = list(summary['by_category'].values())

        fig = px.bar(
            x=categories,
            y=counts,
            labels={'x': 'Category', 'y': 'Count'},
            color=counts,
            color_continuous_scale='Reds'
        )
        fig.update_layout(
            height=250,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        st.plotly_chart(fig, use_container_width=True)


def render_recent_errors(tracker: ErrorTracker):
    """Render recent errors table."""
    st.subheader(f"{ICONS['list']} Recent Errors")

    errors = tracker.get_recent_errors(hours=24)

    if not errors:
        st.info("No errors in the last 24 hours")
        return

    # Convert to dataframe
    df_data = []
    for e in reversed(errors):  # Most recent first
        try:
            timestamp = datetime.fromisoformat(e.timestamp)
            time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError, AttributeError):
            time_str = e.timestamp

        df_data.append({
            "Time": time_str,
            "Category": e.category,
            "Message": e.message[:100] + "..." if len(e.message) > 100 else e.message,
            "Resolved": ICONS['success'] if e.resolved else ICONS['pending'],
            "Timestamp": e.timestamp
        })

    df = pd.DataFrame(df_data)

    # Style function
    def highlight_unresolved(row):
        if row['Resolved'] == ICONS['pending']:
            return ['background-color: rgba(255,0,0,0.1)'] * len(row)
        return [''] * len(row)

    styled_df = df.drop(columns=['Timestamp']).style.apply(highlight_unresolved, axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Resolve buttons
    unresolved = [e for e in errors if not e.resolved]
    if unresolved:
        st.markdown("---")
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("Resolve All", type="secondary"):
                for e in unresolved:
                    tracker.resolve_error(e.timestamp)
                st.success(f"Resolved {len(unresolved)} errors")
                st.rerun()


def render_alerts(manager: AlertManager):
    """Render alerts section."""
    st.subheader(f"{ICONS['alert']} Alerts")

    alerts = manager.get_recent_alerts(hours=24)
    unacked = manager.get_unacknowledged()

    col1, col2 = st.columns([3, 1])

    with col1:
        if unacked:
            st.warning(f"{len(unacked)} unacknowledged alert(s)")
        else:
            st.success("All alerts acknowledged")

    with col2:
        if unacked:
            if st.button("Acknowledge All"):
                count = manager.acknowledge_all()
                st.success(f"Acknowledged {count} alerts")
                st.rerun()

    if not alerts:
        st.info("No alerts in the last 24 hours")
        return

    # Display alerts
    for alert in reversed(alerts):  # Most recent first
        try:
            timestamp = datetime.fromisoformat(alert.timestamp)
            time_str = timestamp.strftime('%H:%M:%S')
        except (ValueError, TypeError, AttributeError):
            time_str = str(alert.timestamp) if alert.timestamp else "--:--:--"

        # Choose display based on level
        level = alert.level
        ack_icon = ICONS['success'] if alert.acknowledged else ""

        if level == "critical":
            st.error(f"**{time_str}** [{alert.source}] {alert.message} {ack_icon}")
        elif level == "error":
            st.error(f"**{time_str}** [{alert.source}] {alert.message} {ack_icon}")
        elif level == "warning":
            st.warning(f"**{time_str}** [{alert.source}] {alert.message} {ack_icon}")
        else:
            st.info(f"**{time_str}** [{alert.source}] {alert.message} {ack_icon}")


def render_error_timeline(tracker: ErrorTracker):
    """Render error timeline chart."""
    st.subheader(f"{ICONS['chart']} Error Timeline (7 days)")

    errors = tracker.get_recent_errors(hours=168)  # 7 days

    if not errors:
        st.info("No errors in the last 7 days")
        return

    # Group by day and category
    daily_data = {}
    for e in errors:
        try:
            date = datetime.fromisoformat(e.timestamp).date()
            date_str = date.isoformat()
        except (ValueError, TypeError, AttributeError):
            continue

        if date_str not in daily_data:
            daily_data[date_str] = {}

        cat = e.category
        daily_data[date_str][cat] = daily_data[date_str].get(cat, 0) + 1

    if not daily_data:
        st.info("No data to display")
        return

    # Convert to dataframe for plotting
    dates = sorted(daily_data.keys())
    categories = list(set(cat for day in daily_data.values() for cat in day.keys()))

    plot_data = []
    for date in dates:
        for cat in categories:
            count = daily_data.get(date, {}).get(cat, 0)
            plot_data.append({
                "Date": date,
                "Category": cat,
                "Count": count
            })

    df = pd.DataFrame(plot_data)

    fig = px.bar(
        df,
        x="Date",
        y="Count",
        color="Category",
        barmode="stack"
    )
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    st.plotly_chart(fig, use_container_width=True)


def main():
    st.title(f"{ICONS['monitor']} System Monitoring")

    client = get_client()
    tracker = ErrorTracker()
    alert_manager = AlertManager()

    # Refresh button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("Refresh", type="primary"):
            st.rerun()
    with col2:
        if st.button("Run Health Check"):
            # Trigger critical condition check
            if client and st.session_state.connected:
                try:
                    account = client.get_account()
                    positions = client.get_positions()
                    alerts = alert_manager.check_critical_conditions(account, positions, config)
                    if alerts:
                        st.warning(f"Generated {len(alerts)} alert(s)")
                    else:
                        st.success("No critical conditions found")
                except Exception as e:
                    st.error(f"Health check failed: {e}")
            else:
                st.error("MT5 not connected")

    st.divider()

    # System Health
    health = check_system_health()
    render_health_status(health)

    st.divider()

    # Two columns for errors and alerts
    col1, col2 = st.columns(2)

    with col1:
        render_error_summary(tracker)

    with col2:
        render_alerts(alert_manager)

    st.divider()

    # Error timeline
    render_error_timeline(tracker)

    st.divider()

    # Recent errors table
    render_recent_errors(tracker)

    st.divider()

    # Maintenance actions
    st.subheader(f"{ICONS['settings']} Maintenance")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Clear Old Errors (30+ days)"):
            count = tracker.clear_old_errors(days=30)
            st.success(f"Cleared {count} old errors")

    with col2:
        if st.button("Clear Old Alerts (7+ days)"):
            count = alert_manager.clear_old_alerts(days=7)
            st.success(f"Cleared {count} old alerts")

    with col3:
        st.caption("Automatic cleanup runs periodically")

    # Status bar
    if client and is_connected():
        try:
            status_data = get_status_bar_data(client, config)
            render_status_bar(**status_data)
        except Exception:
            render_status_bar(connected=False)


if __name__ == "__main__":
    main()
