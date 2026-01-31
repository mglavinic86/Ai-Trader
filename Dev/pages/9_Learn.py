"""
AI Trader - Learn Page

Educational content for forex trading beginners.
"""

import streamlit as st
import sys
from pathlib import Path

DEV_DIR = Path(__file__).parent.parent
if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))

from components.tooltips import ICONS

st.set_page_config(page_title="Learn - AI Trader", page_icon="", layout="wide")


def render_forex_basics():
    """Tab: Forex Basics."""
    st.header("Forex Basics")

    st.markdown("""
    Welcome to the world of Forex trading! This guide will help you understand
    the fundamentals before you start using AI Trader.
    """)

    # What is Forex?
    with st.expander("What is Forex?", expanded=True):
        st.markdown("""
        **Forex** (Foreign Exchange) is the global marketplace for trading national currencies.

        - It's the **largest financial market** in the world with over $6 trillion traded daily
        - Open **24 hours a day**, 5 days a week (Monday-Friday)
        - Unlike stocks, there's no central exchange - trading happens electronically

        **Why do people trade Forex?**
        - To profit from currency price movements
        - To hedge business currency risk
        - For speculation and investment
        """)

    # Currency Pairs
    with st.expander("Currency Pairs", expanded=True):
        st.markdown("""
        Currencies are always traded in **pairs**. When you buy EUR/USD, you're:
        - **Buying** Euros (the base currency)
        - **Selling** US Dollars (the quote currency)

        **Common Pairs:**

        | Pair | Name | Description |
        |------|------|-------------|
        | EUR/USD | Euro/Dollar | Most traded pair |
        | GBP/USD | Pound/Dollar | "Cable" |
        | USD/JPY | Dollar/Yen | Popular for carry trades |
        | AUD/USD | Aussie/Dollar | Commodity-linked |
        | USD/CHF | Dollar/Franc | Safe-haven pair |

        **Reading a Quote:**

        If EUR/USD = 1.0850, it means:
        - 1 Euro costs 1.0850 US Dollars
        - If you think the Euro will **strengthen**, you **BUY** (go long)
        - If you think the Euro will **weaken**, you **SELL** (go short)
        """)

    # Pips
    with st.expander("What is a Pip?", expanded=True):
        st.markdown("""
        A **pip** (Point in Percentage) is the smallest price movement in forex.

        For most pairs, 1 pip = **0.0001** (the 4th decimal place)

        **Examples:**
        - EUR/USD moves from 1.0850 to 1.0851 = **+1 pip**
        - EUR/USD moves from 1.0850 to 1.0900 = **+50 pips**

        **Exception:** For Japanese Yen pairs, 1 pip = **0.01** (2nd decimal place)
        - USD/JPY moves from 150.00 to 150.01 = **+1 pip**

        **Pip Value:**

        For a standard lot (100,000 units) in EUR/USD:
        - 1 pip = approximately **$10**

        For a mini lot (10,000 units):
        - 1 pip = approximately **$1**
        """)

    # Spread
    with st.expander("Understanding the Spread"):
        st.markdown("""
        The **spread** is the difference between the buy (ask) and sell (bid) price.

        **Example:**
        - EUR/USD Bid: 1.0850 (price to sell)
        - EUR/USD Ask: 1.0852 (price to buy)
        - Spread: 2 pips

        **Why does it matter?**
        - The spread is the **cost** of entering a trade
        - Lower spread = lower cost
        - Major pairs (like EUR/USD) have the lowest spreads
        - Exotic pairs have higher spreads

        **When to trade:**
        - Spreads are lowest during high-volume sessions (London/New York overlap)
        - Spreads widen during news events and low-liquidity hours
        """)

    # Lots
    with st.expander("Position Sizes (Lots)"):
        st.markdown("""
        A **lot** is the standard unit size of a trade.

        | Lot Type | Size | Pip Value (EUR/USD) |
        |----------|------|---------------------|
        | Standard | 100,000 units | ~$10 per pip |
        | Mini | 10,000 units | ~$1 per pip |
        | Micro | 1,000 units | ~$0.10 per pip |

        **AI Trader uses units** rather than lots for precision.
        For example, 10,000 units = 1 mini lot.
        """)

    # Leverage
    with st.expander("Leverage and Margin"):
        st.markdown("""
        **Leverage** allows you to control a large position with a small amount of money.

        With 1:100 leverage:
        - $1,000 in your account controls $100,000 in trades
        - This amplifies **both profits AND losses**

        **Margin** is the amount required to open a position:
        - 1:100 leverage = 1% margin requirement
        - $100,000 position requires $1,000 margin

        **Warning:**
        - High leverage is **risky**
        - You can lose more than your initial deposit
        - AI Trader uses conservative position sizing to manage this risk
        """)


def render_technical_analysis():
    """Tab: Technical Analysis."""
    st.header("Technical Analysis")

    st.markdown("""
    Technical analysis uses past price data to predict future movements.
    Here's what AI Trader analyzes:
    """)

    # RSI
    with st.expander("RSI (Relative Strength Index)", expanded=True):
        st.markdown("""
        **What it measures:** The speed and change of price movements.

        **Scale:** 0 to 100

        **How to read it:**

        | RSI Value | Meaning | Signal |
        |-----------|---------|--------|
        | Above 70 | Overbought | Price may fall - possible SELL |
        | Below 30 | Oversold | Price may rise - possible BUY |
        | 30-70 | Neutral | No clear signal |

        **Example:**
        - RSI at 75 = Market has been rising fast, might be due for a pullback
        - RSI at 25 = Market has been falling hard, might bounce soon

        **Caution:** In strong trends, RSI can stay overbought/oversold for extended periods!
        """)

        # Visual representation
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Oversold Zone**")
            st.progress(0.25)
            st.caption("RSI < 30: Potential buy opportunity")
        with col2:
            st.markdown("**Neutral Zone**")
            st.progress(0.50)
            st.caption("RSI 30-70: No signal")
        with col3:
            st.markdown("**Overbought Zone**")
            st.progress(0.85)
            st.caption("RSI > 70: Potential sell opportunity")

    # MACD
    with st.expander("MACD (Moving Average Convergence Divergence)", expanded=True):
        st.markdown("""
        **What it measures:** Trend momentum and direction.

        **Components:**
        - **MACD Line:** Fast moving average minus slow moving average
        - **Signal Line:** Average of the MACD line
        - **Histogram:** Difference between MACD and Signal lines

        **How to read it:**

        | Signal | Meaning |
        |--------|---------|
        | MACD crosses ABOVE signal | Bullish (price may rise) |
        | MACD crosses BELOW signal | Bearish (price may fall) |
        | Histogram growing | Trend strengthening |
        | Histogram shrinking | Trend weakening |

        **Pro tip:** MACD works best for identifying trend changes, not for predicting exact entry/exit points.
        """)

    # Moving Averages
    with st.expander("Moving Averages (EMA)"):
        st.markdown("""
        **What they are:** Average price over a specific number of periods.

        **AI Trader uses:**
        - **EMA 20:** Short-term trend (20 periods)
        - **EMA 50:** Medium-term trend (50 periods)

        **How to read them:**

        | Situation | Interpretation |
        |-----------|----------------|
        | Price ABOVE EMAs | Bullish trend |
        | Price BELOW EMAs | Bearish trend |
        | EMA 20 ABOVE EMA 50 | Uptrend (Golden Cross) |
        | EMA 20 BELOW EMA 50 | Downtrend (Death Cross) |

        **The slope matters:**
        - EMAs pointing UP = Bullish
        - EMAs pointing DOWN = Bearish
        - EMAs flat = Ranging/No trend
        """)

    # ATR
    with st.expander("ATR (Average True Range)"):
        st.markdown("""
        **What it measures:** Market volatility.

        **How it's used:**
        - Setting appropriate **stop loss** distances
        - Setting appropriate **take profit** targets
        - Determining position size

        **Example:**
        - If ATR = 50 pips, the market moves about 50 pips per day
        - A stop loss of 2x ATR (100 pips) gives room for normal fluctuation
        - A take profit of 4x ATR (200 pips) targets a 1:2 risk/reward

        **When ATR is high:**
        - Market is volatile - bigger moves expected
        - Wider stops needed
        - Can be riskier or more profitable

        **When ATR is low:**
        - Market is calm - smaller moves expected
        - Tighter stops possible
        - May indicate incoming breakout
        """)

    # Support and Resistance
    with st.expander("Support and Resistance"):
        st.markdown("""
        **Support:** A price level where buying pressure prevents further decline.
        - Price "bounces" off support levels
        - If broken, becomes resistance

        **Resistance:** A price level where selling pressure prevents further rise.
        - Price "bounces" off resistance levels
        - If broken, becomes support

        **Trading these levels:**

        | Strategy | How it works |
        |----------|--------------|
        | Bounce | Enter when price touches level and reverses |
        | Breakout | Enter when price breaks through level with momentum |

        **AI Trader identifies these levels automatically** based on price action history.
        """)

    # Trend
    with st.expander("Reading the Trend"):
        st.markdown("""
        **"The trend is your friend"** - One of the oldest trading adages.

        **Types of trends:**

        - **BULLISH:** Higher highs, higher lows - price going UP
        - **BEARISH:** Lower highs, lower lows - price going DOWN
        - **NEUTRAL/RANGING:** No clear direction - price moving sideways

        **Trend strength:**

        AI Trader measures trend strength from 0-100%:

        | Strength | Meaning |
        |----------|---------|
        | 70-100% | Strong trend - trade with confidence |
        | 40-70% | Moderate trend - trade with caution |
        | 0-40% | Weak/no trend - consider waiting |

        **Best practice:** Trade in the direction of the trend.
        Fighting the trend is risky for beginners.
        """)


def render_risk_management():
    """Tab: Risk Management with interactive calculator."""
    st.header("Risk Management")

    st.markdown("""
    **Risk management is the most important part of trading!**
    Even the best analysis is worthless if you don't protect your capital.
    """)

    # Key Rules
    with st.expander("The Golden Rules of Risk", expanded=True):
        st.markdown("""
        ### Never Break These Rules:

        1. **Never risk more than 1-3% per trade**
           - With $10,000 account: risk max $100-300 per trade
           - This lets you survive losing streaks

        2. **Always use a stop loss**
           - Know your max loss BEFORE entering a trade
           - Let AI Trader calculate it for you

        3. **Use proper position sizing**
           - Bigger account doesn't mean bigger risk percentage
           - Keep risk consistent regardless of account size

        4. **Don't revenge trade**
           - After a loss, don't double down to "make it back"
           - Stick to your plan

        5. **Know when to stop**
           - Set a daily loss limit (AI Trader uses 3%)
           - If hit, stop trading for the day
        """)

    st.divider()

    # Interactive Risk Calculator
    st.subheader("Risk Calculator")
    st.markdown("Use this calculator to understand how position sizing works:")

    col1, col2 = st.columns(2)

    with col1:
        account_balance = st.number_input(
            "Account Balance ($)",
            min_value=100,
            max_value=1000000,
            value=10000,
            step=1000
        )

        risk_percent = st.slider(
            "Risk Per Trade (%)",
            min_value=0.5,
            max_value=5.0,
            value=2.0,
            step=0.5,
            help="How much of your account you're willing to risk on this trade"
        )

        stop_loss_pips = st.number_input(
            "Stop Loss (pips)",
            min_value=5,
            max_value=200,
            value=30,
            step=5,
            help="Distance from entry to stop loss in pips"
        )

    with col2:
        # Calculations
        risk_amount = account_balance * (risk_percent / 100)
        pip_value = 10  # Standard pip value for 1 standard lot

        # Position size in lots
        position_lots = risk_amount / (stop_loss_pips * pip_value)
        position_units = int(position_lots * 100000)

        st.markdown("### Results")
        st.metric("Risk Amount", f"${risk_amount:,.2f}")
        st.metric("Position Size", f"{position_lots:.2f} lots ({position_units:,} units)")

        # Visual breakdown
        st.markdown("---")
        st.markdown("**What this means:**")
        st.info(f"""
        - If the trade hits your stop loss, you'll lose **${risk_amount:.2f}** ({risk_percent}% of your account)
        - This is {position_lots:.2f} standard lots or {position_units:,} units
        - You can afford {int(100/risk_percent)} losing trades in a row before losing your account
        """)

        # Risk tier explanation
        if risk_percent <= 1:
            st.success("**Conservative risk** - Good for beginners or uncertain setups")
        elif risk_percent <= 2:
            st.info("**Moderate risk** - Standard for confident setups")
        elif risk_percent <= 3:
            st.warning("**Higher risk** - Only for very high confidence trades")
        else:
            st.error("**Dangerous risk** - Not recommended! Consider reducing.")

    # Risk scenarios table
    st.divider()
    st.subheader("Scenario Analysis")
    st.markdown("See how different risk levels affect your account over time:")

    import pandas as pd

    scenarios = []
    for risk in [1, 2, 3]:
        risk_amt = account_balance * (risk / 100)
        # Simulate 10 consecutive losses
        balance_after_losses = account_balance
        for _ in range(10):
            balance_after_losses -= balance_after_losses * (risk / 100)

        scenarios.append({
            "Risk %": f"{risk}%",
            "Risk per Trade": f"${account_balance * (risk/100):,.0f}",
            "After 5 Losses": f"${account_balance * (1 - risk/100)**5:,.0f}",
            "After 10 Losses": f"${balance_after_losses:,.0f}",
            "Trades to Lose 50%": int(round(-50 / (-risk)))
        })

    df = pd.DataFrame(scenarios)
    st.table(df)

    st.caption("This shows why lower risk per trade is crucial - it gives you more chances to recover from losing streaks.")

    # Risk:Reward
    st.divider()

    with st.expander("Risk:Reward Ratio"):
        st.markdown("""
        **Risk:Reward (R:R)** compares potential loss to potential gain.

        AI Trader targets a **1:2 risk:reward ratio**:
        - Risk 30 pips to make 60 pips
        - Even with 40% win rate, you're profitable!

        **Math Example:**

        10 trades with 1:2 R:R and 40% win rate:
        - 4 winners x $60 = $240
        - 6 losers x $30 = $180
        - **Net profit: $60** (even while losing more trades than winning!)

        **Minimum acceptable R:R:** 1:1.5 (risk 30 to make 45)

        **Never trade if R:R is below 1:1!**
        """)


def render_how_to_use():
    """Tab: How to use AI Trader."""
    st.header("How to Use AI Trader")

    st.markdown("""
    This quick-start guide will help you get started with AI Trader.
    """)

    # Step 1
    st.subheader("Step 1: Check the Dashboard")
    st.markdown("""
    The **Dashboard** is your command center:

    - **Balance & Equity:** Your account status
    - **Today's P/L:** How you're doing today
    - **Open Positions:** Active trades
    - **Risk Status:** Daily drawdown and margin health

    **Always check the dashboard first** before making any decisions!
    """)

    st.divider()

    # Step 2
    st.subheader("Step 2: Get AI Analysis")
    st.markdown("""
    Use the **Chat** page for AI-powered analysis:

    **How to ask for analysis:**
    - Type: "Analyze EUR/USD" (or any pair)
    - The AI will examine technical indicators
    - You'll get a confidence score and recommendation

    **Understanding the recommendation:**

    | Confidence | Meaning | Action |
    |------------|---------|--------|
    | 70-100% | High confidence | Trade with normal size |
    | 50-69% | Medium confidence | Trade with smaller size |
    | Below 50% | Low confidence | Wait for better setup |

    **The AI considers:**
    - Trend direction and strength
    - RSI (overbought/oversold)
    - MACD (momentum)
    - Support/Resistance levels
    - Bull vs Bear arguments
    """)

    st.divider()

    # Step 3
    st.subheader("Step 3: Execute a Trade")
    st.markdown("""
    If the AI recommends a trade:

    1. Review the **analysis summary**
    2. Check the **stop loss** and **take profit** levels
    3. Verify the **position size** fits your risk tolerance
    4. Confirm the trade checkbox
    5. Click **Execute Trade**

    **Important:**
    - AI Trader automatically calculates position size based on:
      - Your account balance
      - The confidence level
      - Your risk settings
    - Stop loss and take profit are set automatically
    """)

    st.divider()

    # Step 4
    st.subheader("Step 4: Monitor Positions")
    st.markdown("""
    Use the **Positions** page to:

    - View all open trades
    - See current profit/loss
    - Close trades manually if needed
    - Use "Close All" in emergencies

    **Tips:**
    - Don't obsess over open positions
    - Trust your stop loss and take profit
    - Avoid moving your stop loss further away!
    """)

    st.divider()

    # Step 5
    st.subheader("Step 5: Review Your Performance")
    st.markdown("""
    Use **History** and **Backtest** pages:

    **History:**
    - View all past trades
    - See win/loss ratio
    - Identify patterns in your trading

    **Backtest:**
    - Test how AI Trader would have performed historically
    - Try different settings
    - Build confidence before live trading
    """)

    st.divider()

    # Tips
    st.subheader("Pro Tips")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        **{ICONS['success']} Do:**
        - Start with the demo account
        - Follow the AI's confidence scores
        - Keep a trading journal
        - Review your trades weekly
        - Take breaks after losses
        """)

    with col2:
        st.markdown(f"""
        **{ICONS['error']} Don't:**
        - Trade during high-impact news
        - Override AI recommendations emotionally
        - Trade when tired or distracted
        - Risk more than 3% per trade
        - Chase losses with bigger trades
        """)

    # FAQ
    st.divider()
    st.subheader("Frequently Asked Questions")

    with st.expander("What timeframe should I use?"):
        st.markdown("""
        **For beginners: H1 (1 hour) or H4 (4 hour)**

        - Gives you time to think
        - Less noise than lower timeframes
        - Still provides enough opportunities

        Avoid M1/M5 until you're experienced - they're noisy and stressful!
        """)

    with st.expander("Which currency pairs are best for beginners?"):
        st.markdown("""
        Start with **major pairs**:
        - EUR/USD (most liquid, lowest spread)
        - GBP/USD (good volatility)
        - USD/JPY (stable trends)

        Avoid exotic pairs (high spreads, unpredictable moves).
        """)

    with st.expander("When is the best time to trade?"):
        st.markdown("""
        **Best times:**
        - London session (8:00-16:00 GMT)
        - New York session (13:00-21:00 GMT)
        - London/NY overlap (13:00-16:00 GMT) - most volatile

        **Worst times:**
        - During major news announcements
        - Low-liquidity hours (22:00-06:00 GMT)
        - Holidays
        """)

    with st.expander("What if the AI is wrong?"):
        st.markdown("""
        **The AI will sometimes be wrong** - this is normal!

        That's why:
        - Every trade has a stop loss
        - Position sizing limits your loss
        - We target 50-60% win rate (not 100%)

        The goal is to be **profitable over many trades**, not win every single one.
        """)


def main():
    st.title("Learn Trading")
    st.markdown("Educational resources to help you become a better trader.")

    # Tab navigation
    tab1, tab2, tab3, tab4 = st.tabs([
        "Forex Basics",
        "Technical Analysis",
        "Risk Management",
        "How to Use AI Trader"
    ])

    with tab1:
        render_forex_basics()

    with tab2:
        render_technical_analysis()

    with tab3:
        render_risk_management()

    with tab4:
        render_how_to_use()


if __name__ == "__main__":
    main()
