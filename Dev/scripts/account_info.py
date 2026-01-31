#!/usr/bin/env python3
"""
Display MT5 account information.

Usage:
    python scripts/account_info.py

Shows:
- Account balance and equity
- Margin status
- Open positions
- Risk status
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import config
from src.trading.mt5_client import MT5Client, MT5Error


def format_currency(value: float, currency: str = "USD") -> str:
    """Format value as currency."""
    return f"{value:,.2f} {currency}"


def calculate_risk_status(account: dict) -> dict:
    """Calculate current risk metrics."""
    balance = account["balance"]
    nav = account["nav"]
    unrealized_pl = account["unrealized_pl"]

    # Calculate drawdown from balance
    if balance > 0:
        drawdown_percent = ((balance - nav) / balance) * 100 if nav < balance else 0
    else:
        drawdown_percent = 0

    # Check against limits
    daily_limit = config.MAX_DAILY_DRAWDOWN * 100
    weekly_limit = config.MAX_WEEKLY_DRAWDOWN * 100

    return {
        "balance": balance,
        "equity": nav,
        "unrealized_pl": unrealized_pl,
        "drawdown_percent": drawdown_percent,
        "daily_limit": daily_limit,
        "weekly_limit": weekly_limit,
        "can_trade": drawdown_percent < daily_limit
    }


def main():
    # Validate config
    is_valid, error_msg = config.validate()
    if not is_valid:
        print(f"\n❌ Error: {error_msg}")
        sys.exit(1)

    try:
        client = MT5Client()
        account = client.get_account()
        positions = client.get_positions()

    except MT5Error as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

    currency = account["currency"]
    risk = calculate_risk_status(account)

    # Header
    print("\n" + "=" * 50)
    print("           AI TRADER - ACCOUNT STATUS")
    print("=" * 50)

    # Account Type
    if config.is_demo():
        print("\n📊 DEMO ACCOUNT")
    else:
        print("\n💰 LIVE ACCOUNT")

    # Balance Section
    print("\n┌─────────────────────────────────────────────────┐")
    print("│                   BALANCE                       │")
    print("├─────────────────────────────────────────────────┤")
    print(f"│ Balance:          {format_currency(account['balance'], currency):>26} │")
    print(f"│ Equity (NAV):     {format_currency(account['nav'], currency):>26} │")
    print(f"│ Unrealized P/L:   {format_currency(account['unrealized_pl'], currency):>26} │")
    print("└─────────────────────────────────────────────────┘")

    # Margin Section
    print("\n┌─────────────────────────────────────────────────┐")
    print("│                   MARGIN                        │")
    print("├─────────────────────────────────────────────────┤")
    print(f"│ Margin Available: {format_currency(account['margin_available'], currency):>26} │")
    print(f"│ Margin Used:      {format_currency(account['margin_used'], currency):>26} │")
    print("└─────────────────────────────────────────────────┘")

    # Risk Section
    print("\n┌─────────────────────────────────────────────────┐")
    print("│                 RISK STATUS                     │")
    print("├─────────────────────────────────────────────────┤")

    dd_status = "✅" if risk["drawdown_percent"] < risk["daily_limit"] else "❌"
    print(f"│ Current Drawdown:    {risk['drawdown_percent']:>6.2f}%  {dd_status}               │")
    print(f"│ Daily Limit:         {risk['daily_limit']:>6.2f}%                   │")
    print(f"│ Weekly Limit:        {risk['weekly_limit']:>6.2f}%                   │")

    can_trade_str = "YES ✅" if risk["can_trade"] else "NO ❌ (daily limit reached)"
    print(f"│ Can Trade:           {can_trade_str:<25} │")
    print("└─────────────────────────────────────────────────┘")

    # Positions Section
    print("\n┌─────────────────────────────────────────────────┐")
    print("│                 POSITIONS                       │")
    print("├─────────────────────────────────────────────────┤")

    pos_count = account["open_position_count"]
    max_pos = config.MAX_CONCURRENT_POSITIONS
    pos_status = "✅" if pos_count < max_pos else "⚠️ (at limit)"

    print(f"│ Open Positions:      {pos_count}/{max_pos}  {pos_status:<20} │")
    print(f"│ Open Trades:         {account['open_trade_count']:<25} │")
    print("└─────────────────────────────────────────────────┘")

    # Position Details
    if positions:
        print("\n  Open Position Details:")
        print("  ─────────────────────────────────────────────")
        for pos in positions:
            pair = pos["instrument"].replace("_", "/")
            direction = pos["direction"]
            units = pos["long_units"] if direction == "LONG" else pos["short_units"]
            pl = pos["unrealized_pl"]
            pl_str = f"+{pl:.2f}" if pl >= 0 else f"{pl:.2f}"
            print(f"  {pair:<10} {direction:<6} {units:>8} units  P/L: {pl_str}")
    else:
        print("\n  No open positions")

    # Risk Tiers Info
    print("\n┌─────────────────────────────────────────────────┐")
    print("│              RISK TIER LIMITS                   │")
    print("├─────────────────────────────────────────────────┤")
    print("│ Confidence 90-100%:  Max 3% risk per trade     │")
    print("│ Confidence 70-89%:   Max 2% risk per trade     │")
    print("│ Confidence 50-69%:   Max 1% risk per trade     │")
    print("│ Confidence < 50%:    NO TRADE                  │")
    print("└─────────────────────────────────────────────────┘")

    print()


if __name__ == "__main__":
    main()
