#!/usr/bin/env python3
"""
EMERGENCY: Close ALL positions immediately.

Usage:
    python scripts/emergency_close.py

This script:
1. Closes ALL open positions
2. Does NOT ask for confirmation
3. Logs all closures

Use this when something goes wrong and you need to exit all trades immediately.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import config
from src.trading.mt5_client import MT5Client, MT5Error
from src.trading.orders import OrderManager
from src.utils.logger import logger


def main():
    print("\n" + "=" * 50)
    print("⚠️  EMERGENCY CLOSE - CLOSING ALL POSITIONS")
    print("=" * 50)

    # Validate config
    is_valid, error_msg = config.validate()
    if not is_valid:
        print(f"\n❌ Error: {error_msg}")
        sys.exit(1)

    try:
        client = MT5Client()
        order_manager = OrderManager(client)

        # Get current positions
        positions = client.get_positions()

        if not positions:
            print("\n✅ No open positions to close")
            sys.exit(0)

        print(f"\n📊 Found {len(positions)} open position(s):")
        for pos in positions:
            pair = pos["instrument"].replace("_", "/")
            direction = pos["direction"]
            units = pos["long_units"] if direction == "LONG" else pos["short_units"]
            pl = pos["unrealized_pl"]
            print(f"   {pair} {direction} {units} units (P/L: ${pl:.2f})")

        print("\n🔄 Closing all positions...")

        # Close all positions
        results = order_manager.close_all_positions()

        # Report results
        print("\n📋 Results:")
        print("─" * 40)

        success_count = 0
        for result in results:
            if result.success:
                success_count += 1
                print(f"   ✅ {result.instrument}: Closed @ {result.price}")
            else:
                print(f"   ❌ {result.instrument or 'Unknown'}: {result.error}")

        print("─" * 40)
        print(f"\n✅ Closed {success_count}/{len(results)} positions")

        if success_count < len(results):
            print("\n⚠️  Some positions failed to close!")
            print("   Check OANDA web platform manually:")
            print("   https://fxpractice.oanda.com (demo)")
            print("   https://fxtrade.oanda.com (live)")

    except MT5Error as e:
        print(f"\n❌ MT5 Error: {e}")
        print("\n⚠️  Manual intervention required!")
        print("   Close positions manually in MT5 terminal")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.exception("Emergency close failed")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
