"""
Tooltips and metric explanations for AI Trader dashboard.

Provides contextual help and simple explanations for trading metrics
to make the dashboard accessible to beginners.
"""

import streamlit as st
from typing import Optional, Any

# =============================================================================
# WINDOWS-SAFE ICONS
# =============================================================================
# Using simple Unicode that renders correctly on Windows

ICONS = {
    "info": "[i]",
    "warning": "[!]",
    "success": "[+]",
    "error": "[x]",
    "bull": "[^]",
    "bear": "[v]",
    "neutral": "[-]",
    "trade": "[T]",
    "money": "[$]",
    "chart": "[~]",
    "alert": "[*]",
    "question": "[?]",
    "check": "[ok]",
    "cross": "[no]",
    "arrow_up": ">>",
    "arrow_down": "<<",
    "dot": "*",
    # Monitoring icons
    "health": "[H]",
    "monitor": "[M]",
    "list": "[=]",
    "settings": "[S]",
    "pending": "[.]",
}


# =============================================================================
# METRIC TOOLTIPS - Simple explanations for all trading metrics
# =============================================================================

METRIC_TOOLTIPS = {
    # Account metrics
    "balance": {
        "title": "Balance",
        "simple": "Your total account value, not counting open trades.",
        "detail": "This is the amount of money in your account after all closed trades. It doesn't include profits or losses from trades that are still open."
    },
    "equity": {
        "title": "Equity",
        "simple": "Your real-time account value including open trades.",
        "detail": "Equity = Balance + Unrealized P/L. This number changes as your open positions move. It's what your account would be worth if you closed everything now."
    },
    "unrealized_pl": {
        "title": "Unrealized P/L",
        "simple": "Profit or loss from trades you haven't closed yet.",
        "detail": "This is the current profit or loss on your open positions. It's 'unrealized' because it can still change - you only lock in the profit or loss when you close the trade."
    },
    "daily_pnl": {
        "title": "Today's P/L",
        "simple": "How much you've made or lost today.",
        "detail": "The total profit or loss from all trades closed today, plus the unrealized P/L from open positions."
    },
    "margin_used": {
        "title": "Margin Used",
        "simple": "Money set aside to keep your trades open.",
        "detail": "When you open a leveraged trade, your broker requires you to put up a portion of the trade value as collateral. This is the total margin being used by all your open positions."
    },
    "margin_available": {
        "title": "Margin Available",
        "simple": "Money available to open new trades.",
        "detail": "This is how much margin you have left to open new positions. If this drops too low, you may get a margin call."
    },
    "margin_level": {
        "title": "Margin Level",
        "simple": "How healthy is your account? Higher is safer.",
        "detail": "Margin Level = (Equity / Margin Used) x 100%. Above 200% is generally safe. Below 100% means you're at risk of a margin call where the broker may close your trades."
    },

    # Performance metrics
    "win_rate": {
        "title": "Win Rate",
        "simple": "Percentage of trades that made money.",
        "detail": "Number of winning trades divided by total trades. A 60% win rate means 6 out of 10 trades were profitable. Note: You can be profitable with a win rate below 50% if your winners are bigger than your losers."
    },
    "profit_factor": {
        "title": "Profit Factor",
        "simple": "How much you win for every dollar you lose.",
        "detail": "Total profits divided by total losses. A profit factor of 2.0 means you make $2 for every $1 you lose. Above 1.5 is good, above 2.0 is excellent."
    },
    "sharpe_ratio": {
        "title": "Sharpe Ratio",
        "simple": "Risk-adjusted returns. Higher means better returns for the risk taken.",
        "detail": "Measures how much return you get per unit of risk. Above 1.0 is acceptable, above 2.0 is very good, above 3.0 is excellent. Negative means you're losing money."
    },
    "sortino_ratio": {
        "title": "Sortino Ratio",
        "simple": "Like Sharpe, but only counts bad volatility.",
        "detail": "Similar to Sharpe ratio, but only penalizes downside volatility (losses). This is often considered a better measure because upside volatility (gains) shouldn't be penalized."
    },
    "max_drawdown": {
        "title": "Max Drawdown",
        "simple": "The biggest drop from a peak. Shows worst-case loss.",
        "detail": "The largest percentage drop from an equity high to a subsequent low. If your account went from $10,000 to $8,000, that's a 20% drawdown. This shows the worst losing streak you experienced."
    },
    "expectancy": {
        "title": "Expectancy",
        "simple": "Average profit/loss per trade.",
        "detail": "The average amount you expect to win (or lose) on each trade. Positive expectancy means your strategy is profitable over time. Calculated as: (Win Rate x Avg Win) - (Loss Rate x Avg Loss)."
    },
    "total_return": {
        "title": "Total Return",
        "simple": "How much your account grew (or shrank).",
        "detail": "The percentage change from your starting capital to your ending capital. A 10% return means if you started with $10,000, you now have $11,000."
    },

    # Risk metrics
    "daily_drawdown": {
        "title": "Daily Drawdown",
        "simple": "How much you've lost today compared to starting balance.",
        "detail": "Tracks your losses for the day. The system has a maximum daily drawdown limit (typically 3%) to protect your capital. If you hit this limit, trading may be paused."
    },
    "position_limit": {
        "title": "Position Limit",
        "simple": "Max number of trades you can have open at once.",
        "detail": "To manage risk, the system limits how many positions you can have open simultaneously. This prevents over-exposure to the market."
    },
    "risk_tier": {
        "title": "Risk Tier",
        "simple": "How much of your account to risk on this trade.",
        "detail": "Based on confidence level: High confidence (90-100%) = 3% risk, Medium (70-89%) = 2% risk, Low (50-69%) = 1% risk. Below 50% confidence = don't trade."
    },

    # Technical indicators
    "confidence": {
        "title": "Confidence Score",
        "simple": "How sure the AI is about this trade setup.",
        "detail": "A score from 0-100 combining technical analysis, sentiment, and risk factors. Above 70% is high confidence, 50-70% is medium, below 50% means the AI doesn't recommend trading."
    },
    "rsi": {
        "title": "RSI (Relative Strength Index)",
        "simple": "Is the price overbought or oversold?",
        "detail": "RSI ranges from 0-100. Above 70 = overbought (price may fall), below 30 = oversold (price may rise). Between 30-70 is neutral. It measures the speed and change of price movements."
    },
    "macd": {
        "title": "MACD",
        "simple": "Shows momentum and trend direction.",
        "detail": "MACD (Moving Average Convergence Divergence) shows the relationship between two moving averages. When MACD crosses above signal line = bullish. When it crosses below = bearish."
    },
    "atr": {
        "title": "ATR (Average True Range)",
        "simple": "How much the price typically moves.",
        "detail": "ATR measures volatility - the average range between high and low prices. Higher ATR = more volatile market. Used to set stop losses and take profits at appropriate distances."
    },
    "trend": {
        "title": "Trend Direction",
        "simple": "Is the market going up, down, or sideways?",
        "detail": "Based on moving average analysis. BULLISH = price trending up, BEARISH = price trending down, NEUTRAL = no clear trend or ranging market."
    },
    "trend_strength": {
        "title": "Trend Strength",
        "simple": "How strong is the current trend?",
        "detail": "A percentage showing trend conviction. Above 70% = strong trend, 40-70% = moderate trend, below 40% = weak or no trend. Stronger trends are generally more reliable."
    },

    # Trade metrics
    "spread": {
        "title": "Spread",
        "simple": "The cost to enter a trade.",
        "detail": "The difference between buy (ask) and sell (bid) prices. You pay this cost when entering a trade. Lower spread = lower cost. Major pairs like EUR/USD typically have lower spreads."
    },
    "stop_loss": {
        "title": "Stop Loss",
        "simple": "The price where you'll exit to limit losses.",
        "detail": "An automatic order that closes your trade if the price moves against you by a certain amount. This protects you from large losses. Never trade without a stop loss!"
    },
    "take_profit": {
        "title": "Take Profit",
        "simple": "The price where you'll exit to lock in profits.",
        "detail": "An automatic order that closes your trade when you've reached your profit target. Helps you capture gains without having to watch the market constantly."
    },
    "pips": {
        "title": "Pips",
        "simple": "The smallest price move in forex.",
        "detail": "A pip is typically the 4th decimal place for most pairs (0.0001) or 2nd for JPY pairs (0.01). If EUR/USD moves from 1.1000 to 1.1050, that's 50 pips."
    },

    # Adversarial analysis
    "bull_score": {
        "title": "Bull Score",
        "simple": "Strength of arguments for prices going UP.",
        "detail": "The AI analyzes reasons why the price might go up and scores them. Higher score = more bullish factors present."
    },
    "bear_score": {
        "title": "Bear Score",
        "simple": "Strength of arguments for prices going DOWN.",
        "detail": "The AI analyzes reasons why the price might go down and scores them. Higher score = more bearish factors present."
    },
    "verdict": {
        "title": "AI Verdict",
        "simple": "The AI's final recommendation.",
        "detail": "After weighing bull and bear arguments, the AI gives a verdict: STRONGLY BULLISH, BULLISH, NEUTRAL, BEARISH, or STRONGLY BEARISH."
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_tooltip(metric_key: str) -> dict:
    """
    Get tooltip info for a metric.

    Args:
        metric_key: Key from METRIC_TOOLTIPS

    Returns:
        Dict with title, simple, detail or default if not found
    """
    return METRIC_TOOLTIPS.get(metric_key, {
        "title": metric_key.replace("_", " ").title(),
        "simple": "No explanation available.",
        "detail": ""
    })


def tooltip_text(metric_key: str, detailed: bool = False) -> str:
    """
    Get tooltip text for a metric.

    Args:
        metric_key: Key from METRIC_TOOLTIPS
        detailed: If True, include detailed explanation

    Returns:
        Explanation string
    """
    info = get_tooltip(metric_key)
    if detailed and info.get("detail"):
        return f"{info['simple']}\n\n{info['detail']}"
    return info["simple"]


def metric_with_tooltip(
    label: str,
    value: Any,
    metric_key: str,
    delta: Optional[str] = None,
    delta_color: str = "normal",
    help_text: Optional[str] = None
):
    """
    Render a Streamlit metric with a tooltip explanation.

    Args:
        label: Metric label
        value: Metric value
        metric_key: Key from METRIC_TOOLTIPS
        delta: Optional delta value
        delta_color: Delta color ("normal", "inverse", "off")
        help_text: Override tooltip text
    """
    tooltip = help_text or tooltip_text(metric_key)
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=tooltip
    )


def info_expander(metric_key: str, title: str = "What does this mean?"):
    """
    Create an expander with detailed explanation of a metric.

    Args:
        metric_key: Key from METRIC_TOOLTIPS
        title: Expander title

    Returns:
        Expander context manager
    """
    return st.expander(f"{ICONS['question']} {title}")


def render_explanation_box(metric_key: str, value: Any = None, style: str = "info"):
    """
    Render a styled explanation box for a metric.

    Args:
        metric_key: Key from METRIC_TOOLTIPS
        value: Optional current value for context
        style: "info", "success", "warning", or "error"
    """
    info = get_tooltip(metric_key)

    # Build message with value context if provided
    message = info["simple"]
    if value is not None:
        message = f"**{info['title']}:** {value}\n\n{message}"

    # Render appropriate box
    if style == "success":
        st.success(message)
    elif style == "warning":
        st.warning(message)
    elif style == "error":
        st.error(message)
    else:
        st.info(message)


def render_metric_explanation(metric_key: str, value: Any, thresholds: dict = None):
    """
    Render a metric with contextual explanation based on its value.

    Args:
        metric_key: Key from METRIC_TOOLTIPS
        value: Current value
        thresholds: Optional dict with "good", "warning", "bad" thresholds
    """
    info = get_tooltip(metric_key)

    # Default thresholds for known metrics
    default_thresholds = {
        "sharpe_ratio": {"good": 2.0, "warning": 1.0, "bad": 0},
        "sortino_ratio": {"good": 2.0, "warning": 1.0, "bad": 0},
        "win_rate": {"good": 60, "warning": 50, "bad": 40},
        "profit_factor": {"good": 2.0, "warning": 1.5, "bad": 1.0},
        "max_drawdown": {"good": 5, "warning": 10, "bad": 20, "inverse": True},
        "confidence": {"good": 70, "warning": 50, "bad": 30},
        "rsi": {"overbought": 70, "oversold": 30},
        "margin_level": {"good": 500, "warning": 200, "bad": 100},
    }

    th = thresholds or default_thresholds.get(metric_key, {})

    # Determine status based on thresholds
    status = "info"
    context_msg = ""

    if metric_key == "rsi" and value is not None:
        if value >= 70:
            status = "warning"
            context_msg = f"RSI at {value:.1f} - The market is overbought. Prices may fall soon."
        elif value <= 30:
            status = "success"
            context_msg = f"RSI at {value:.1f} - The market is oversold. Prices may rise soon."
        else:
            context_msg = f"RSI at {value:.1f} - The market is in a neutral zone."
    elif "inverse" in th and th.get("inverse"):
        # Lower is better (like drawdown)
        if value is not None:
            if value <= th.get("good", 0):
                status = "success"
                context_msg = f"Excellent! {info['title']} is low at {value:.1f}%."
            elif value <= th.get("warning", 0):
                status = "warning"
                context_msg = f"Acceptable. {info['title']} is moderate at {value:.1f}%."
            else:
                status = "error"
                context_msg = f"Caution! {info['title']} is high at {value:.1f}%."
    elif th:
        # Higher is better
        if value is not None:
            if value >= th.get("good", float('inf')):
                status = "success"
                context_msg = f"Excellent! Your {info['title'].lower()} of {value:.2f} is above the good threshold."
            elif value >= th.get("warning", 0):
                status = "info"
                context_msg = f"Acceptable. Your {info['title'].lower()} of {value:.2f} is in the normal range."
            else:
                status = "warning"
                context_msg = f"Could be better. Your {info['title'].lower()} of {value:.2f} is below ideal."

    # Render
    if context_msg:
        render_explanation_box(metric_key, style=status)
        st.caption(context_msg)


def simple_explanation_section(metrics: dict, title: str = "What do these numbers mean?"):
    """
    Render a collapsible section with simple explanations of multiple metrics.

    Args:
        metrics: Dict of {metric_key: value}
        title: Section title
    """
    with st.expander(f"{ICONS['question']} {title}"):
        for key, value in metrics.items():
            info = get_tooltip(key)

            # Format value
            if isinstance(value, float):
                if "pct" in key or "rate" in key or key == "max_drawdown":
                    formatted = f"{value:.1f}%"
                elif "ratio" in key or "factor" in key:
                    formatted = f"{value:.2f}"
                else:
                    formatted = f"{value:.2f}"
            else:
                formatted = str(value)

            st.markdown(f"**{info['title']}** ({formatted})")
            st.caption(info["simple"])
            st.markdown("---")


def get_icon(icon_key: str) -> str:
    """
    Get a Windows-safe icon.

    Args:
        icon_key: Key from ICONS dict

    Returns:
        Icon string or empty if not found
    """
    return ICONS.get(icon_key, "")
