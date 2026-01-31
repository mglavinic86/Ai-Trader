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
from components.empty_states import render_minimal_status

st.set_page_config(page_title="History - AI Trader", page_icon="", layout="wide")


def main():
    st.title("Trade History")

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

    # Error analysis (RAG)
    st.subheader("Error Analysis")

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
