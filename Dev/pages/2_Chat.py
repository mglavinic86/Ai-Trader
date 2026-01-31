"""
AI Trader - Chat Page

Main chat interface for interacting with the AI trading assistant.
"""

import streamlit as st
from datetime import datetime
import sys
from pathlib import Path

# Add Dev to path
DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from src.utils.config import config
from src.utils.database import db
from src.trading.mt5_client import MT5Client, MT5Error
from src.market.indicators import TechnicalAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.analysis.adversarial import AdversarialEngine
from src.analysis.confidence import ConfidenceCalculator
from components.tooltips import ICONS, tooltip_text
from components.skill_buttons import render_compact_skill_buttons, get_available_pairs
from components.mt5_session import get_client, is_connected, reset_connection
from components.status_bar import render_status_bar, get_status_bar_data

# Page config - no emoji for Windows compatibility
st.set_page_config(page_title="Chat - AI Trader", page_icon="", layout="wide")

# ===================
# Session State
# ===================

def init_chat_state():
    """Initialize chat-specific session state."""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": "Hello! I'm your AI trading assistant. I can help you with:\n\n"
                           "- **Analyzing** currency pairs (e.g., 'analyze EUR/USD')\n"
                           "- **Checking prices** (e.g., 'price GBP/USD')\n"
                           "- **Account info** (e.g., 'account')\n"
                           "- **Viewing positions** (e.g., 'positions')\n\n"
                           "How can I help you today?"
            }
        ]
    if "last_analysis" not in st.session_state:
        st.session_state.last_analysis = None


# ===================
# Command Processing
# ===================

def process_command(user_input: str) -> str:
    """
    Process user command and return response.

    Args:
        user_input: User's message

    Returns:
        Response text
    """
    client = get_client()
    cmd = user_input.lower().strip()

    # Skill command pattern: "X analiza za Y" (e.g., "SMC analiza za BTC/USD")
    import re
    skill_pattern = r"^(smc|fvg|killzone|scalping|swing|news)\s+analiza\s+za\s+(\S+)"
    skill_match = re.match(skill_pattern, cmd, re.IGNORECASE)
    if skill_match:
        skill_name = skill_match.group(1).upper()
        pair = skill_match.group(2).upper().replace("/", "_")
        # Pass skill context to analyze
        return analyze_pair(pair, client, skill=skill_name)

    # Parse command
    parts = cmd.split()
    command = parts[0] if parts else ""
    args = parts[1:] if len(parts) > 1 else []

    # Help
    if command in ["help", "h", "?"]:
        return """**Available Commands:**

**Analysis:**
- `analyze <PAIR>` - Full AI analysis (e.g., analyze EUR/USD)
- `price <PAIR>` - Current price

**Account:**
- `account` - Account status
- `positions` - Open positions

**Trading:**
- `trade` - Start trade workflow (after analysis)

**Examples:**
- analyze EUR/USD
- price GBP/USD
- account"""

    # Check connection for most commands
    if command not in ["help", "h", "?"]:
        if not client or not st.session_state.connected:
            return "Not connected to MT5. Please check the connection in the sidebar."

    # Analyze command
    if command in ["analyze", "a"]:
        if not args:
            return "Please specify a currency pair. Example: `analyze EUR/USD`"
        return analyze_pair(args[0], client)

    # Price command
    if command in ["price", "p"]:
        if not args:
            # Default pairs
            return get_multiple_prices(config.DEFAULT_PAIRS, client)
        return get_price(args[0], client)

    # Account command
    if command in ["account", "acc"]:
        return get_account_info(client)

    # Positions command
    if command in ["positions", "pos"]:
        return get_positions(client)

    # Trade command
    if command in ["trade", "t"]:
        return start_trade_workflow()

    # Unknown command - try to be helpful
    if "/" in cmd or "_" in cmd:
        # Looks like a pair
        pair = cmd.upper().replace("/", "_")
        return f"Did you mean `analyze {pair}` or `price {pair}`?"

    return f"I don't understand '{user_input}'. Type `help` for available commands."


def analyze_pair(pair: str, client: MT5Client, skill: str = None) -> str:
    """Run full analysis on a currency pair with optional skill focus."""
    instrument = pair.upper().replace("/", "_")

    # Skill descriptions for context
    skill_context = {
        "SMC": "Smart Money Concepts - institutional order flow, FVG, OB, liquidity",
        "FVG": "Fair Value Gap - imbalance zones, entry opportunities",
        "KILLZONE": "Session Trading - London/NY killzone strategies",
        "SCALPING": "Scalping - quick M5/M15 trades, tight stops",
        "SWING": "Swing Trading - multi-day positions, D1 bias",
        "NEWS": "News Trading - event-driven strategies"
    }

    try:
        # Get price
        price = client.get_price(instrument)

        # Get candles
        candles = client.get_candles(instrument, "H4", 100)
        if len(candles) < 20:
            return f"Not enough data for {instrument}. Need at least 20 candles."

        # Technical analysis
        technical_analyzer = TechnicalAnalyzer()
        technical = technical_analyzer.analyze(candles, instrument)

        # Sentiment analysis
        sentiment_analyzer = SentimentAnalyzer()
        sentiment = sentiment_analyzer.analyze(candles, technical)

        # Adversarial analysis
        adversarial_engine = AdversarialEngine()
        adversarial = adversarial_engine.analyze(technical, sentiment, instrument, "LONG")

        # RAG check
        similar_errors = db.find_similar_errors(instrument, limit=3)
        rag_warnings = len(similar_errors)

        # Confidence calculation
        confidence_calc = ConfidenceCalculator()
        confidence = confidence_calc.calculate(technical, sentiment, adversarial, rag_warnings)

        # Store analysis
        st.session_state.last_analysis = {
            "instrument": instrument,
            "price": price,
            "technical": technical,
            "sentiment": sentiment,
            "adversarial": adversarial,
            "confidence": confidence,
            "timestamp": datetime.now()
        }

        # Build response - Windows safe icons
        trend_icon = "[^]" if technical.trend == "BULLISH" else "[v]" if technical.trend == "BEARISH" else "[-]"
        verdict_icon = "[OK]" if confidence.can_trade else "[NO]"

        # Add skill header if using skill-based analysis
        skill_header = ""
        if skill and skill in skill_context:
            skill_header = f"""**Strategy: {skill}**
*{skill_context[skill]}*

---

"""

        response = f"""{skill_header}**Analysis: {instrument.replace('_', '/')}**

**Price:** {price['bid']:.5f} / {price['ask']:.5f} (spread: {price['spread_pips']:.1f} pips)

---

**Technical Analysis** {trend_icon}
- Trend: **{technical.trend}** (strength: {technical.trend_strength:.0f}%)
- RSI(14): {technical.rsi:.1f} - {technical.rsi_signal}
- MACD: {technical.macd_trend}
- ATR: {technical.atr_pips:.1f} pips
- Score: **{technical.technical_score}/100**

---

**Adversarial Analysis**

| Bull Case ({adversarial.bull_score:.0f}) | Bear Case ({adversarial.bear_score:.0f}) |
|---|---|
"""
        # Add bull/bear points
        bull_points = [p.argument for p in adversarial.bull_case[:3]]
        bear_points = [p.argument for p in adversarial.bear_case[:3]]

        max_points = max(len(bull_points), len(bear_points))
        for i in range(max_points):
            bull = bull_points[i] if i < len(bull_points) else ""
            bear = bear_points[i] if i < len(bear_points) else ""
            response += f"| {bull} | {bear} |\n"

        response += f"""
Verdict: **{adversarial.verdict}** (adjustment: {adversarial.confidence_adjustment:+d})

---

**Confidence Score** {verdict_icon}
- Technical: {confidence.technical_score}/100
- Sentiment: {confidence.sentiment_score}/100
- Adversarial: {confidence.adversarial_adjustment:+d}
- RAG Penalty: {confidence.rag_penalty:+d}

## **FINAL: {confidence.confidence_score}/100**

Risk Tier: {confidence.risk_tier}
"""

        if confidence.can_trade:
            response += "\n**TRADE OPPORTUNITY** - Type `trade` to proceed"
        else:
            response += f"\n**Not recommended** (confidence below {config.MIN_CONFIDENCE_TO_TRADE}%)"

        if similar_errors:
            response += f"\n\n*Found {rag_warnings} similar past error(s) for this pair*"

        # Add simple explanation
        response += f"""

---
**{ICONS['question']} Quick Summary:**
"""
        if confidence.confidence_score >= 70:
            response += f"The AI is **confident** about this setup. Technical indicators and sentiment align well."
        elif confidence.confidence_score >= 50:
            response += f"The AI sees a **moderate** opportunity. Some signals are mixed - consider smaller position size."
        else:
            response += f"The AI **does not recommend** trading now. Wait for a clearer setup with stronger signals."

        return response

    except MT5Error as e:
        return f"Analysis failed: {e}"
    except Exception as e:
        return f"Error during analysis: {e}"


def get_price(pair: str, client: MT5Client) -> str:
    """Get current price for a pair."""
    instrument = pair.upper().replace("/", "_")

    try:
        price = client.get_price(instrument)
        pair_display = price["instrument"].replace("_", "/")
        return f"""**{pair_display}**

Bid: **{price['bid']:.5f}**
Ask: **{price['ask']:.5f}**
Spread: {price['spread_pips']:.1f} pips
Tradeable: {'Yes' if price['tradeable'] else 'No'}"""

    except MT5Error as e:
        return f"Could not get price for {pair}: {e}"


def get_multiple_prices(pairs: list, client: MT5Client) -> str:
    """Get prices for multiple pairs."""
    try:
        prices = client.get_prices(pairs)
        if not prices:
            return "Could not fetch prices."

        response = "**Current Prices:**\n\n"
        response += "| Pair | Bid | Ask | Spread |\n|---|---|---|---|\n"

        for p in prices:
            pair = p["instrument"].replace("_", "/")
            response += f"| {pair} | {p['bid']:.5f} | {p['ask']:.5f} | {p['spread_pips']:.1f} |\n"

        return response

    except Exception as e:
        return f"Error fetching prices: {e}"


def get_account_info(client: MT5Client) -> str:
    """Get account information."""
    try:
        account = client.get_account()
        daily_pnl = db.get_daily_pnl()
        mode = "DEMO" if config.is_demo() else "LIVE"

        return f"""**Account ({mode})**

| | |
|---|---|
| Balance | {account['currency']} {account['balance']:,.2f} |
| Equity | {account['currency']} {account['nav']:,.2f} |
| Unrealized P/L | {account['currency']} {account['unrealized_pl']:+,.2f} |
| Margin Used | {account['margin_used']:,.2f} |
| Margin Available | {account['margin_available']:,.2f} |
| Open Positions | {account['open_position_count']}/{config.MAX_CONCURRENT_POSITIONS} |
| Today's P/L | {account['currency']} {daily_pnl:+,.2f} |"""

    except MT5Error as e:
        return f"Could not get account info: {e}"


def get_positions(client: MT5Client) -> str:
    """Get open positions."""
    try:
        positions = client.get_positions()

        if not positions:
            return "**No open positions**"

        response = "**Open Positions:**\n\n"
        response += "| Pair | Direction | Volume | P/L | Entry | Current |\n|---|---|---|---|---|---|\n"

        for pos in positions:
            pair = pos["instrument"].replace("_", "/")
            pl_display = f"{pos['unrealized_pl']:+.2f}"
            if pos['unrealized_pl'] >= 0:
                pl_display = f"**{pl_display}**"

            response += f"| {pair} | {pos['direction']} | {pos['volume']} | {pl_display} | {pos['price_open']:.5f} | {pos['price_current']:.5f} |\n"

        return response

    except MT5Error as e:
        return f"Could not get positions: {e}"


def start_trade_workflow() -> str:
    """Start the trade workflow."""
    if not st.session_state.last_analysis:
        return "No recent analysis. Please run `analyze <PAIR>` first."

    analysis = st.session_state.last_analysis
    if not analysis["confidence"].can_trade:
        return f"""**Warning:** Confidence is too low ({analysis['confidence'].confidence_score}%)

The analysis for {analysis['instrument']} does not meet the minimum confidence threshold.
Run another analysis or wait for better market conditions."""

    return f"""**Trade Setup: {analysis['instrument']}**

Current Price: {analysis['price']['ask']:.5f}
Confidence: {analysis['confidence'].confidence_score}%
Risk Tier: {analysis['confidence'].risk_tier}

To execute a trade, go to the **Positions** page and use the trade form.

*Note: Full trade execution workflow coming in next update.*"""


# ===================
# Page Layout
# ===================

def main():
    """Main chat page."""
    init_chat_state()

    # Check for pending command from Dashboard
    if "pending_command" in st.session_state and st.session_state.pending_command:
        cmd = st.session_state.pending_command
        st.session_state.pending_command = None
        st.session_state.chat_messages.append({"role": "user", "content": cmd})
        response = process_command(cmd)
        st.session_state.chat_messages.append({"role": "assistant", "content": response})

    st.title("AI Trading Assistant")

    # Sidebar
    with st.sidebar:
        st.title("AI Trader")

        # Connection status
        client = get_client()
        if is_connected():
            st.success("Connected to MT5")
            try:
                account = client.get_account()
                st.metric("Balance", f"{account['currency']} {account['balance']:,.0f}")
                st.metric("Positions", f"{account['open_position_count']}/3")
            except MT5Error as e:
                st.warning(f"Account error: {e}")
            except Exception as e:
                st.warning(f"Error: {e}")
        else:
            st.error("Not connected")
            if st.button("Reconnect"):
                reset_connection()
                st.rerun()

        st.divider()

        # Pair selector for analysis
        st.subheader("Quick Analysis")
        analysis_pair = st.selectbox(
            "Select pair",
            get_available_pairs(),
            format_func=lambda x: x.replace("_", "/"),
            key="chat_analysis_pair"
        )

        # Skill buttons (SMC, FVG, Killzone, Scalping, Swing, News)
        render_compact_skill_buttons(
            pair=analysis_pair,
            key_prefix="chat_",
            process_command_func=process_command
        )

        st.divider()

        # Standard pair buttons
        st.caption("Standard Analysis")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("EUR/USD", use_container_width=True, key="std_eur"):
                st.session_state.chat_messages.append({"role": "user", "content": "analyze EUR/USD"})
                response = process_command("analyze EUR/USD")
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
                st.rerun()

            if st.button("BTC/USD", use_container_width=True, key="std_btc"):
                st.session_state.chat_messages.append({"role": "user", "content": "analyze BTC/USD"})
                response = process_command("analyze BTC/USD")
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
                st.rerun()

        with col2:
            if st.button("GBP/USD", use_container_width=True, key="std_gbp"):
                st.session_state.chat_messages.append({"role": "user", "content": "analyze GBP/USD"})
                response = process_command("analyze GBP/USD")
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
                st.rerun()

            if st.button("Account", use_container_width=True, key="std_acc"):
                st.session_state.chat_messages.append({"role": "user", "content": "account"})
                response = process_command("account")
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
                st.rerun()

        if st.button("Clear Chat", use_container_width=True):
            st.session_state.chat_messages = [st.session_state.chat_messages[0]]
            st.rerun()

    # Chat container
    chat_container = st.container()

    # Display chat history
    with chat_container:
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Type a command (e.g., 'analyze EUR/USD')..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        # Process and get response
        response = process_command(prompt)

        # Add assistant response
        st.session_state.chat_messages.append({"role": "assistant", "content": response})

        # Rerun to show new messages
        st.rerun()

    # Status bar at bottom
    if is_connected():
        try:
            status_data = get_status_bar_data(client, config)
            render_status_bar(**status_data)
        except Exception:
            render_status_bar(connected=False)
    else:
        render_status_bar(connected=False)


if __name__ == "__main__":
    main()
