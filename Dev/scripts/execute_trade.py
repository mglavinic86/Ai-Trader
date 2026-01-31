#!/usr/bin/env python3
"""
Execute a trade with full risk validation.

Usage:
    python scripts/execute_trade.py EUR_USD LONG --sl 1.0800 --tp 1.0900 --confidence 75
    python scripts/execute_trade.py EUR_USD SHORT --sl 1.0900 --tp 1.0750 --confidence 80

Options:
    --sl          Stop loss price (required)
    --tp          Take profit price (required)
    --confidence  Confidence score 0-100 (default: 50)
    --force       Skip confirmation prompt
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import config
from src.trading.mt5_client import MT5Client, MT5Error
from src.trading.orders import OrderManager
from src.trading.position_sizer import calculate_position_size, calculate_risk_reward
from src.trading.risk_manager import RiskManager
from src.utils.database import db
from src.utils.logger import logger
from src.utils.helpers import generate_trade_id


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Execute a trade with risk validation")

    parser.add_argument("instrument", help="Currency pair (e.g., EUR_USD)")
    parser.add_argument("direction", choices=["LONG", "SHORT", "long", "short"],
                        help="Trade direction")
    parser.add_argument("--sl", type=float, required=True, help="Stop loss price")
    parser.add_argument("--tp", type=float, required=True, help="Take profit price")
    parser.add_argument("--confidence", type=int, default=50, help="Confidence score (0-100)")
    parser.add_argument("--force", action="store_true", help="Skip confirmation")

    return parser.parse_args()


def format_checklist(checks: list) -> str:
    """Format risk checks as checklist."""
    lines = []
    for check in checks:
        status = "✓" if check.passed else "✗"
        lines.append(f"[{status}] {check.message}")
    return "\n".join(lines)


def main():
    args = parse_args()

    # Normalize inputs
    instrument = args.instrument.upper()
    direction = args.direction.upper()

    print(f"\n{'='*50}")
    print(f"   TRADE EXECUTION: {instrument} {direction}")
    print(f"{'='*50}")

    # Validate config
    is_valid, error_msg = config.validate()
    if not is_valid:
        print(f"\n❌ Error: {error_msg}")
        sys.exit(1)

    try:
        # Initialize components
        client = MT5Client()
        order_manager = OrderManager(client)
        risk_manager = RiskManager()

        # Get account info
        account = client.get_account()
        equity = account["nav"]
        open_positions = account["open_position_count"]

        print(f"\n📊 Account: {account['currency']} {equity:,.2f}")

        # Get current price
        price_data = client.get_price(instrument)
        current_price = price_data["ask"] if direction == "LONG" else price_data["bid"]
        spread_pips = price_data["spread_pips"]

        print(f"💹 Current Price: {current_price:.5f} (spread: {spread_pips:.1f} pips)")

        # Calculate position size
        position_result = calculate_position_size(
            equity=equity,
            confidence=args.confidence,
            entry_price=current_price,
            stop_loss=args.sl,
            instrument=instrument
        )

        if not position_result.can_trade:
            print(f"\n❌ Cannot trade: {position_result.reason}")
            sys.exit(1)

        # Calculate risk/reward
        rr = calculate_risk_reward(current_price, args.sl, args.tp, instrument)

        # Validate trade
        daily_pnl = db.get_daily_pnl()
        validation = risk_manager.validate_trade(
            equity=equity,
            risk_amount=position_result.risk_amount,
            confidence=args.confidence,
            open_positions=open_positions,
            spread_pips=spread_pips,
            daily_pnl=daily_pnl
        )

        # Display checklist
        print(f"\n📋 Pre-trade Checklist:")
        print("─" * 40)
        print(format_checklist(validation.checks))
        print("─" * 40)

        if not validation.valid:
            print("\n❌ TRADE BLOCKED - Risk checks failed")
            for check in validation.get_failed_checks():
                print(f"   • {check.name}: {check.message}")
            sys.exit(1)

        # Display trade details
        units = position_result.units if direction == "LONG" else -position_result.units

        print(f"\n📝 Trade Details:")
        print("─" * 40)
        print(f"   Instrument:   {instrument.replace('_', '/')}")
        print(f"   Direction:    {direction}")
        print(f"   Entry:        {current_price:.5f}")
        print(f"   Stop Loss:    {args.sl:.5f} ({position_result.pip_distance:.1f} pips)")
        print(f"   Take Profit:  {args.tp:.5f} ({rr['reward_pips']:.1f} pips)")
        print(f"   Size:         {abs(units):,} units")
        print(f"   Risk:         ${position_result.risk_amount:.2f} ({position_result.risk_percent*100:.1f}%)")
        print(f"   Risk/Reward:  {rr['ratio_display']}")
        print(f"   Confidence:   {args.confidence}%")
        print(f"   Risk Tier:    {position_result.risk_tier}")
        print("─" * 40)

        # Confirmation
        if not args.force:
            print("\n⚠️  Execute this trade?")
            response = input("   Type 'yes' to confirm: ").strip().lower()
            if response != "yes":
                print("\n❌ Trade cancelled")
                sys.exit(0)

        # Execute trade
        print("\n🔄 Executing trade...")

        result = order_manager.open_position(
            instrument=instrument,
            units=units,
            stop_loss=args.sl,
            take_profit=args.tp,
            confidence=args.confidence,
            risk_amount=position_result.risk_amount
        )

        if not result.success:
            print(f"\n❌ Trade failed: {result.error}")
            sys.exit(1)

        # Log to database
        trade_data = {
            "trade_id": result.trade_id,
            "instrument": instrument,
            "direction": direction,
            "entry_price": result.price,
            "stop_loss": args.sl,
            "take_profit": args.tp,
            "units": abs(units),
            "risk_amount": position_result.risk_amount,
            "risk_percent": position_result.risk_percent,
            "confidence_score": args.confidence
        }
        db.log_trade(trade_data)

        # Success message
        print(f"\n✅ TRADE EXECUTED SUCCESSFULLY")
        print("─" * 40)
        print(f"   Trade ID:     {result.trade_id}")
        print(f"   Order ID:     {result.order_id}")
        print(f"   Fill Price:   {result.price:.5f}")
        print("─" * 40)

        if config.is_demo():
            print("\n📊 This is a DEMO trade")

    except MT5Error as e:
        print(f"\n❌ MT5 Error: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n❌ Trade cancelled by user")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.exception("Trade execution failed")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
