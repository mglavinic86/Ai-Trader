"""
Auto-Trading Runner Script.

Runs the auto-trading service continuously in the background.
Press Ctrl+C to stop.

Usage:
    python run_auto_trading.py
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add Dev to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.auto_trading_service import AutoTradingService
from src.trading.emergency import emergency_controller
from src.utils.logger import logger


async def main():
    """Main entry point."""
    print("=" * 50)
    print("  AI TRADER - AUTO TRADING SERVICE")
    print("=" * 50)
    print()

    service = AutoTradingService()

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\nShutting down...")
        asyncio.create_task(service.stop())

    signal.signal(signal.SIGINT, signal_handler)

    # Start service
    started = await service.start()

    if not started:
        print("Failed to start auto-trading service")
        return

    print("Auto-trading service started!")
    print("Press Ctrl+C to stop")
    print()

    # Keep running
    try:
        while service._running:
            status = service.get_status()

            # Print status every 30 seconds
            print(f"[{status['state']}] Scans: {status['scans_today']} | "
                  f"Signals: {status['signals_found_today']} | "
                  f"Trades: {status['trades_executed_today']} | "
                  f"Errors: {status['errors_today']}")

            await asyncio.sleep(30)

    except asyncio.CancelledError:
        pass

    await service.stop()
    print("Auto-trading service stopped.")


if __name__ == "__main__":
    asyncio.run(main())
