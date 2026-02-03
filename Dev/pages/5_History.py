"""
AI Trader - History Page

Trade history and performance statistics.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.utils.database import db
from src.utils.mt5_sync import sync_mt5_history, get_sync_status
from src.analysis.post_trade_analyzer import PostTradeAnalyzer
from components.empty_states import render_minimal_status

st.set_page_config(page_title="History - AI Trader", page_icon="", layout="wide")


def main():
    st.title("Trade History")

    # MT5 Sync Section
    with st.expander("MT5 History Sync", expanded=False):
        st.markdown("""
        Sync trades executed directly in MT5 (not through AI Trader) into the dashboard.
        This updates your statistics and history with all MT5 trades.
        """)

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            days_to_sync = st.number_input("Days to sync", min_value=1, max_value=365, value=30)

        with col2:
            st.write("")  # Spacer
            st.write("")
            if st.button("Sync Now", type="primary", use_container_width=True):
                with st.spinner("Syncing MT5 history..."):
                    result = sync_mt5_history(days=days_to_sync)

                if result["success"]:
                    if result["imported"] > 0:
                        st.success(f"Imported {result['imported']} trades from MT5!")
                    else:
                        st.info("No new trades to import.")
                    st.rerun()
                else:
                    st.error(f"Sync failed: {result['message']}")

        with col3:
            # Show sync status
            try:
                status = get_sync_status()
                if status["mt5_connected"]:
                    status_text = f"MT5: {status['mt5_closed_trades']} trades | DB: {status['db_closed_trades']} trades"
                    if status["needs_sync"]:
                        st.warning(f"{status_text} - **Sync recommended**")
                    else:
                        st.success(f"{status_text} - In sync")
                else:
                    st.error("MT5 not connected")
            except Exception as e:
                st.warning(f"Could not get sync status: {e}")

    st.divider()

    # Performance stats
    stats = db.get_performance_stats()
    daily_pnl = db.get_daily_pnl()
    trades_today = db.get_trades_today()

    # Summary metrics
    st.subheader("Performance Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Trades", stats["total_trades"])

    with col2:
        win_rate_delta = "Good" if stats["win_rate"] >= 50 else "Needs work"
        st.metric("Win Rate", f"{stats['win_rate']:.1f}%", delta=win_rate_delta)

    with col3:
        st.metric("Total P/L", f"${stats['total_pnl']:+,.2f}")

    with col4:
        pf_delta = "Good" if stats["profit_factor"] >= 1.5 else "OK" if stats["profit_factor"] >= 1 else "Losing"
        st.metric("Profit Factor", f"{stats['profit_factor']:.2f}", delta=pf_delta)

    st.divider()

    # Detailed stats
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Win/Loss Breakdown")

        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | Winning Trades | {stats['winning_trades']} |
        | Losing Trades | {stats['losing_trades']} |
        | Average Win | ${stats['avg_win']:.2f} |
        | Average Loss | ${abs(stats['avg_loss']):.2f} |
        """)

    with col2:
        st.subheader("Today's Performance")

        st.metric("Today's P/L", f"${daily_pnl:+,.2f}")
        st.metric("Trades Today", len(trades_today))

    st.divider()

    # Trade history table
    st.subheader("Recent Trades")

    # Get closed trades from database
    try:
        with db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    trade_id,
                    timestamp,
                    instrument,
                    direction,
                    entry_price,
                    exit_price,
                    units,
                    pnl,
                    pnl_percent,
                    confidence_score,
                    close_reason,
                    status
                FROM trades
                ORDER BY timestamp DESC
                LIMIT 50
            """)
            trades = [dict(row) for row in cursor.fetchall()]

        if trades:
            df = pd.DataFrame(trades)

            # Format columns
            df['instrument'] = df['instrument'].apply(lambda x: x.replace('_', '/') if x else '')
            df['pnl'] = df['pnl'].apply(lambda x: f"${x:+,.2f}" if x else "$0.00")
            df['pnl_percent'] = df['pnl_percent'].apply(lambda x: f"{x:+.2f}%" if x else "0%")
            df['entry_price'] = df['entry_price'].apply(lambda x: f"{x:.5f}" if x else "-")
            df['exit_price'] = df['exit_price'].apply(lambda x: f"{x:.5f}" if x else "-")

            # Rename columns
            df = df.rename(columns={
                'trade_id': 'Trade ID',
                'timestamp': 'Time',
                'instrument': 'Pair',
                'direction': 'Direction',
                'entry_price': 'Entry',
                'exit_price': 'Exit',
                'units': 'Units',
                'pnl': 'P/L',
                'pnl_percent': 'P/L %',
                'confidence_score': 'Confidence',
                'close_reason': 'Close Reason',
                'status': 'Status'
            })

            # Display
            st.dataframe(
                df[['Time', 'Pair', 'Direction', 'Entry', 'Exit', 'P/L', 'P/L %', 'Confidence', 'Status']],
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info("No trade history yet. Start trading to see your history here.")

    except Exception as e:
        st.error(f"Error loading trade history: {e}")

    st.divider()

    # Deep Trade Analysis
    st.subheader("Deep Trade Analysis")

    st.markdown("""
    Select a trade to get detailed post-trade analysis including:
    market structure, entry quality, MFE/MAE, and actionable lessons.
    """)

    # Get trades for selection
    try:
        with db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT trade_id, timestamp, closed_at, instrument, direction, pnl, entry_price, exit_price
                FROM trades WHERE status = 'CLOSED'
                ORDER BY timestamp DESC LIMIT 20
            """)
            analysis_trades = [dict(row) for row in cursor.fetchall()]

        if analysis_trades:
            # Create selection options
            trade_options = {
                f"{t['instrument']} {t['direction']} ({t['pnl']:+.2f}) - {t['timestamp'][:10]}": t
                for t in analysis_trades
            }

            col1, col2 = st.columns([3, 1])

            with col1:
                selected_trade_label = st.selectbox(
                    "Select trade to analyze",
                    options=list(trade_options.keys()),
                    key="trade_analysis_select"
                )

            with col2:
                st.write("")
                st.write("")
                analyze_btn = st.button("Analyze Trade", type="primary", use_container_width=True)

            if analyze_btn and selected_trade_label:
                selected_trade = trade_options[selected_trade_label]

                with st.spinner("Fetching market data and analyzing..."):
                    try:
                        analyzer = PostTradeAnalyzer()
                        result = analyzer.analyze_trade({
                            "trade_id": selected_trade["trade_id"],
                            "instrument": selected_trade["instrument"],
                            "direction": selected_trade["direction"],
                            "entry_price": selected_trade["entry_price"],
                            "exit_price": selected_trade["exit_price"],
                            "opened_at": selected_trade["timestamp"],
                            "closed_at": selected_trade.get("closed_at") or selected_trade["timestamp"],
                            "pnl": selected_trade["pnl"]
                        })

                        # Display results
                        st.markdown("---")

                        # Verdict
                        verdict_colors = {
                            "GOOD_TRADE_WIN": "green",
                            "GOOD_TRADE_LOSS": "orange",
                            "BAD_TRADE_WIN": "yellow",
                            "BAD_TRADE_LOSS": "red",
                            "UNLUCKY": "blue",
                            "PREMATURE_EXIT": "orange"
                        }
                        verdict_text = {
                            "GOOD_TRADE_WIN": "Good trade that worked",
                            "GOOD_TRADE_LOSS": "Valid setup, acceptable loss",
                            "BAD_TRADE_WIN": "Got lucky on poor setup",
                            "BAD_TRADE_LOSS": "Poor setup, expected loss",
                            "UNLUCKY": "Good trade, unfairly stopped",
                            "PREMATURE_EXIT": "Good entry, poor management"
                        }
                        color = verdict_colors.get(result.outcome.value, "gray")
                        verdict = verdict_text.get(result.outcome.value, result.outcome.value)

                        st.markdown(f"### Verdict: :{color}[{verdict}]")

                        # Key metrics in columns
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Entry Quality", result.entry_analysis.quality.value)
                        with col2:
                            st.metric("HTF Trend", result.market_context.htf_trend)
                        with col3:
                            st.metric("MFE", f"{result.excursion.mfe_pips:.0f} pips")
                        with col4:
                            st.metric("MAE", f"{result.excursion.mae_pips:.0f} pips")

                        # Details in expanders
                        with st.expander("Market Context", expanded=True):
                            mc = result.market_context
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"""
                                - **HTF Trend:** {mc.htf_trend}
                                - **LTF Trend:** {mc.ltf_trend}
                                - **Aligned:** {'Yes' if mc.trend_aligned else 'No'}
                                """)
                            with col2:
                                st.markdown(f"""
                                - **RSI at Entry:** {mc.rsi_at_entry:.1f}
                                - **ATR:** {mc.atr_pips:.1f} pips
                                - **Price vs EMA20:** {mc.price_vs_ema20}
                                """)

                        with st.expander("Entry Analysis", expanded=True):
                            ea = result.entry_analysis
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"""
                                - **Quality:** {ea.quality.value}
                                - **Session:** {ea.session.value}
                                - **Killzone:** {'Yes' if ea.was_killzone else 'No'}
                                - **Day:** {ea.day_of_week}
                                """)
                            with col2:
                                st.markdown(f"""
                                - **With Trend:** {'Yes' if ea.with_trend else 'No'}
                                - **At FVG:** {'Yes' if ea.at_fvg else 'No'}
                                - **At Order Block:** {'Yes' if ea.at_order_block else 'No'}
                                - **At S/R:** {'Yes' if ea.at_support_resistance else 'No'}
                                """)

                            if ea.issues:
                                st.markdown("**Issues:**")
                                for issue in ea.issues:
                                    st.markdown(f"- :red[{issue}]")
                            if ea.positives:
                                st.markdown("**Positives:**")
                                for pos in ea.positives:
                                    st.markdown(f"- :green[{pos}]")

                        with st.expander("Excursion Analysis (MFE/MAE)"):
                            ex = result.excursion
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"""
                                **Max Favorable Excursion:**
                                - MFE: **{ex.mfe_pips:.1f} pips** ({ex.mfe_as_multiple_of_risk:.2f}R)
                                - Time to MFE: {ex.time_to_mfe_hours:.1f}h
                                - Reached 1R: {'Yes' if ex.reached_1r_profit else 'No'}
                                - Reached 2R: {'Yes' if ex.reached_2r_profit else 'No'}
                                """)
                            with col2:
                                st.markdown(f"""
                                **Max Adverse Excursion:**
                                - MAE: **{ex.mae_pips:.1f} pips** ({ex.mae_as_multiple_of_risk:.2f}R)
                                - Time to MAE: {ex.time_to_mae_hours:.1f}h
                                - Stop Hunt: {'Detected!' if ex.stop_hunt_detected else 'No'}
                                """)

                        # Lessons and recommendations
                        st.markdown("### Key Findings")
                        for finding in result.findings[:5]:
                            st.markdown(f"- {finding}")

                        st.markdown("### Lessons")
                        for lesson in result.lessons[:3]:
                            st.markdown(f"- :orange[{lesson}]")

                        if result.what_to_do_differently:
                            st.markdown("### Action Items")
                            for rec in result.what_to_do_differently:
                                st.markdown(f"- :blue[{rec}]")

                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
                        import traceback
                        st.code(traceback.format_exc())

        else:
            st.info("No closed trades to analyze. Sync from MT5 or execute trades first.")

    except Exception as e:
        st.warning(f"Could not load trades for analysis: {e}")

    st.divider()

    # Error analysis (RAG)
    st.subheader("Error Analysis (Legacy)")

    error_categories = db.get_error_categories_summary()

    if error_categories:
        st.markdown("**Error Categories:**")

        for category, count in error_categories.items():
            st.markdown(f"- {category}: {count} occurrence(s)")

        # Top repeated errors
        top_errors = db.get_top_repeated_errors(limit=3)
        if top_errors:
            st.markdown("**Most Common Mistakes:**")
            for err in top_errors:
                with st.expander(f"{err['error_category']} - {err['instrument']} ({err['count']}x)"):
                    lessons = err.get('all_lessons', '').split(' | ')
                    for lesson in lessons[:3]:
                        if lesson:
                            st.markdown(f"- {lesson}")
    else:
        st.info("No errors logged yet. Errors from losing trades will appear here for learning.")

    # Minimal status bar
    render_minimal_status()


if __name__ == "__main__":
    main()
