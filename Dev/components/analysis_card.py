"""
Analysis result display components.
"""

import streamlit as st


def render_analysis_card(title: str, content: str, score: int = None, card_type: str = "default"):
    """
    Render an analysis result card.

    Args:
        title: Card title
        content: Card content (markdown supported)
        score: Optional score (0-100)
        card_type: "bullish", "bearish", "neutral", or "default"
    """
    # Determine border color based on type
    border_colors = {
        "bullish": "#10b981",
        "bearish": "#ef4444",
        "neutral": "#f59e0b",
        "default": "#3b82f6"
    }
    border_color = border_colors.get(card_type, border_colors["default"])

    # Build card HTML
    score_html = ""
    if score is not None:
        score_color = "#10b981" if score >= 70 else "#f59e0b" if score >= 50 else "#ef4444"
        score_html = f'<div style="float: right; font-size: 24px; font-weight: bold; color: {score_color};">{score}/100</div>'

    st.markdown(f"""
    <div style="
        background-color: #1e2530;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid {border_color};
        margin: 10px 0;
    ">
        {score_html}
        <h4 style="margin: 0 0 10px 0; color: #e5e7eb;">{title}</h4>
        <div style="color: #9ca3af;">{content}</div>
    </div>
    """, unsafe_allow_html=True)


def render_confidence_meter(confidence: int, risk_tier: str = "", can_trade: bool = True):
    """
    Render a confidence meter visualization.

    Args:
        confidence: Confidence score (0-100)
        risk_tier: Risk tier description
        can_trade: Whether trading is recommended
    """
    # Determine color based on confidence
    if confidence >= 70:
        color = "#10b981"
        status = "HIGH"
    elif confidence >= 50:
        color = "#f59e0b"
        status = "MEDIUM"
    else:
        color = "#ef4444"
        status = "LOW"

    # Trade recommendation
    trade_text = "CAN TRADE" if can_trade else "DO NOT TRADE"
    trade_color = "#10b981" if can_trade else "#ef4444"

    st.markdown(f"""
    <div style="
        background-color: #1e2530;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    ">
        <h4 style="margin: 0 0 15px 0; color: #e5e7eb;">Confidence Score</h4>

        <div style="
            background-color: #374151;
            border-radius: 10px;
            height: 30px;
            overflow: hidden;
        ">
            <div style="
                background-color: {color};
                width: {confidence}%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                transition: width 0.5s ease;
            ">
                {confidence}%
            </div>
        </div>

        <div style="display: flex; justify-content: space-between; margin-top: 15px;">
            <span style="color: #9ca3af;">Status: <strong style="color: {color};">{status}</strong></span>
            <span style="color: {trade_color}; font-weight: bold;">{trade_text}</span>
        </div>

        {f'<div style="color: #9ca3af; margin-top: 10px;">Risk Tier: {risk_tier}</div>' if risk_tier else ''}
    </div>
    """, unsafe_allow_html=True)


def render_bull_bear_case(bull_points: list, bear_points: list, bull_score: float, bear_score: float):
    """
    Render bull vs bear case comparison.

    Args:
        bull_points: List of bullish argument dicts
        bear_points: List of bearish argument dicts
        bull_score: Bull case score
        bear_score: Bear case score
    """
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div style="
            background-color: #1e2530;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #10b981;
        ">
            <h4 style="color: #10b981; margin: 0;">BULL CASE ({bull_score:.0f})</h4>
        </div>
        """, unsafe_allow_html=True)

        for point in bull_points:
            arg = point.get("argument", point) if isinstance(point, dict) else point
            st.markdown(f"- {arg}")

    with col2:
        st.markdown(f"""
        <div style="
            background-color: #1e2530;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #ef4444;
        ">
            <h4 style="color: #ef4444; margin: 0;">BEAR CASE ({bear_score:.0f})</h4>
        </div>
        """, unsafe_allow_html=True)

        for point in bear_points:
            arg = point.get("argument", point) if isinstance(point, dict) else point
            st.markdown(f"- {arg}")


def render_technical_summary(technical_data: dict):
    """
    Render technical analysis summary.

    Args:
        technical_data: Technical analysis dict
    """
    trend = technical_data.get("trend", "N/A")
    trend_color = "#10b981" if trend == "BULLISH" else "#ef4444" if trend == "BEARISH" else "#f59e0b"

    rsi = technical_data.get("rsi", 0)
    rsi_signal = technical_data.get("rsi_signal", "N/A")

    macd_trend = technical_data.get("macd_trend", "N/A")

    st.markdown(f"""
    <div style="
        background-color: #1e2530;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    ">
        <h4 style="margin: 0 0 15px 0; color: #e5e7eb;">Technical Analysis</h4>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div>
                <span style="color: #9ca3af;">Trend:</span>
                <span style="color: {trend_color}; font-weight: bold;"> {trend}</span>
            </div>
            <div>
                <span style="color: #9ca3af;">Strength:</span>
                <span style="color: #e5e7eb;"> {technical_data.get('trend_strength', 0):.0f}%</span>
            </div>
            <div>
                <span style="color: #9ca3af;">RSI(14):</span>
                <span style="color: #e5e7eb;"> {rsi:.1f} ({rsi_signal})</span>
            </div>
            <div>
                <span style="color: #9ca3af;">MACD:</span>
                <span style="color: #e5e7eb;"> {macd_trend}</span>
            </div>
            <div>
                <span style="color: #9ca3af;">ATR:</span>
                <span style="color: #e5e7eb;"> {technical_data.get('atr_pips', 0):.1f} pips</span>
            </div>
            <div>
                <span style="color: #9ca3af;">Score:</span>
                <span style="color: #e5e7eb;"> {technical_data.get('technical_score', 0)}/100</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
