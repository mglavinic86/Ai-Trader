#!/usr/bin/env python3
"""
Check MT5 connection and credentials.

Usage:
    python scripts/check_connection.py

This script verifies:
1. .env file exists and has credentials
2. MT5 terminal is running
3. Login successful
4. Account is accessible
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import config
from src.trading.mt5_client import MT5Client, MT5Error


def main():
    print("\n[CHECK] AI Trader - MT5 Connection Check")
    print("=" * 40)

    # Step 1: Check .env configuration
    print("\n1. Checking configuration...")

    is_valid, error_msg = config.validate()

    if not is_valid:
        print(f"   [X] {error_msg}")
        print("\n   To fix:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your MT5 credentials:")
        print("      MT5_LOGIN=your_login")
        print("      MT5_PASSWORD=your_password")
        print("      MT5_SERVER=OANDA-TMS-Demo")
        print("   3. Make sure MT5 terminal is running")
        sys.exit(1)

    print("   [OK] Configuration OK")
    print(f"   - Login: {config.MT5_LOGIN}")
    print(f"   - Server: {config.MT5_SERVER}")

    # Step 2: Check MT5 connection
    print("\n2. Testing MT5 connection...")

    try:
        client = MT5Client()

        if not client.is_connected():
            print("   [X] Cannot connect to MT5")
            print("   Check that MT5 terminal is running and credentials are correct")
            sys.exit(1)

        print("   [OK] MT5 connection OK")

    except MT5Error as e:
        print(f"   [X] Connection failed: {e}")
        sys.exit(1)

    # Step 3: Get account info
    print("\n3. Fetching account info...")

    try:
        account = client.get_account()

        print("   [OK] Account accessible")
        print(f"\n   Account Details:")
        print(f"   -------------------------------")
        print(f"   ID:              {account['id']}")
        print(f"   Currency:        {account['currency']}")
        print(f"   Balance:         {account['balance']:,.2f} {account['currency']}")
        print(f"   NAV:             {account['nav']:,.2f} {account['currency']}")
        print(f"   Margin Available: {account['margin_available']:,.2f}")
        print(f"   Unrealized P/L:  {account['unrealized_pl']:,.2f}")
        print(f"   Open Positions:  {account['open_position_count']}")
        print(f"   Open Trades:     {account['open_trade_count']}")

    except MT5Error as e:
        print(f"   [X] Failed to get account info: {e}")
        sys.exit(1)

    # Step 4: Test price fetching
    print("\n4. Testing price fetch...")

    try:
        price = client.get_price("EUR_USD")
        print("   [OK] Price fetch OK")
        print(f"   EUR/USD: {price['bid']:.5f} / {price['ask']:.5f} (spread: {price['spread_pips']:.1f} pips)")

    except MT5Error as e:
        print(f"   [X] Price fetch failed: {e}")
        sys.exit(1)

    # Summary
    print("\n" + "=" * 40)
    print("[OK] ALL CHECKS PASSED")
    print("=" * 40)

    if config.is_demo():
        print("\n[DEMO] You are using a DEMO account")
        print("   This is perfect for testing!")
    else:
        print("\n[!] You are using a LIVE account")
        print("   Be careful with real money!")

    print("\nNext steps:")
    print("  python scripts/fetch_prices.py EUR_USD")
    print("  python scripts/account_info.py")
    print()

    # Cleanup
    client.shutdown()


if __name__ == "__main__":
    main()
