"""
AI Trader - Backtest Page

Walk-forward backtesting simulation using historical data.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path
from datetime import datetime, timedelta

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.backtesting import (
    DataLoader,
    HistoricalDataRequest,
    BacktestEngine,
    BacktestConfig,
    ReportGenerator,
    MetricsCalculator,
)
from components.tooltips import (
    metric_with_tooltip,
    simple_explanation_section,
    ICONS,
    tooltip_text,
    get_tooltip,
)
from components.status_bar import render_compact_status_bar

st.set_page_config(page_title="Backtest - AI Trader", page_icon="", layout="wide")


def format_number(value: float, decimals: int = 2, prefix: str = "", suffix: str = "") -> str:
    """Format number with optional prefix/suffix."""
    if value >= 0:
        return f"{prefix}{value:,.{decimals}f}{suffix}"
    return f"-{prefix}{abs(value):,.{decimals}f}{suffix}"


def render_metric_card(label: str, value: str, delta: str = None, delta_color: str = "normal"):
    """Render a styled metric card."""
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def render_equity_chart(chart_data: dict):
    """Render equity curve chart with Plotly."""
    if not chart_data.get("x") or not chart_data.get("y"):
        st.info("No equity data available")
        return

    fig = go.Figure()

    # Main equity line
    fig.add_trace(go.Scatter(
        x=chart_data["x"],
        y=chart_data["y"],
        mode="lines",
        name="Equity",
        line=dict(color="#2196F3", width=2),
        fill="tozeroy",
        fillcolor="rgba(33, 150, 243, 0.1)"
    ))

    # Initial equity reference line
    initial = chart_data.get("initial", 0)
    if initial > 0:
        fig.add_hline(
            y=initial,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Initial: ${initial:,.0f}"
        )

    # Trade markers
    trades = chart_data.get("trades", {})
    if trades.get("x"):
        for i, (x, y, t_type, color) in enumerate(zip(
            trades["x"], trades["y"], trades["types"], trades["colors"]
        )):
            fig.add_trace(go.Scatter(
                x=[x],
                y=[y],
                mode="markers",
                marker=dict(
                    size=10,
                    color=color,
                    symbol="triangle-up" if t_type == "entry" else "triangle-down"
                ),
                showlegend=False,
                hoverinfo="text",
                hovertext=f"{t_type.capitalize()} @ ${y:,.2f}"
            ))

    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        hovermode="x unified",
        height=400,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_drawdown_chart(chart_data: dict):
    """Render drawdown chart."""
    if not chart_data.get("x") or not chart_data.get("y"):
        st.info("No drawdown data available")
        return

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=chart_data["x"],
        y=chart_data["y"],
        mode="lines",
        name="Drawdown",
        line=dict(color="#f44336", width=1),
        fill="tozeroy",
        fillcolor="rgba(244, 67, 54, 0.3)"
    ))

    fig.update_layout(
        title="Drawdown",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        hovermode="x unified",
        height=250,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_trade_distribution(chart_data: dict):
    """Render trade P&L distribution histogram."""
    pnls = chart_data.get("pnls", [])

    if not pnls:
        st.info("No trades to display")
        return

    # Create DataFrame for coloring
    df = pd.DataFrame({"pnl": pnls})
    df["result"] = df["pnl"].apply(lambda x: "Win" if x > 0 else "Loss")

    fig = px.histogram(
        df,
        x="pnl",
        color="result",
        color_discrete_map={"Win": "#4CAF50", "Loss": "#f44336"},
        nbins=chart_data.get("bins", 20),
        title="Trade P&L Distribution"
    )

    fig.update_layout(
        xaxis_title="P&L ($)",
        yaxis_title="Count",
        height=300,
        margin=dict(l=0, r=0, t=40, b=0),
        bargap=0.1
    )

    st.plotly_chart(fig, use_container_width=True)


def render_monthly_returns(chart_data: dict):
    """Render monthly returns heatmap."""
    heatmap_data = chart_data.get("heatmap_data", [])

    if not heatmap_data:
        st.info("No monthly return data available")
        return

    # Convert to DataFrame
    df = pd.DataFrame(heatmap_data)

    if df.empty:
        st.info("No monthly return data available")
        return

    # Pivot for heatmap
    pivot = df.pivot_table(
        index="year",
        columns="month",
        values="return",
        aggfunc="mean"
    )

    # Month names
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[month_names[m - 1] for m in pivot.columns],
        y=pivot.index,
        colorscale="RdYlGn",
        zmid=0,
        text=[[f"{v:.1f}%" if not pd.isna(v) else "" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont={"size": 10},
        hovertemplate="Year: %{y}<br>Month: %{x}<br>Return: %{z:.2f}%<extra></extra>"
    ))

    fig.update_layout(
        title="Monthly Returns (%)",
        height=250,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_trades_table(trades: list):
    """Render trades table."""
    if not trades:
        st.info("No trades executed")
        return

    df = pd.DataFrame([t.to_dict() if hasattr(t, 'to_dict') else t for t in trades])

    # Format columns
    if "entry_time" in df.columns:
        df["entry_time"] = pd.to_datetime(df["entry_time"]).dt.strftime("%Y-%m-%d %H:%M")
    if "exit_time" in df.columns:
        df["exit_time"] = pd.to_datetime(df["exit_time"]).dt.strftime("%Y-%m-%d %H:%M")

    # Select columns to display
    display_cols = ["entry_time", "direction", "entry_price", "exit_price",
                    "exit_reason", "pnl", "pnl_pips", "confidence", "risk_tier"]
    display_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "entry_time": st.column_config.TextColumn("Entry Time"),
            "direction": st.column_config.TextColumn("Direction"),
            "entry_price": st.column_config.NumberColumn("Entry", format="%.5f"),
            "exit_price": st.column_config.NumberColumn("Exit", format="%.5f"),
            "exit_reason": st.column_config.TextColumn("Reason"),
            "pnl": st.column_config.NumberColumn("P&L ($)", format="%.2f"),
            "pnl_pips": st.column_config.NumberColumn("Pips", format="%.1f"),
            "confidence": st.column_config.NumberColumn("Confidence"),
            "risk_tier": st.column_config.TextColumn("Risk Tier"),
        }
    )


def main():
    st.title("Backtesting")
    st.markdown("Walk-forward simulation using historical data and AI analysis")

    # Configuration section
    st.subheader("Configuration")

    col1, col2, col3 = st.columns(3)

    with col1:
        pairs = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF",
                 "EUR_GBP", "EUR_JPY", "GBP_JPY", "USD_CAD", "NZD_USD", "BTC_USD"]
        instrument = st.selectbox(
            "Currency Pair",
            pairs,
            format_func=lambda x: x.replace("_", "/")
        )

    with col2:
        timeframes = ["M5", "M15", "M30", "H1", "H4", "D"]
        timeframe = st.selectbox("Timeframe", timeframes, index=3)

    with col3:
        initial_capital = st.number_input(
            "Initial Capital ($)",
            min_value=1000,
            max_value=1000000,
            value=10000,
            step=1000
        )

    col1, col2 = st.columns(2)

    with col1:
        # Default: last 3 months
        default_end = datetime.now()
        default_start = default_end - timedelta(days=90)

        start_date = st.date_input(
            "Start Date",
            value=default_start,
            max_value=datetime.now().date()
        )

    with col2:
        end_date = st.date_input(
            "End Date",
            value=default_end,
            max_value=datetime.now().date()
        )

    # Advanced options
    with st.expander("Advanced Options"):
        col1, col2, col3 = st.columns(3)

        with col1:
            min_confidence = st.slider(
                "Minimum Confidence",
                min_value=30,
                max_value=90,
                value=50,
                step=5,
                help="Only trade when confidence score is above this threshold"
            )

        with col2:
            use_adversarial = st.checkbox(
                "Use Adversarial Analysis",
                value=True,
                help="Enable bull/bear debate for signal confirmation"
            )

        with col3:
            lookback_bars = st.number_input(
                "Lookback Bars",
                min_value=20,
                max_value=200,
                value=50,
                help="Number of bars used for analysis"
            )

        col1, col2 = st.columns(2)

        with col1:
            atr_sl_mult = st.number_input(
                "Stop Loss (ATR multiplier)",
                min_value=1.0,
                max_value=5.0,
                value=2.0,
                step=0.5
            )

        with col2:
            atr_tp_mult = st.number_input(
                "Take Profit (ATR multiplier)",
                min_value=1.0,
                max_value=10.0,
                value=4.0,
                step=0.5
            )

        st.divider()

        col1, col2, col3 = st.columns(3)

        with col1:
            spread_pips = st.number_input(
                "Avg Spread (pips)",
                min_value=0.0,
                max_value=10.0,
                value=1.2,
                step=0.1,
                help="Average spread applied to entries/exits"
            )

        with col2:
            slippage_pips = st.number_input(
                "Slippage (pips)",
                min_value=0.0,
                max_value=5.0,
                value=0.2,
                step=0.1,
                help="Adverse slippage per side"
            )

        with col3:
            commission_per_lot = st.number_input(
                "Commission (per lot, round-turn)",
                min_value=0.0,
                max_value=50.0,
                value=7.0,
                step=0.5,
                help="Round-turn commission per lot"
            )

        st.divider()

        limit_sessions = st.checkbox(
            "Limit entries to trading sessions (UTC)",
            value=True
        )

        session_options = {
            "Tokyo (00-09)": (0, 9),
            "London (07-16)": (7, 16),
            "New York (12-21)": (12, 21),
            "Sydney (21-06)": (21, 6),
        }

        selected_sessions = st.multiselect(
            "Sessions",
            list(session_options.keys()),
            default=["London (07-16)", "New York (12-21)"]
        )

        allow_weekends = st.checkbox(
            "Allow weekend entries",
            value=False
        )

    # Validate dates
    if start_date >= end_date:
        st.error("Start date must be before end date")
        return

    # View mode toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        view_mode = st.radio(
            "View Mode",
            options=["Simple", "Detailed"],
            horizontal=True,
            key="backtest_view_mode",
            help="Simple: Key results only. Detailed: Full metrics and charts."
        )
    # view_mode is automatically stored in session_state via key

    # Run button
    st.divider()

    if st.button("Run Backtest", type="primary", use_container_width=True):
        run_backtest(
            instrument=instrument,
            timeframe=timeframe,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time()),
            initial_capital=initial_capital,
            min_confidence=min_confidence,
            use_adversarial=use_adversarial,
            lookback_bars=lookback_bars,
            atr_sl_mult=atr_sl_mult,
            atr_tp_mult=atr_tp_mult,
            spread_pips=spread_pips,
            slippage_pips=slippage_pips,
            commission_per_lot=commission_per_lot,
            limit_sessions=limit_sessions,
            selected_sessions=selected_sessions,
            session_options=session_options,
            allow_weekends=allow_weekends
        )

    # Display results if available
    if "backtest_report" in st.session_state and st.session_state.backtest_report:
        display_results(st.session_state.backtest_report)


def run_backtest(**params):
    """Execute backtest with given parameters."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Step 1: Load data
        status_text.text("Loading historical data...")
        progress_bar.progress(10)

        loader = DataLoader()

        def data_progress(current, total):
            progress_bar.progress(10 + int((current / total) * 30))
            status_text.text(f"Loading data chunk {current}/{total}...")

        historical_data = loader.load_simple(
            instrument=params["instrument"],
            timeframe=params["timeframe"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            progress_callback=data_progress
        )

        if historical_data.total_bars < params["lookback_bars"] + 10:
            st.error(f"Not enough data: {historical_data.total_bars} bars loaded, need at least {params['lookback_bars'] + 10}")
            return

        status_text.text(f"Loaded {historical_data.total_bars} bars")
        progress_bar.progress(40)

        # Step 2: Run backtest
        status_text.text("Running backtest simulation...")

        session_hours = None
        if params.get("limit_sessions"):
            session_hours = []
            for label in params.get("selected_sessions", []):
                if label in params.get("session_options", {}):
                    session_hours.append(params["session_options"][label])

        config = BacktestConfig(
            instrument=params["instrument"],
            timeframe=params["timeframe"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            initial_capital=params["initial_capital"],
            min_confidence=params["min_confidence"],
            use_adversarial=params["use_adversarial"],
            lookback_bars=params["lookback_bars"],
            atr_sl_multiplier=params["atr_sl_mult"],
            atr_tp_multiplier=params["atr_tp_mult"],
            spread_pips=params.get("spread_pips", 1.2),
            slippage_pips=params.get("slippage_pips", 0.2),
            commission_per_lot=params.get("commission_per_lot", 7.0),
            session_hours=session_hours,
            allow_weekends=params.get("allow_weekends", False)
        )

        engine = BacktestEngine()

        def backtest_progress(current, total, message):
            progress_bar.progress(40 + int((current / total) * 50))
            status_text.text(message)

        result = engine.run(
            candles=historical_data.candles,
            config=config,
            progress_callback=backtest_progress
        )

        progress_bar.progress(90)
        status_text.text("Generating report...")

        # Step 3: Generate report
        report_gen = ReportGenerator()
        report = report_gen.generate(result)

        progress_bar.progress(100)
        status_text.text("Backtest complete!")

        # Store in session
        st.session_state.backtest_report = report
        st.session_state.backtest_result = result

        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()

        st.success(f"Backtest completed! {len(result.trades)} trades executed in {result.run_time_seconds:.1f}s")
        st.rerun()

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Backtest failed: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())


def display_results(report):
    """Display backtest results."""
    st.divider()
    st.subheader("Results")

    # Get view mode
    current_view_mode = st.session_state.get("backtest_view_mode", "Detailed")

    # Get metrics (handle both object and dict)
    if hasattr(report.metrics, 'to_dict'):
        metrics = report.metrics
    else:
        metrics = type('Metrics', (), report.metrics)()

    # Extract values for easy access
    ret_pct = getattr(metrics, 'total_return_pct', 0) if not isinstance(metrics, dict) else metrics.get('total_return_pct', 0)
    ret_abs = getattr(metrics, 'total_return_abs', 0) if not isinstance(metrics, dict) else metrics.get('total_return_abs', 0)
    dd_pct = getattr(metrics, 'max_drawdown_pct', 0) if not isinstance(metrics, dict) else metrics.get('max_drawdown_pct', 0)
    sharpe = getattr(metrics, 'sharpe_ratio', None) if not isinstance(metrics, dict) else metrics.get('sharpe_ratio', None)
    sortino = getattr(metrics, 'sortino_ratio', None) if not isinstance(metrics, dict) else metrics.get('sortino_ratio', None)
    win_rate = getattr(metrics, 'win_rate', 0) if not isinstance(metrics, dict) else metrics.get('win_rate', 0)
    profit_factor = getattr(metrics, 'profit_factor', None) if not isinstance(metrics, dict) else metrics.get('profit_factor', None)

    # Key metrics cards with tooltips
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_with_tooltip(
            "Total Return",
            f"{ret_pct:+.2f}%",
            "total_return",
            delta=f"${ret_abs:+,.2f}"
        )

    with col2:
        metric_with_tooltip(
            "Max Drawdown",
            f"{dd_pct:.2f}%",
            "max_drawdown",
            delta_color="inverse"
        )

    with col3:
        metric_with_tooltip(
            "Sharpe Ratio",
            f"{sharpe:.2f}" if sharpe else "N/A",
            "sharpe_ratio"
        )

    with col4:
        metric_with_tooltip(
            "Win Rate",
            f"{win_rate:.1f}%",
            "win_rate"
        )

    # Simple mode: Show only summary
    if current_view_mode == "Simple":
        # Simple summary
        st.divider()
        st.subheader("Summary")

        # Calculate simple grade
        score = 0
        if ret_pct > 10: score += 2
        elif ret_pct > 0: score += 1
        if sharpe and sharpe >= 1.0: score += 2
        elif sharpe and sharpe > 0: score += 1
        if dd_pct <= 15: score += 2
        elif dd_pct <= 25: score += 1
        if win_rate >= 55: score += 1

        if score >= 6:
            st.success("**STRONG STRATEGY** - The backtest shows promising results.")
        elif score >= 4:
            st.info("**ACCEPTABLE STRATEGY** - Results are okay but there's room for improvement.")
        elif score >= 2:
            st.warning("**NEEDS WORK** - The strategy shows weaknesses.")
        else:
            st.error("**NOT RECOMMENDED** - This strategy needs significant changes.")

        # Show just the equity curve
        st.divider()
        st.subheader("Equity Curve")
        render_equity_chart(report.equity_chart)

        # Quick stats
        total = getattr(metrics, 'total_trades', 0) if not isinstance(metrics, dict) else metrics.get('total_trades', 0)
        wins = getattr(metrics, 'winning_trades', 0) if not isinstance(metrics, dict) else metrics.get('winning_trades', 0)
        losses = getattr(metrics, 'losing_trades', 0) if not isinstance(metrics, dict) else metrics.get('losing_trades', 0)

        st.markdown(f"""
        **Quick Stats:**
        - Total trades: **{total}**
        - Wins: **{wins}** | Losses: **{losses}**
        - Return: **{ret_pct:+.2f}%** (${ret_abs:+,.2f})
        - Max drawdown: **{dd_pct:.2f}%**
        """)

        # Save button
        st.divider()
        if st.button("Save Report"):
            try:
                filepath = report.save()
                st.success(f"Report saved to: {filepath}")
            except Exception as e:
                st.error(f"Failed to save report: {e}")

        return  # Exit early for Simple mode

    # Detailed mode: Full analysis
    # Simple explanation section - What do these results mean?
    with st.expander(f"{ICONS['question']} What do these results mean?"):
        st.markdown("### Understanding Your Backtest Results")
        st.markdown("---")

        # Total Return interpretation
        if ret_pct > 0:
            ret_status = "success"
            ret_msg = f"Your strategy made money! A return of **{ret_pct:.1f}%** means if you started with $10,000, you'd have **${10000 * (1 + ret_pct/100):,.0f}** now."
        else:
            ret_status = "error"
            ret_msg = f"Your strategy lost money. A return of **{ret_pct:.1f}%** means if you started with $10,000, you'd have **${10000 * (1 + ret_pct/100):,.0f}** now."

        st.markdown(f"**Total Return:** {ret_pct:+.1f}%")
        if ret_status == "success":
            st.success(ret_msg)
        else:
            st.error(ret_msg)

        st.markdown("---")

        # Sharpe Ratio interpretation
        st.markdown(f"**Sharpe Ratio:** {sharpe:.2f}" if sharpe else "**Sharpe Ratio:** N/A")
        if sharpe is not None:
            if sharpe >= 2.0:
                st.success(f"Excellent! A Sharpe of {sharpe:.2f} means you're getting great returns for the risk you're taking. Professional funds aim for 1.0+.")
            elif sharpe >= 1.0:
                st.info(f"Good. A Sharpe of {sharpe:.2f} is acceptable. You're earning decent returns relative to your risk.")
            elif sharpe > 0:
                st.warning(f"Below average. A Sharpe of {sharpe:.2f} means returns aren't great relative to the volatility. Consider adjusting the strategy.")
            else:
                st.error(f"Negative Sharpe ({sharpe:.2f}) means you're losing money. The strategy needs significant changes.")

        st.markdown("---")

        # Max Drawdown interpretation
        st.markdown(f"**Max Drawdown:** {dd_pct:.1f}%")
        if dd_pct <= 10:
            st.success(f"Low risk! Your worst drop was only {dd_pct:.1f}%. This means your capital was well protected during losing streaks.")
        elif dd_pct <= 20:
            st.info(f"Moderate risk. A {dd_pct:.1f}% drawdown is common for active trading strategies. Just make sure you can handle seeing your account drop this much.")
        elif dd_pct <= 30:
            st.warning(f"High drawdown. Losing {dd_pct:.1f}% from your peak can be psychologically challenging. Consider reducing position sizes.")
        else:
            st.error(f"Very high drawdown of {dd_pct:.1f}%! This level of loss would be difficult to recover from. The strategy is too risky.")

        st.markdown("---")

        # Win Rate interpretation
        st.markdown(f"**Win Rate:** {win_rate:.1f}%")
        if win_rate >= 60:
            st.success(f"High win rate of {win_rate:.0f}%! You're winning more trades than you lose. This can provide psychological comfort.")
        elif win_rate >= 50:
            st.info(f"Average win rate of {win_rate:.0f}%. You win about half your trades. Make sure your winners are bigger than your losers!")
        else:
            st.warning(f"Low win rate of {win_rate:.0f}%. This is fine IF your winning trades make much more than your losing trades cost. Check your profit factor.")

        # Overall assessment
        st.markdown("---")
        st.markdown("### Overall Assessment")

        # Calculate simple grade
        score = 0
        if ret_pct > 10: score += 2
        elif ret_pct > 0: score += 1
        if sharpe and sharpe >= 1.0: score += 2
        elif sharpe and sharpe > 0: score += 1
        if dd_pct <= 15: score += 2
        elif dd_pct <= 25: score += 1
        if win_rate >= 55: score += 1

        if score >= 6:
            st.success("**STRONG STRATEGY** - The backtest shows promising results. Consider paper trading before going live.")
        elif score >= 4:
            st.info("**ACCEPTABLE STRATEGY** - Results are okay but there's room for improvement. Review your entry/exit rules.")
        elif score >= 2:
            st.warning("**NEEDS WORK** - The strategy shows weaknesses. Analyze your losing trades to find patterns.")
        else:
            st.error("**NOT RECOMMENDED** - This strategy needs significant changes before using real money.")

    # Charts tabs
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["Equity Curve", "Drawdown", "Trades", "Monthly Returns"])

    with tab1:
        render_equity_chart(report.equity_chart)

    with tab2:
        render_drawdown_chart(report.drawdown_chart)

    with tab3:
        col1, col2 = st.columns([2, 1])
        with col1:
            render_trade_distribution(report.trade_distribution)
        with col2:
            # Trade summary stats with tooltips
            total = getattr(metrics, 'total_trades', 0) if not isinstance(metrics, dict) else metrics.get('total_trades', 0)
            wins = getattr(metrics, 'winning_trades', 0) if not isinstance(metrics, dict) else metrics.get('winning_trades', 0)
            losses = getattr(metrics, 'losing_trades', 0) if not isinstance(metrics, dict) else metrics.get('losing_trades', 0)
            pf = getattr(metrics, 'profit_factor', None) if not isinstance(metrics, dict) else metrics.get('profit_factor', None)

            st.metric("Total Trades", total, help="Total number of trades executed during the backtest period.")
            st.metric("Wins / Losses", f"{wins} / {losses}", help="Number of winning vs losing trades.")
            metric_with_tooltip("Profit Factor", f"{pf:.2f}" if pf else "N/A", "profit_factor")

        st.subheader("Trade List")
        result = st.session_state.get('backtest_result')
        if result:
            render_trades_table(result.trades)

    with tab4:
        render_monthly_returns(report.monthly_returns)

    # Detailed metrics expander with explanations
    with st.expander("All Metrics (with explanations)"):
        col1, col2, col3 = st.columns(3)

        # Extract additional metrics
        gross_profit = getattr(metrics, 'gross_profit', 0) if not isinstance(metrics, dict) else metrics.get('gross_profit', 0)
        gross_loss = getattr(metrics, 'gross_loss', 0) if not isinstance(metrics, dict) else metrics.get('gross_loss', 0)
        expectancy = getattr(metrics, 'expectancy', 0) if not isinstance(metrics, dict) else metrics.get('expectancy', 0)
        avg_win = getattr(metrics, 'avg_win', 0) if not isinstance(metrics, dict) else metrics.get('avg_win', 0)
        avg_loss = getattr(metrics, 'avg_loss', 0) if not isinstance(metrics, dict) else metrics.get('avg_loss', 0)
        largest_win = getattr(metrics, 'largest_win', 0) if not isinstance(metrics, dict) else metrics.get('largest_win', 0)
        largest_loss = getattr(metrics, 'largest_loss', 0) if not isinstance(metrics, dict) else metrics.get('largest_loss', 0)
        max_consec_wins = getattr(metrics, 'max_consecutive_wins', 0) if not isinstance(metrics, dict) else metrics.get('max_consecutive_wins', 0)
        max_consec_losses = getattr(metrics, 'max_consecutive_losses', 0) if not isinstance(metrics, dict) else metrics.get('max_consecutive_losses', 0)

        with col1:
            st.markdown("**Returns**")
            st.text(f"Total Return: {ret_pct:.2f}%")
            st.caption(tooltip_text("total_return"))
            st.text(f"Gross Profit: ${gross_profit:,.2f}")
            st.caption("Total amount won from all winning trades.")
            st.text(f"Gross Loss: ${gross_loss:,.2f}")
            st.caption("Total amount lost from all losing trades.")
            st.text(f"Expectancy: ${expectancy:,.2f}")
            st.caption(tooltip_text("expectancy"))

        with col2:
            st.markdown("**Risk Metrics**")
            st.text(f"Max Drawdown: {dd_pct:.2f}%")
            st.caption(tooltip_text("max_drawdown"))
            st.text(f"Sharpe Ratio: {sharpe:.2f}" if sharpe else "Sharpe Ratio: N/A")
            st.caption(tooltip_text("sharpe_ratio"))
            st.text(f"Sortino Ratio: {sortino:.2f}" if sortino else "Sortino Ratio: N/A")
            st.caption(tooltip_text("sortino_ratio"))

        with col3:
            st.markdown("**Trade Stats**")
            st.text(f"Avg Win: ${avg_win:,.2f}")
            st.caption("Average profit per winning trade.")
            st.text(f"Avg Loss: ${avg_loss:,.2f}")
            st.caption("Average loss per losing trade.")
            st.text(f"Largest Win: ${largest_win:,.2f}")
            st.text(f"Largest Loss: ${largest_loss:,.2f}")
            st.text(f"Max Consecutive Wins: {max_consec_wins}")
            st.text(f"Max Consecutive Losses: {max_consec_losses}")
            st.caption("Longest winning and losing streaks.")

    # Save report button
    st.divider()
    col1, col2 = st.columns([1, 4])

    with col1:
        if st.button("Save Report"):
            try:
                filepath = report.save()
                st.success(f"Report saved to: {filepath}")
            except Exception as e:
                st.error(f"Failed to save report: {e}")

    # Show config
    with st.expander("Backtest Configuration"):
        st.json({
            "instrument": report.instrument,
            "timeframe": report.timeframe,
            "date_range": report.date_range,
            "created_at": report.created_at,
        })


if __name__ == "__main__":
    main()
