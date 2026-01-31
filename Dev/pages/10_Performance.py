"""
AI Trader - Performance Analytics Page

Comprehensive performance analytics with:
- Summary metrics (Total P/L, Win Rate, Profit Factor, etc.)
- Equity curve chart
- Performance by pair
- Performance by day/hour heatmap
- Recent trades table
- Drawdown analysis
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.utils.database import db
from src.utils.config import config
from components.tooltips import (
    metric_with_tooltip,
    simple_explanation_section,
    ICONS,
    tooltip_text,
    get_tooltip,
)
from components.status_bar import render_status_bar, get_status_bar_data
from components.mt5_session import get_client, is_connected
from src.trading.mt5_client import MT5Client

st.set_page_config(page_title="Performance - AI Trader", page_icon="", layout="wide")


# =============================================================================
# DATA FETCHING
# =============================================================================


def get_all_trades() -> list:
    """Fetch all closed trades from database."""
    try:
        with db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    trade_id,
                    timestamp,
                    closed_at,
                    instrument,
                    direction,
                    entry_price,
                    exit_price,
                    units,
                    pnl,
                    pnl_percent,
                    confidence_score,
                    close_reason,
                    status,
                    risk_amount,
                    risk_percent
                FROM trades
                WHERE status = 'CLOSED'
                ORDER BY closed_at ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"Error fetching trades: {e}")
        return []


def get_extended_stats(trades: list) -> dict:
    """Calculate extended performance statistics."""
    if not trades:
        return {
            "total_pnl": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "avg_trade": 0,
            "expectancy": 0,
            "max_drawdown_pct": 0,
            "max_drawdown_abs": 0,
            "current_drawdown_pct": 0,
            "gross_profit": 0,
            "gross_loss": 0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
        }

    pnls = [t.get("pnl", 0) or 0 for t in trades]

    winning = [p for p in pnls if p > 0]
    losing = [p for p in pnls if p < 0]

    gross_profit = sum(winning)
    gross_loss = abs(sum(losing))

    # Calculate max consecutive wins/losses
    max_wins, max_losses = 0, 0
    current_wins, current_losses = 0, 0

    for pnl in pnls:
        if pnl > 0:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        elif pnl < 0:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)

    # Calculate drawdown
    equity_curve = [0]
    peak = 0
    max_dd_abs = 0
    max_dd_pct = 0

    for pnl in pnls:
        equity_curve.append(equity_curve[-1] + pnl)
        peak = max(peak, equity_curve[-1])
        dd = peak - equity_curve[-1]
        if dd > max_dd_abs:
            max_dd_abs = dd
            max_dd_pct = (dd / peak * 100) if peak > 0 else 0

    current_dd = peak - equity_curve[-1] if equity_curve else 0
    current_dd_pct = (current_dd / peak * 100) if peak > 0 else 0

    win_rate = (len(winning) / len(pnls) * 100) if pnls else 0
    avg_win = sum(winning) / len(winning) if winning else 0
    avg_loss = sum(losing) / len(losing) if losing else 0

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    expectancy = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)

    return {
        "total_pnl": sum(pnls),
        "total_trades": len(pnls),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "best_trade": max(pnls) if pnls else 0,
        "worst_trade": min(pnls) if pnls else 0,
        "avg_trade": sum(pnls) / len(pnls) if pnls else 0,
        "expectancy": expectancy,
        "max_drawdown_pct": max_dd_pct,
        "max_drawdown_abs": max_dd_abs,
        "current_drawdown_pct": current_dd_pct,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "max_consecutive_wins": max_wins,
        "max_consecutive_losses": max_losses,
    }


def get_performance_by_pair(trades: list) -> dict:
    """Group performance by currency pair."""
    pair_stats = {}

    for trade in trades:
        pair = (trade.get("instrument") or "UNKNOWN").replace("_", "/")
        pnl = trade.get("pnl", 0) or 0

        if pair not in pair_stats:
            pair_stats[pair] = {"pnl": 0, "trades": 0, "wins": 0}

        pair_stats[pair]["pnl"] += pnl
        pair_stats[pair]["trades"] += 1
        if pnl > 0:
            pair_stats[pair]["wins"] += 1

    return pair_stats


def get_performance_by_time(trades: list) -> dict:
    """Group performance by day of week and hour."""
    day_hour_stats = {}

    for trade in trades:
        closed_at = trade.get("closed_at")
        if not closed_at:
            continue

        try:
            dt = datetime.fromisoformat(closed_at.replace("Z", "+00:00")) if isinstance(closed_at, str) else closed_at
            day = dt.strftime("%A")  # Day name
            hour = dt.hour
            pnl = trade.get("pnl", 0) or 0

            key = (day, hour)
            if key not in day_hour_stats:
                day_hour_stats[key] = {"pnl": 0, "trades": 0}

            day_hour_stats[key]["pnl"] += pnl
            day_hour_stats[key]["trades"] += 1
        except (ValueError, TypeError, AttributeError):
            continue

    return day_hour_stats


def calculate_equity_curve(trades: list, initial_capital: float = 10000) -> list:
    """Calculate equity curve from trades."""
    equity = [{"date": None, "equity": initial_capital, "pnl": 0}]

    for trade in trades:
        closed_at = trade.get("closed_at")
        pnl = trade.get("pnl", 0) or 0

        try:
            if closed_at:
                dt = datetime.fromisoformat(closed_at.replace("Z", "+00:00")) if isinstance(closed_at, str) else closed_at
            else:
                dt = datetime.now()

            new_equity = equity[-1]["equity"] + pnl
            equity.append({
                "date": dt,
                "equity": new_equity,
                "pnl": pnl
            })
        except (ValueError, TypeError, AttributeError):
            continue

    return equity[1:]  # Remove initial placeholder


# =============================================================================
# CHART RENDERERS
# =============================================================================

def render_equity_curve(equity_data: list, initial_capital: float):
    """Render equity curve chart."""
    if not equity_data:
        st.info("No equity data to display")
        return

    df = pd.DataFrame(equity_data)

    fig = go.Figure()

    # Equity line
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["equity"],
        mode="lines",
        name="Equity",
        line=dict(color="#2196F3", width=2),
        fill="tozeroy",
        fillcolor="rgba(33, 150, 243, 0.1)"
    ))

    # Initial capital reference line
    fig.add_hline(
        y=initial_capital,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Initial: ${initial_capital:,.0f}"
    )

    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        hovermode="x unified",
        height=400,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_pair_performance(pair_stats: dict):
    """Render performance by pair bar chart."""
    if not pair_stats:
        st.info("No pair performance data")
        return

    pairs = list(pair_stats.keys())
    pnls = [pair_stats[p]["pnl"] for p in pairs]
    trades = [pair_stats[p]["trades"] for p in pairs]
    win_rates = [pair_stats[p]["wins"] / pair_stats[p]["trades"] * 100 if pair_stats[p]["trades"] > 0 else 0 for p in pairs]

    colors = ["#4CAF50" if pnl > 0 else "#f44336" for pnl in pnls]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=pairs,
        y=pnls,
        marker_color=colors,
        text=[f"${pnl:+,.2f}<br>{t} trades<br>{wr:.0f}% win" for pnl, t, wr in zip(pnls, trades, win_rates)],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>P/L: $%{y:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        title="Performance by Currency Pair",
        xaxis_title="Pair",
        yaxis_title="Total P/L ($)",
        height=350,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_time_heatmap(time_stats: dict):
    """Render performance by day/hour heatmap."""
    if not time_stats:
        st.info("No time performance data")
        return

    # Create matrix for heatmap
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hours = list(range(24))

    # Initialize matrix
    data = []
    for day in days:
        row = []
        for hour in hours:
            key = (day, hour)
            if key in time_stats:
                row.append(time_stats[key]["pnl"])
            else:
                row.append(0)
        data.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=[f"{h:02d}:00" for h in hours],
        y=days,
        colorscale="RdYlGn",
        zmid=0,
        hovertemplate="Day: %{y}<br>Hour: %{x}<br>P/L: $%{z:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        title="Performance by Day and Hour",
        xaxis_title="Hour",
        yaxis_title="Day",
        height=300,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_drawdown_chart(equity_data: list):
    """Render drawdown chart."""
    if not equity_data:
        st.info("No drawdown data")
        return

    # Calculate drawdown series
    equities = [e["equity"] for e in equity_data]
    dates = [e["date"] for e in equity_data]

    peak = equities[0]
    drawdowns = []

    for eq in equities:
        peak = max(peak, eq)
        dd_pct = ((peak - eq) / peak * 100) if peak > 0 else 0
        drawdowns.append(-dd_pct)  # Negative for display

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=drawdowns,
        mode="lines",
        name="Drawdown",
        line=dict(color="#f44336", width=1),
        fill="tozeroy",
        fillcolor="rgba(244, 67, 54, 0.3)"
    ))

    fig.update_layout(
        title="Drawdown Over Time",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        hovermode="x unified",
        height=250,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_pnl_distribution(trades: list):
    """Render P/L distribution histogram."""
    pnls = [t.get("pnl", 0) or 0 for t in trades if t.get("pnl") is not None]

    if not pnls:
        st.info("No P/L data to display")
        return

    df = pd.DataFrame({"pnl": pnls})
    df["result"] = df["pnl"].apply(lambda x: "Win" if x > 0 else "Loss")

    fig = px.histogram(
        df,
        x="pnl",
        color="result",
        color_discrete_map={"Win": "#4CAF50", "Loss": "#f44336"},
        nbins=20,
        title="Trade P/L Distribution"
    )

    fig.update_layout(
        xaxis_title="P/L ($)",
        yaxis_title="Count",
        height=300,
        margin=dict(l=0, r=0, t=40, b=0),
        bargap=0.1
    )

    st.plotly_chart(fig, use_container_width=True)


def render_recent_trades_table(trades: list, limit: int = 20):
    """Render recent trades table."""
    if not trades:
        st.info("No trades to display")
        return

    # Get last N trades (reverse order for most recent first)
    recent = trades[-limit:][::-1]

    df = pd.DataFrame(recent)

    # Format columns
    if "closed_at" in df.columns:
        df["closed_at"] = pd.to_datetime(df["closed_at"]).dt.strftime("%Y-%m-%d %H:%M")
    if "instrument" in df.columns:
        df["instrument"] = df["instrument"].apply(lambda x: (x or "").replace("_", "/"))
    if "entry_price" in df.columns:
        df["entry_price"] = df["entry_price"].apply(lambda x: f"{x:.5f}" if x else "-")
    if "exit_price" in df.columns:
        df["exit_price"] = df["exit_price"].apply(lambda x: f"{x:.5f}" if x else "-")
    if "pnl" in df.columns:
        df["pnl_display"] = df["pnl"].apply(lambda x: f"${x:+,.2f}" if x else "$0.00")

    # Select and rename columns
    display_cols = ["closed_at", "instrument", "direction", "entry_price", "exit_price", "pnl_display", "confidence_score", "close_reason"]
    display_cols = [c for c in display_cols if c in df.columns]

    column_names = {
        "closed_at": "Date",
        "instrument": "Pair",
        "direction": "Direction",
        "entry_price": "Entry",
        "exit_price": "Exit",
        "pnl_display": "P/L",
        "confidence_score": "Confidence",
        "close_reason": "Reason"
    }

    df_display = df[display_cols].rename(columns=column_names)

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True
    )


# =============================================================================
# MAIN PAGE
# =============================================================================

def main():
    st.title("Performance Analytics")
    st.caption("Comprehensive trading performance analysis")

    # Get all trades
    trades = get_all_trades()

    if not trades:
        st.warning("No closed trades found. Start trading to see performance analytics here.")

        # Show placeholder
        st.info("""
        **What you'll see here:**

        - **Summary Metrics** - Total P/L, Win Rate, Profit Factor, Best/Worst trades
        - **Equity Curve** - Visual chart of your account growth over time
        - **Performance by Pair** - Which currency pairs perform best
        - **Time Analysis** - When do you trade best (day/hour)
        - **Drawdown Analysis** - Risk metrics and worst losing streaks
        - **Recent Trades** - Table of your latest trades with details
        """)
        return

    # Calculate stats
    stats = get_extended_stats(trades)
    pair_stats = get_performance_by_pair(trades)
    time_stats = get_performance_by_time(trades)

    # View mode toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        view_mode = st.radio(
            "View Mode",
            options=["Simple", "Detailed"],
            horizontal=True,
            key="performance_view_mode",
            help="Simple: Key metrics only. Detailed: Full analysis with charts."
        )

    st.divider()

    # ===================
    # SUMMARY METRICS (Always shown)
    # ===================
    st.subheader("Summary Metrics")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        pnl_color = "normal" if stats["total_pnl"] >= 0 else "inverse"
        metric_with_tooltip(
            "Total P/L",
            f"${stats['total_pnl']:+,.2f}",
            "total_return",
            delta=f"{stats['total_trades']} trades",
            delta_color=pnl_color
        )

    with col2:
        metric_with_tooltip(
            "Win Rate",
            f"{stats['win_rate']:.1f}%",
            "win_rate",
            delta=f"{stats['winning_trades']}W / {stats['losing_trades']}L"
        )

    with col3:
        pf_quality = "Good" if stats['profit_factor'] >= 1.5 else "OK" if stats['profit_factor'] >= 1 else "Poor"
        metric_with_tooltip(
            "Profit Factor",
            f"{stats['profit_factor']:.2f}",
            "profit_factor",
            delta=pf_quality
        )

    with col4:
        metric_with_tooltip(
            "Best Trade",
            f"${stats['best_trade']:+,.2f}",
            "total_return",
            help_text="Your most profitable single trade."
        )

    with col5:
        metric_with_tooltip(
            "Worst Trade",
            f"${stats['worst_trade']:+,.2f}",
            "total_return",
            help_text="Your biggest loss on a single trade."
        )

    # Simple mode: Just show summary and recent trades
    if view_mode == "Simple":
        st.divider()

        # Quick summary
        st.subheader("Quick Summary")

        if stats["total_pnl"] > 0:
            st.success(f"**Good job!** You're up ${stats['total_pnl']:,.2f} overall with a {stats['win_rate']:.0f}% win rate.")
        elif stats["total_pnl"] < 0:
            st.warning(f"**Room for improvement.** You're down ${abs(stats['total_pnl']):,.2f}. Focus on improving your win rate or reducing losses.")
        else:
            st.info("**Break-even.** Keep working on your strategy.")

        # Key insights
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            **Quick Stats:**
            - Average Win: **${stats['avg_win']:,.2f}**
            - Average Loss: **${stats['avg_loss']:,.2f}**
            - Expectancy: **${stats['expectancy']:,.2f}** per trade
            """)
        with col2:
            st.markdown(f"""
            **Streaks:**
            - Max Consecutive Wins: **{stats['max_consecutive_wins']}**
            - Max Consecutive Losses: **{stats['max_consecutive_losses']}**
            - Max Drawdown: **{stats['max_drawdown_pct']:.1f}%**
            """)

        st.divider()
        st.subheader("Recent Trades")
        render_recent_trades_table(trades, limit=10)

        # Status bar
        client = get_client()
        if client and st.session_state.connected:
            status_data = get_status_bar_data(client, config)
            render_status_bar(**status_data)

        return

    # ===================
    # DETAILED MODE
    # ===================

    st.divider()

    # Secondary metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_with_tooltip(
            "Average Trade",
            f"${stats['avg_trade']:+,.2f}",
            "expectancy",
            help_text="Average profit/loss per trade."
        )

    with col2:
        metric_with_tooltip(
            "Expectancy",
            f"${stats['expectancy']:+,.2f}",
            "expectancy"
        )

    with col3:
        st.metric(
            "Gross Profit",
            f"${stats['gross_profit']:,.2f}",
            help="Total amount won from all winning trades."
        )

    with col4:
        st.metric(
            "Gross Loss",
            f"${stats['gross_loss']:,.2f}",
            help="Total amount lost from all losing trades."
        )

    st.divider()

    # Equity curve
    st.subheader("Equity Curve")
    initial_capital = 10000  # Could be from config
    equity_data = calculate_equity_curve(trades, initial_capital)
    render_equity_curve(equity_data, initial_capital)

    st.divider()

    # Two column layout for pair performance and distribution
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Performance by Pair")
        render_pair_performance(pair_stats)

    with col2:
        st.subheader("P/L Distribution")
        render_pnl_distribution(trades)

    st.divider()

    # Time analysis
    st.subheader("Performance by Time")
    st.caption("Shows when your trades are most profitable (green) or losing (red)")
    render_time_heatmap(time_stats)

    st.divider()

    # Drawdown analysis
    st.subheader("Drawdown Analysis")

    col1, col2, col3 = st.columns(3)

    with col1:
        metric_with_tooltip(
            "Max Drawdown",
            f"{stats['max_drawdown_pct']:.1f}%",
            "max_drawdown",
            delta=f"${stats['max_drawdown_abs']:,.2f}"
        )

    with col2:
        current_dd_status = "OK" if stats['current_drawdown_pct'] < 10 else "Warning"
        st.metric(
            "Current Drawdown",
            f"{stats['current_drawdown_pct']:.1f}%",
            delta=current_dd_status,
            delta_color="normal" if current_dd_status == "OK" else "inverse",
            help="How much below your peak equity you currently are."
        )

    with col3:
        st.metric(
            "Max Losing Streak",
            f"{stats['max_consecutive_losses']} trades",
            help="Longest streak of consecutive losing trades."
        )

    # Drawdown chart
    render_drawdown_chart(equity_data)

    st.divider()

    # Recent trades
    st.subheader("Recent Trades")
    render_recent_trades_table(trades, limit=20)

    # Explanation section
    st.divider()
    with st.expander(f"{ICONS['question']} Understanding Your Performance"):
        st.markdown("""
        ### Key Metrics Explained

        **Win Rate** - Percentage of trades that made money. Above 50% is good, but not required for profitability.

        **Profit Factor** - Gross profit divided by gross loss. Above 1.5 is good, above 2.0 is excellent.

        **Expectancy** - Average expected profit per trade. Positive expectancy means your strategy is profitable over time.

        **Max Drawdown** - The largest peak-to-trough decline in your equity. Lower is better. Professional traders aim for under 20%.

        ---

        ### Tips for Improvement

        1. **If Win Rate is low:** Focus on better entry timing and analysis quality
        2. **If Profit Factor is low:** Your winners might be too small or losers too big - review your exit strategy
        3. **If Drawdown is high:** Consider reducing position sizes or tightening stop losses
        4. **If certain pairs underperform:** Consider removing them from your trading watchlist
        """)

    # Status bar
    client = get_client()
    if client and st.session_state.connected:
        status_data = get_status_bar_data(client, config)
        render_status_bar(**status_data)


if __name__ == "__main__":
    main()
