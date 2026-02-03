"""
AI Trader - Analysis Page

Technical analysis with charts, AI recommendation, and trade execution.
"""

import streamlit as st
import pandas as pd
import sys
import time
from datetime import datetime
from pathlib import Path

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.utils.config import config
from src.trading.mt5_client import MT5Client, MT5Error
from src.trading.orders import OrderManager
from src.trading.position_sizer import calculate_position_size, get_risk_tier
from src.market.indicators import TechnicalAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.analysis.adversarial import AdversarialEngine
from src.analysis.confidence import ConfidenceCalculator
from src.analysis.llm_engine import LLMEngine
from src.core.settings_manager import settings_manager
from src.utils.database import db
from src.utils.instrument_profiles import get_profile, is_in_session
from components.tooltips import (
    metric_with_tooltip,
    tooltip_text,
    ICONS,
    simple_explanation_section,
    get_tooltip,
)
from components.status_bar import render_status_bar, get_status_bar_data
from components.mt5_session import get_client, reset_connection

st.set_page_config(page_title="Analysis - AI Trader", page_icon="", layout="wide")


def execute_trade(
    instrument: str,
    direction: str,
    units: int,
    stop_loss: float,
    take_profit: float,
    confidence: int,
    risk_amount: float
):
    """Execute trade via OrderManager with risk validation."""
    try:
        client = get_client()
        if not client:
            return False, "Not connected to MT5"

        om = OrderManager(client)

        # Convert direction to units sign
        trade_units = units if direction == "LONG" else -units

        result = om.open_position(
            instrument=instrument,
            units=trade_units,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            risk_amount=risk_amount
        )

        if result.success:
            return True, f"Trade executed! Order #{result.order_id} @ {result.price:.5f}"
        else:
            return False, f"Trade failed: {result.error}"

    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    st.title("Technical Analysis")

    client = get_client()

    if not st.session_state.connected:
        st.error("Not connected to MT5")
        if st.button("Reconnect MT5"):
            reset_connection()
            st.rerun()
        return

    # Controls
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        pairs = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF", "EUR_GBP", "EUR_JPY", "GBP_JPY", "BTC_USD"]
        instrument = st.selectbox("Currency Pair", pairs, format_func=lambda x: x.replace("_", "/"))

    with col2:
        timeframes = ["M15", "M30", "H1", "H4", "D1"]
        timeframe = st.selectbox("Timeframe", timeframes, index=2)

    with col3:
        candle_count = st.number_input("Candles", min_value=50, max_value=500, value=100)

    profile = get_profile(instrument)

    # Skill focus selector
    skills = ["None"] + settings_manager.list_skills()
    skill_focus = st.selectbox(
        "Skill Focus",
        skills,
        help="Optional: focus analysis on a specific skill/strategy"
    )
    llm_engine = LLMEngine()
    llm_available, llm_reason = llm_engine.status()
    st.caption(f"LLM Status: {'Enabled' if llm_available else 'Disabled'} - {llm_reason}")

    # View mode toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        view_mode = st.radio(
            "View Mode",
            options=["Simple", "Detailed"],
            horizontal=True,
            key="analysis_view_mode",
            help="Simple: Key metrics only. Detailed: Full technical analysis."
        )
    # view_mode is automatically stored in session_state via key

    if st.button("Run Analysis", type="primary"):
        try:
            with st.spinner("Running AI analysis..."):
                if not is_in_session(profile):
                    st.warning("Outside allowed trading session for this instrument.")

                # Get price
                price = client.get_price(instrument)

                max_spread = profile.get("max_spread_pips")
                if max_spread is not None and price["spread_pips"] > max_spread:
                    st.warning(f"Spread too high for this instrument ({price['spread_pips']:.1f} > {max_spread})")

                # Get candles
                candles = client.get_candles(instrument, timeframe, candle_count)

                if len(candles) < 20:
                    st.error("Not enough candle data")
                    return

                # Get account for position sizing
                account = client.get_account()

                # === AI ANALYSIS PIPELINE ===

                # 1. Technical analysis
                tech_analyzer = TechnicalAnalyzer()
                technical = tech_analyzer.analyze(candles, instrument)

                min_atr = profile.get("min_atr_pips")
                if min_atr is not None and technical.atr_pips < min_atr:
                    st.warning(f"Volatility too low (ATR {technical.atr_pips:.1f} < {min_atr})")

                # 2. Sentiment analysis
                sent_analyzer = SentimentAnalyzer()
                sentiment = sent_analyzer.analyze(candles, technical)

                # 3. Determine direction for adversarial
                if technical.trend == "BULLISH":
                    direction = "LONG"
                elif technical.trend == "BEARISH":
                    direction = "SHORT"
                else:
                    direction = "LONG"  # Default

                # 4. Adversarial analysis
                adv_engine = AdversarialEngine()
                adversarial = adv_engine.analyze(
                    technical=technical,
                    sentiment=sentiment,
                    instrument=instrument,
                    direction=direction,
                    current_price=price["bid"]
                )

                # 5. Confidence calculation
                conf_calc = ConfidenceCalculator()
                confidence = conf_calc.calculate(
                    technical=technical,
                    sentiment=sentiment,
                    adversarial=adversarial
                )

                # 6. Calculate trade parameters
                current_price = price["ask"] if direction == "LONG" else price["bid"]
                atr = technical.atr

                if direction == "LONG":
                    stop_loss = current_price - (atr * 2)
                    take_profit = current_price + (atr * 4)
                else:
                    stop_loss = current_price + (atr * 2)
                    take_profit = current_price - (atr * 4)

                # 7. Position sizing
                position_size = calculate_position_size(
                    equity=account["nav"],
                    confidence=confidence.confidence_score,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    instrument=instrument
                )

                # Store for display
                st.session_state.analysis_result = {
                    "price": price,
                    "candles": candles,
                    "technical": technical,
                    "sentiment": sentiment,
                    "adversarial": adversarial,
                    "confidence": confidence,
                    "instrument": instrument,
                    "timeframe": timeframe,
                    "direction": direction,
                    "current_price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "position_size": position_size,
                    "account": account
                }

                # LLM advisory (optional)
                llm_result = None
                if llm_engine.is_available():
                    selected_skill = None if skill_focus == "None" else skill_focus
                    skill_content = settings_manager.get_skill(selected_skill) if selected_skill else None
                    with st.spinner("Running LLM analysis..."):
                        llm_result = llm_engine.analyze(
                            instrument=instrument,
                            price=price,
                            technical=technical,
                            sentiment=sentiment,
                            adversarial=adversarial,
                            rag_errors=[],
                            skill_name=selected_skill,
                            skill_content=skill_content
                        )
                    st.session_state.llm_result = llm_result
                    st.session_state.llm_skill_excerpt = None
                    if skill_content:
                        excerpt = skill_content.strip()
                        if len(excerpt) > 800:
                            excerpt = excerpt[:800] + "\n... (truncated)"
                        st.session_state.llm_skill_excerpt = excerpt

                    # Timeline log
                    if "llm_timeline" not in st.session_state:
                        st.session_state.llm_timeline = []
                    st.session_state.llm_timeline.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "instrument": instrument,
                        "skill": selected_skill or "None",
                        "model": llm_result.model if llm_result else "n/a",
                        "latency_ms": llm_result.latency_ms if llm_result else None
                    })
                    if llm_result:
                        try:
                            db.log_llm_decision({
                                "instrument": instrument,
                                "recommendation": llm_result.recommendation,
                                "direction": llm_result.direction,
                                "confidence_adjustment": llm_result.confidence_adjustment,
                                "summary": llm_result.summary,
                                "risk_notes": llm_result.risk_notes,
                                "strategy_notes": llm_result.strategy_notes,
                                "approved": 0,
                                "executed": 0
                            })
                        except Exception:
                            pass

        except MT5Error as e:
            st.error(f"Analysis failed: {e}")
        except Exception as e:
            st.error(f"Error: {e}")
            import traceback
            st.code(traceback.format_exc())

    # Display results if available
    if "analysis_result" in st.session_state and st.session_state.analysis_result:
        result = st.session_state.analysis_result
        technical = result["technical"]
        sentiment = result["sentiment"]
        adversarial = result["adversarial"]
        confidence = result["confidence"]
        price = result["price"]
        candles = result["candles"]

        st.divider()

        # Price header
        pair_display = result["instrument"].replace("_", "/")
        st.subheader(f"{pair_display} - {result['timeframe']}")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Bid", f"{price['bid']:.5f}")
        with col2:
            st.metric("Ask", f"{price['ask']:.5f}")
        with col3:
            st.metric("Spread", f"{price['spread_pips']:.1f} pips")

        st.divider()

        # ============================================
        # AI RECOMMENDATION SECTION
        # ============================================
        st.subheader("AI Recommendation")

        # Confidence score with big display
        conf_score = confidence.confidence_score
        conf_color = "green" if conf_score >= 70 else "orange" if conf_score >= 50 else "red"

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            metric_with_tooltip("Confidence", f"{conf_score}%", "confidence")
        with col2:
            metric_with_tooltip("Risk Tier", confidence.risk_tier, "risk_tier")
        with col3:
            dir_color = "green" if result["direction"] == "LONG" else "red"
            st.metric("Direction", result["direction"],
                     help="LONG = expecting price to go UP. SHORT = expecting price to go DOWN.")
        with col4:
            metric_with_tooltip("Verdict", adversarial.verdict, "verdict")

        # Trade parameters
        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Entry Price", f"{result['current_price']:.5f}",
                     help="The price at which the trade would be opened.")
        with col2:
            sl_pips = abs(result['current_price'] - result['stop_loss']) / (0.01 if "JPY" in result["instrument"] else 0.0001)
            metric_with_tooltip("Stop Loss", f"{result['stop_loss']:.5f}", "stop_loss", delta=f"-{sl_pips:.0f} pips")
        with col3:
            tp_pips = abs(result['take_profit'] - result['current_price']) / (0.01 if "JPY" in result["instrument"] else 0.0001)
            metric_with_tooltip("Take Profit", f"{result['take_profit']:.5f}", "take_profit", delta=f"+{tp_pips:.0f} pips")
        with col4:
            pos_size = result["position_size"]
            if pos_size.can_trade:
                st.metric("Position Size", f"{pos_size.units:,} units",
                         help="Number of currency units to trade, calculated based on your risk settings.")
            else:
                st.metric("Position Size", "N/A",
                         help="Position size could not be calculated. Check confidence level.")

        # Risk info
        if result["position_size"].can_trade:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"Risk: {result['position_size'].risk_percent*100:.0f}% = ${result['position_size'].risk_amount:.2f}")
            with col2:
                st.info(f"Risk:Reward = 1:2")
            with col3:
                st.info(f"Account: ${result['account']['nav']:,.2f}")

        # ============================================
        # EXECUTE TRADE BUTTON
        # ============================================
        st.markdown("---")

        # LLM advisory
        llm_result = st.session_state.get("llm_result")
        if llm_result:
            st.subheader("LLM Advisory (Skill-Aware)")
            st.caption(
                f"Model: {llm_result.model} | "
                f"Latency: {llm_result.latency_ms} ms | "
                f"Tokens: {llm_result.input_tokens or 'n/a'}/{llm_result.output_tokens or 'n/a'} | "
                f"Skill: {llm_result.skill_used or 'None'} | "
                f"Knowledge: {'Yes' if llm_result.knowledge_included else 'No'}"
            )
            st.markdown(
                f"**Bias:** {llm_result.bias}\n\n"
                f"**Recommendation:** {llm_result.recommendation}\n\n"
                f"**Direction:** {llm_result.direction}\n\n"
                f"**Summary:** {llm_result.summary}"
            )
            if llm_result.risk_notes:
                st.markdown("**Risks:**\n" + "\n".join([f"- {r}" for r in llm_result.risk_notes]))
            if llm_result.strategy_notes:
                st.markdown("**Strategy Notes:**\n" + "\n".join([f"- {s}" for s in llm_result.strategy_notes]))
            with st.expander("Show raw LLM output"):
                st.code(llm_result.raw or "")
            skill_excerpt = st.session_state.get("llm_skill_excerpt")
            if skill_excerpt:
                with st.expander("Show skill excerpt used in prompt"):
                    st.code(skill_excerpt)
            timeline = st.session_state.get("llm_timeline", [])
            if timeline:
                with st.expander("LLM Timeline"):
                    for item in timeline[-10:][::-1]:
                        st.markdown(
                            f"- **{item['time']}** {item['instrument']} | "
                            f"Skill: {item['skill']} | Model: {item['model']} | "
                            f"Latency: {item['latency_ms']} ms"
                        )
            st.markdown("---")

        if confidence.can_trade and result["position_size"].can_trade:
            col1, col2, col3 = st.columns([1, 2, 1])

            with col2:
                # Confirmation checkbox
                confirm = st.checkbox(
                    f"I confirm: {result['direction']} {result['position_size'].units:,} units with {result['position_size'].risk_percent*100:.0f}% risk",
                    key="trade_confirm"
                )

                button_color = "primary" if result["direction"] == "LONG" else "secondary"

                if st.button(
                    f"EXECUTE {result['direction']} TRADE",
                    type=button_color,
                    disabled=not confirm,
                    use_container_width=True
                ):
                    with st.spinner("Executing trade..."):
                        success, message = execute_trade(
                            instrument=result["instrument"],
                            direction=result["direction"],
                            units=result["position_size"].units,
                            stop_loss=result["stop_loss"],
                            take_profit=result["take_profit"],
                            confidence=result["confidence"].confidence_score,
                            risk_amount=result["position_size"].risk_amount
                        )

                        if success:
                            st.success(message)
                            st.balloons()
                            # Clear analysis after successful trade
                            st.session_state.analysis_result = None
                        else:
                            st.error(message)

                if not confirm:
                    st.caption("Check the box above to enable trade execution")

        else:
            st.warning(f"Trade not recommended: {confidence.risk_tier}")
            if conf_score < 50:
                st.info("Confidence is below 50% - AI suggests waiting for better setup")

        st.divider()

        # ============================================
        # DETAILED ANALYSIS (only show in Detailed mode)
        # ============================================

        # Get view mode from session state
        current_view_mode = st.session_state.get("analysis_view_mode", "Detailed")

        if current_view_mode == "Simple":
            # Simple mode: Show just the summary
            st.subheader("Summary")

            # Simple trend indicator
            trend_icon = "[^]" if technical.trend == "BULLISH" else "[v]" if technical.trend == "BEARISH" else "[-]"
            trend_color = "green" if technical.trend == "BULLISH" else "red" if technical.trend == "BEARISH" else "orange"

            st.markdown(f"""
            **Market is :{trend_color}[{technical.trend}]** {trend_icon}

            - **Trend Strength:** {technical.trend_strength:.0f}%
            - **RSI:** {technical.rsi:.1f} ({technical.rsi_signal})
            - **MACD:** {technical.macd_trend}
            - **Volatility (ATR):** {technical.atr_pips:.1f} pips

            **AI says:** {adversarial.verdict} with {conf_score}% confidence
            """)

            if adversarial.warnings:
                st.warning(f"Warnings: " + ", ".join(adversarial.warnings))

            # Show key levels only
            col1, col2 = st.columns(2)
            with col1:
                if technical.nearest_support:
                    st.info(f"Support: {technical.nearest_support:.5f} ({technical.distance_to_support_pips:.1f} pips away)")
            with col2:
                if technical.nearest_resistance:
                    st.info(f"Resistance: {technical.nearest_resistance:.5f} ({technical.distance_to_resistance_pips:.1f} pips away)")

        else:
            # Detailed mode: Show full analysis
            # Technical indicators
            st.subheader("Technical Indicators")

            # Simple explanation expander
            with st.expander(f"{ICONS['question']} Explain these indicators simply"):
                st.markdown("""
    **What am I looking at?**

    These indicators help predict where the price might go:

    - **Trend** shows if the market is going UP (bullish), DOWN (bearish), or SIDEWAYS (neutral)
    - **RSI** tells you if the price has moved too far, too fast. Above 70 = might drop soon. Below 30 = might rise soon.
    - **MACD** shows momentum - is the trend getting stronger or weaker?
    - **ATR** tells you how much the price typically moves - higher = more volatile
                """)

            col1, col2 = st.columns(2)

            with col1:
                # Trend
                trend_color = "green" if technical.trend == "BULLISH" else "red" if technical.trend == "BEARISH" else "orange"
                st.markdown(f"**Trend:** :{trend_color}[{technical.trend}] (strength: {technical.trend_strength:.0f}%)")
                st.caption(tooltip_text("trend"))

                st.markdown(f"""
                **Moving Averages:**
                - EMA(20): {technical.ema20:.5f}
                - EMA(50): {technical.ema50:.5f}
                - Price vs EMA20: {technical.price_vs_ema20}
                """)

                # RSI gauge
                rsi_color = "red" if technical.rsi >= 70 else "green" if technical.rsi <= 30 else "blue"
                st.markdown(f"**RSI(14):** :{rsi_color}[{technical.rsi:.1f}] - {technical.rsi_signal}")
                st.caption(tooltip_text("rsi"))

            with col2:
                # MACD
                macd_color = "green" if technical.macd_trend == "BULLISH" else "red"
                st.markdown(f"**MACD:** :{macd_color}[{technical.macd_trend}]")
                st.caption(tooltip_text("macd"))
                st.markdown(f"- MACD Line: {technical.macd:.5f}")
                st.markdown(f"- Signal Line: {technical.macd_signal:.5f}")
                st.markdown(f"- Histogram: {technical.macd_histogram:.5f}")

                # ATR
                st.markdown(f"**ATR(14):** {technical.atr_pips:.1f} pips")
                st.caption(tooltip_text("atr"))

            st.divider()

            # Sentiment Analysis
            st.subheader("Sentiment Analysis")

            col1, col2 = st.columns(2)

            with col1:
                sent_color = "green" if sentiment.sentiment_score > 0.3 else "red" if sentiment.sentiment_score < -0.3 else "orange"
                st.markdown(f"**Sentiment:** :{sent_color}[{sentiment.sentiment_label}] ({sentiment.sentiment_score:+.2f})")
                st.markdown(f"- Price Action: {sentiment.price_action_score:+.2f}")
                st.markdown(f"- Momentum: {sentiment.momentum_score:+.2f}")

            with col2:
                st.markdown(f"**Trend Direction:** {sentiment.trend_direction}")
                st.markdown(f"**Is Trending:** {'Yes' if sentiment.is_trending else 'No'}")

            st.divider()

            # Adversarial Analysis
            st.subheader("Adversarial Analysis (Bull vs Bear)")

            with st.expander(f"{ICONS['question']} What is adversarial analysis?"):
                st.markdown("""
    The AI debates with itself! It creates two personas:

    - **Bull Case** - Argues why the price should go UP
    - **Bear Case** - Argues why the price should go DOWN

    Whichever side has stronger arguments influences the final decision.
    This helps avoid bias and catch risks you might miss.
                """)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**{ICONS['bull']} BULL CASE**")
                for point in adversarial.bull_case[:5]:
                    st.markdown(f"- {point.argument}")
                metric_with_tooltip("Bull Score", f"{adversarial.bull_score:.0f}/100", "bull_score")

            with col2:
                st.markdown(f"**{ICONS['bear']} BEAR CASE**")
                for point in adversarial.bear_case[:5]:
                    st.markdown(f"- {point.argument}")
                metric_with_tooltip("Bear Score", f"{adversarial.bear_score:.0f}/100", "bear_score")

            if adversarial.warnings:
                st.warning(f"**{ICONS['warning']} Warnings:** " + ", ".join(adversarial.warnings))

            st.divider()

            # Support/Resistance
            st.subheader("Support & Resistance")

            col1, col2 = st.columns(2)

            with col1:
                if technical.nearest_support:
                    st.metric(
                        "Nearest Support",
                        f"{technical.nearest_support:.5f}",
                        delta=f"{technical.distance_to_support_pips:.1f} pips away"
                    )
                else:
                    st.info("No support level found")

            with col2:
                if technical.nearest_resistance:
                    st.metric(
                        "Nearest Resistance",
                        f"{technical.nearest_resistance:.5f}",
                        delta=f"{technical.distance_to_resistance_pips:.1f} pips away"
                    )
                else:
                    st.info("No resistance level found")

            st.divider()

            # Overall score
            st.subheader("Confidence Breakdown")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Technical", f"{confidence.technical_score}/100",
                         help="Score based on technical indicators (trend, RSI, MACD).")
            with col2:
                st.metric("Sentiment", f"{confidence.sentiment_score}/100",
                         help="Score based on price action and momentum analysis.")
            with col3:
                st.metric("Adversarial Adj.", f"{confidence.adversarial_adjustment:+d}",
                         help="Adjustment from bull vs bear debate. Positive = supports the trade, negative = caution advised.")
            with col4:
                metric_with_tooltip("Final Score", f"{confidence.confidence_score}/100", "confidence")

            st.progress(confidence.confidence_score / 100)

            # Simple interpretation
            if conf_score >= 70:
                st.success(f"**High confidence ({conf_score}%)** - The AI sees a good trading opportunity with strong supporting signals.")
            elif conf_score >= 50:
                st.info(f"**Medium confidence ({conf_score}%)** - The setup is acceptable but not ideal. Consider using smaller position size.")
            else:
                st.warning(f"**Low confidence ({conf_score}%)** - The AI does not recommend trading. Wait for a clearer setup.")

            # Price chart
            st.divider()
            st.subheader("Price Chart")

            # Convert candles to DataFrame for charting
            df = pd.DataFrame(candles)
            df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)

            # Simple line chart of close prices
            st.line_chart(df['close'], use_container_width=True)

            # Show raw data option
            with st.expander("View Raw Data"):
                st.dataframe(df[['open', 'high', 'low', 'close', 'volume']].tail(20))

    # Status bar at bottom
    if st.session_state.connected:
        status_data = get_status_bar_data(client, config)
        render_status_bar(**status_data)


if __name__ == "__main__":
    main()
