#!/usr/bin/env python3
"""
Fetch current prices from MT5.

Usage:
    python scripts/fetch_prices.py EUR_USD
    python scripts/fetch_prices.py EUR_USD GBP_USD USD_JPY
    python scripts/fetch_prices.py --all

Examples:
    $ python scripts/fetch_prices.py EUR_USD

    EUR/USD Price
    ─────────────────────────────
    Bid:      1.08430
    Ask:      1.08445
    Spread:   1.5 pips
    Time:     2026-01-30 15:30:00
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading.mt5_client import MT5Client, MT5Error
from src.utils.config import config


def format_price(price_data: dict) -> str:
    """Format price data for display."""
    instrument = price_data["instrument"].replace("_", "/")

    # Determine decimal places based on pair
    decimals = 3 if "JPY" in price_data["instrument"] else 5

    # Parse time
    time_str = price_data.get("time", "")
    if time_str:
        try:
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            time_display = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except ValueError:
            time_display = time_str
    else:
        time_display = "N/A"

    # Build output
    output = f"""
{instrument} Price
{'─' * 30}
Bid:      {price_data['bid']:.{decimals}f}
Ask:      {price_data['ask']:.{decimals}f}
Spread:   {price_data['spread_pips']:.1f} pips
Time:     {time_display}
"""

    # Add warning if spread is high
    if price_data["spread_pips"] > config.MAX_SPREAD_PIPS:
        output += f"\n⚠️  WARNING: Spread > {config.MAX_SPREAD_PIPS} pips (don't trade!)\n"

    if not price_data.get("tradeable", True):
        output += "\n⚠️  WARNING: Market is closed or not tradeable\n"

    return output


def format_prices_table(prices: list[dict]) -> str:
    """Format multiple prices as table."""
    output = """
┌─────────────┬───────────┬───────────┬────────┐
│ Pair        │ Bid       │ Ask       │ Spread │
├─────────────┼───────────┼───────────┼────────┤
"""

    for p in prices:
        pair = p["instrument"].replace("_", "/")
        decimals = 3 if "JPY" in p["instrument"] else 5
        bid = f"{p['bid']:.{decimals}f}"
        ask = f"{p['ask']:.{decimals}f}"
        spread = f"{p['spread_pips']:.1f}"

        output += f"│ {pair:<11} │ {bid:>9} │ {ask:>9} │ {spread:>5}p │\n"

    output += "└─────────────┴───────────┴───────────┴────────┘\n"

    return output


def main():
    """Main entry point."""
    # Check for arguments
    if len(sys.argv) < 2:
        print("Usage: python fetch_prices.py <INSTRUMENT> [INSTRUMENT2 ...]")
        print("       python fetch_prices.py --all")
        print("\nExamples:")
        print("  python fetch_prices.py EUR_USD")
        print("  python fetch_prices.py EUR_USD GBP_USD")
        print("  python fetch_prices.py --all")
        sys.exit(1)

    # Validate config
    is_valid, error_msg = config.validate()
    if not is_valid:
        print(f"\n❌ Error: {error_msg}")
        print("\nTo fix:")
        print("1. Copy .env.example to .env")
        print("2. Add your MT5 credentials")
        print("3. Make sure MT5 terminal is running")
        sys.exit(1)

    # Initialize client
    try:
        client = MT5Client()
    except Exception as e:
        print(f"\n❌ Error initializing MT5 client: {e}")
        sys.exit(1)

    # Get instruments
    if sys.argv[1] == "--all":
        instruments = config.DEFAULT_PAIRS
    else:
        instruments = [arg.upper() for arg in sys.argv[1:]]

    # Fetch prices
    try:
        if len(instruments) == 1:
            # Single instrument - detailed view
            price = client.get_price(instruments[0])
            print(format_price(price))
        else:
            # Multiple instruments - table view
            prices = client.get_prices(instruments)
            print(format_prices_table(prices))

    except MT5Error as e:
        print(f"\n❌ MT5 Error: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

    # Show account status if demo
    if config.is_demo():
        print("📊 Using DEMO account")


if __name__ == "__main__":
    main()
