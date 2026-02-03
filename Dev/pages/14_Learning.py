"""
AI Trader - Learning Dashboard

Shows what the AI has learned from past trades:
- Pattern statistics (win rates by instrument, session, trend, etc.)
- Best and worst performing patterns
- Trade analysis history
- Bootstrap learning from existing trades
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path
from datetime import datetime

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.utils.database import db
from src.analysis.learning_engine import LearningEngine
from src.utils.mt5_sync import bootstrap_learning
from components.status_bar import render_status_bar, get_status_bar_data
from components.mt5_session import get_client, is_connected

st.set_page_config(page_title="Learning - AI Trader", page_icon="", layout="wide")


# =============================================================================
# DATA FETCHING
# =============================================================================


def get_pattern_stats() -> list:
    """Fetch all pattern statistics from database."""
    try:
        with db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    pattern_type,
                    pattern_value,
                    instrument,
                    direction,
                    total_trades,
                    winning_trades,
                    losing_trades,
                    total_pnl_pips,
                    total_pnl_amount,
                    avg_mfe_pips,
                    avg_mae_pips,
                    last_updated
                FROM pattern_stats
                WHERE total_trades > 0
                ORDER BY total_trades DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"Error fetching pattern stats: {e}")
        return []


def get_trade_analyses() -> list:
    """Fetch all trade analyses from database."""
    try:
        with db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    trade_id,
                    instrument,
                    direction,
                    pnl_pips,
                    pnl_amount,
                    duration_hours,
                    htf_trend,
                    ltf_trend,
                    trend_aligned,
                    entry_quality,
                    session,
                    was_killzone,
                    day_of_week,
                    with_trend,
                    mfe_pips,
                    mae_pips,
                    outcome,
                    was_good_trade,
                    findings,
                    lessons,
                    created_at
                FROM trade_analyses
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"Error fetching trade analyses: {e}")
        return []


def get_unanalyzed_trades_count() -> int:
    """Get count of trades that haven't been analyzed yet."""
    try:
        with db._connection() as conn:
            cursor = conn.cursor()
            # Get closed trades
            cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'CLOSED'")
            total_closed = cursor.fetchone()[0]

            # Get analyzed trades
            cursor.execute("SELECT COUNT(*) FROM trade_analyses")
            analyzed = cursor.fetchone()[0]

            return max(0, total_closed - analyzed)
    except Exception:
        return 0


# =============================================================================
# COMPONENTS
# =============================================================================


def render_learning_summary():
    """Render learning summary metrics."""
    st.subheader("Learning Summary")

    le = LearningEngine()
    summary = le.get_learning_summary()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Trades Analyzed",
            summary.get("total_trades_analyzed", 0)
        )

    with col2:
        st.metric(
            "Instruments Tracked",
            len(summary.get("instruments", {}))
        )

    with col3:
        best_patterns = summary.get("best_patterns", [])
        if best_patterns:
            st.metric(
                "Best Win Rate",
                f"{best_patterns[0]['win_rate']}%"
            )
        else:
            st.metric("Best Win Rate", "N/A")

    with col4:
        unanalyzed = get_unanalyzed_trades_count()
        st.metric(
            "Unanalyzed Trades",
            unanalyzed,
            delta=f"-{unanalyzed}" if unanalyzed > 0 else None,
            delta_color="inverse"
        )

    # Key insights
    if summary.get("key_insights"):
        st.markdown("**Key Insights:**")
        for insight in summary["key_insights"]:
            st.info(insight)


def render_instrument_stats(summary: dict):
    """Render instrument-specific statistics."""
    st.subheader("Performance by Instrument")

    instruments = summary.get("instruments", {})
    if not instruments:
        st.info("No instrument data yet. Analyze some trades first.")
        return

    # Create dataframe
    data = []
    for inst, stats in instruments.items():
        data.append({
            "Instrument": inst,
            "Trades": stats["total_trades"],
            "Win Rate": f"{stats['win_rate']:.1f}%",
            "PnL (pips)": f"{stats['total_pnl_pips']:.1f}",
            "PnL (EUR)": f"{stats['total_pnl_amount']:.2f}"
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Chart
    if len(instruments) > 0:
        fig = px.bar(
            df,
            x="Instrument",
            y=[float(x.replace('%', '')) for x in df["Win Rate"]],
            title="Win Rate by Instrument",
            color=[float(x.replace('%', '')) for x in df["Win Rate"]],
            color_continuous_scale=["red", "yellow", "green"]
        )
        fig.update_layout(showlegend=False, yaxis_title="Win Rate (%)")
        st.plotly_chart(fig, use_container_width=True)


def render_pattern_stats():
    """Render pattern statistics table and charts."""
    st.subheader("Pattern Statistics")

    patterns = get_pattern_stats()
    if not patterns:
        st.info("No pattern data yet. Analyze some trades first.")
        return

    # Group by pattern type
    pattern_types = {}
    for p in patterns:
        p_type = p["pattern_type"]
        if p_type not in pattern_types:
            pattern_types[p_type] = []
        pattern_types[p_type].append(p)

    # Tabs for different pattern types
    tabs = st.tabs(list(pattern_types.keys())[:8])  # Limit to 8 tabs

    for tab, (p_type, p_list) in zip(tabs, list(pattern_types.items())[:8]):
        with tab:
            data = []
            for p in p_list:
                win_rate = p["winning_trades"] / p["total_trades"] * 100 if p["total_trades"] > 0 else 0
                inst_str = f" ({p['instrument']})" if p['instrument'] else ""
                dir_str = f" [{p['direction']}]" if p['direction'] else ""

                data.append({
                    "Pattern": f"{p['pattern_value']}{inst_str}{dir_str}",
                    "Trades": p["total_trades"],
                    "Wins": p["winning_trades"],
                    "Losses": p["losing_trades"],
                    "Win Rate": win_rate,
                    "PnL (pips)": p["total_pnl_pips"] or 0,
                    "Avg MFE": p["avg_mfe_pips"] or 0,
                    "Avg MAE": p["avg_mae_pips"] or 0
                })

            df = pd.DataFrame(data)

            # Color code by win rate
            def highlight_win_rate(val):
                if val >= 60:
                    return 'background-color: #2e7d32; color: white'
                elif val >= 50:
                    return 'background-color: #f9a825'
                elif val < 40:
                    return 'background-color: #c62828; color: white'
                return ''

            styled_df = df.style.applymap(highlight_win_rate, subset=['Win Rate'])
            styled_df = styled_df.format({
                'Win Rate': '{:.1f}%',
                'PnL (pips)': '{:.1f}',
                'Avg MFE': '{:.1f}',
                'Avg MAE': '{:.1f}'
            })

            st.dataframe(styled_df, use_container_width=True, hide_index=True)


def render_best_worst_patterns():
    """Render best and worst performing patterns."""
    col1, col2 = st.columns(2)

    le = LearningEngine()
    summary = le.get_learning_summary()

    with col1:
        st.subheader("Best Patterns")
        best = summary.get("best_patterns", [])
        if best:
            for i, p in enumerate(best[:5], 1):
                st.success(f"**{i}. {p['pattern']}**\n\nWin Rate: {p['win_rate']}% ({p['trades']} trades)")
        else:
            st.info("Not enough data yet")

    with col2:
        st.subheader("Worst Patterns")
        worst = summary.get("worst_patterns", [])
        if worst:
            for i, p in enumerate(worst[:5], 1):
                st.error(f"**{i}. {p['pattern']}**\n\nWin Rate: {p['win_rate']}% ({p['trades']} trades)")
        else:
            st.info("Not enough data yet")


def render_trade_analyses():
    """Render trade analyses history."""
    st.subheader("Trade Analyses History")

    analyses = get_trade_analyses()
    if not analyses:
        st.info("No trade analyses yet. Trades will be automatically analyzed when they close.")
        return

    for analysis in analyses[:20]:  # Show last 20
        outcome = analysis.get("outcome", "UNKNOWN")
        was_good = analysis.get("was_good_trade", False)

        # Color based on outcome
        if "WIN" in outcome:
            icon = "" if was_good else ""
            container = st.success if was_good else st.warning
        else:
            icon = "" if was_good else ""
            container = st.warning if was_good else st.error

        with st.expander(
            f"{icon} {analysis['instrument']} {analysis['direction']} | "
            f"{analysis['pnl_pips']:.1f} pips | {outcome}"
        ):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Market Context**")
                st.write(f"HTF Trend: {analysis.get('htf_trend', 'N/A')}")
                st.write(f"LTF Trend: {analysis.get('ltf_trend', 'N/A')}")
                st.write(f"Aligned: {'Yes' if analysis.get('trend_aligned') else 'No'}")

            with col2:
                st.markdown("**Entry Analysis**")
                st.write(f"Quality: {analysis.get('entry_quality', 'N/A')}")
                st.write(f"Session: {analysis.get('session', 'N/A')}")
                st.write(f"Killzone: {'Yes' if analysis.get('was_killzone') else 'No'}")
                st.write(f"With Trend: {'Yes' if analysis.get('with_trend') else 'No'}")

            with col3:
                st.markdown("**Excursion**")
                st.write(f"MFE: {analysis.get('mfe_pips', 0):.1f} pips")
                st.write(f"MAE: {analysis.get('mae_pips', 0):.1f} pips")
                st.write(f"Duration: {analysis.get('duration_hours', 0):.1f} hours")

            # Findings
            findings = analysis.get("findings")
            if findings:
                import json
                try:
                    findings_list = json.loads(findings) if isinstance(findings, str) else findings
                    if findings_list:
                        st.markdown("**Findings:**")
                        for f in findings_list:
                            st.write(f"- {f}")
                except:
                    pass

            # Lessons
            lessons = analysis.get("lessons")
            if lessons:
                import json
                try:
                    lessons_list = json.loads(lessons) if isinstance(lessons, str) else lessons
                    if lessons_list:
                        st.markdown("**Lessons:**")
                        for l in lessons_list:
                            st.write(f"- {l}")
                except:
                    pass


def render_bootstrap_section():
    """Render bootstrap learning section."""
    st.subheader("Bootstrap Learning")

    unanalyzed = get_unanalyzed_trades_count()

    if unanalyzed > 0:
        st.warning(f"There are **{unanalyzed}** closed trades that haven't been analyzed yet.")

        if st.button("Analyze All Unanalyzed Trades", type="primary"):
            with st.spinner("Analyzing trades... This may take a moment."):
                result = bootstrap_learning(days=365)

                if result.get("success"):
                    st.success(
                        f"Bootstrap complete!\n\n"
                        f"- Trades analyzed: {result.get('trades_analyzed', 0)}\n"
                        f"- Already done: {result.get('already_analyzed', 0)}\n"
                        f"- Patterns updated: {result.get('patterns_total', 0)}"
                    )
                    st.rerun()
                else:
                    st.error(f"Bootstrap failed: {result.get('message', 'Unknown error')}")
    else:
        st.success("All trades have been analyzed!")


def render_current_insights():
    """Render insights for current trading conditions."""
    st.subheader("Current Trade Insights")

    le = LearningEngine()

    # Get configured instruments
    try:
        import json
        config_path = DEV_DIR / "settings" / "auto_trading.json"
        with open(config_path) as f:
            config = json.load(f)
        instruments = config.get("instruments", ["EUR_USD", "GBP_USD", "USD_JPY"])
    except:
        instruments = ["EUR_USD", "GBP_USD", "USD_JPY"]

    # Get current hour for session detection
    from datetime import timezone
    now = datetime.now(timezone.utc)
    hour = now.hour

    # Detect session
    if 0 <= hour < 8:
        session = "ASIAN"
    elif 7 <= hour < 16:
        session = "LONDON"
    elif 12 <= hour < 21:
        session = "NEW_YORK"
    else:
        session = "OFF_HOURS"

    st.info(f"Current session: **{session}** (UTC: {now.strftime('%H:%M')})")

    cols = st.columns(min(len(instruments), 3))

    for i, inst in enumerate(instruments[:6]):
        col = cols[i % 3]

        with col:
            st.markdown(f"**{inst}**")

            for direction in ["LONG", "SHORT"]:
                insights = le.get_insights_for_trade(
                    inst, direction,
                    {"session": session, "with_trend": True}
                )

                # Show quality score
                score = insights.trade_quality_score
                if score >= 60:
                    st.success(f"{direction}: Quality {score}/100")
                elif score >= 40:
                    st.warning(f"{direction}: Quality {score}/100")
                else:
                    st.error(f"{direction}: Quality {score}/100")

                # Show adjustment
                if insights.confidence_adjustment != 0:
                    st.caption(f"Confidence adj: {insights.confidence_adjustment:+d}%")

                # Show warnings
                for w in insights.warnings[:2]:
                    st.caption(f"- {w}")


# =============================================================================
# MAIN PAGE
# =============================================================================


def main():
    st.title("Learning Dashboard")
    st.markdown("*What the AI has learned from past trades*")

    # Status bar
    if is_connected():
        client = get_client()
        status_data = get_status_bar_data(client)
        render_status_bar(status_data)

    st.divider()

    # Summary section
    render_learning_summary()

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Pattern Stats",
        "Best/Worst",
        "Trade History",
        "Current Insights",
        "Bootstrap"
    ])

    with tab1:
        render_pattern_stats()

    with tab2:
        le = LearningEngine()
        summary = le.get_learning_summary()
        render_best_worst_patterns()
        st.divider()
        render_instrument_stats(summary)

    with tab3:
        render_trade_analyses()

    with tab4:
        render_current_insights()

    with tab5:
        render_bootstrap_section()

        st.divider()
        st.markdown("### Manual Refresh")
        if st.button("Refresh Learning Data"):
            st.rerun()


if __name__ == "__main__":
    main()
