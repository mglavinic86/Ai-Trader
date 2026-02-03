"""
AI Trader Daemon - 24/7 Auto-Trading with Watchdog.

This is the main entry point for running the auto-trading system
in daemon mode with automatic restart on failure.

Features:
- Starts auto-trading service as subprocess
- Monitors heartbeat for health checks
- Auto-restarts on crash (max 5/hour)
- Graceful shutdown on Ctrl+C
- Detailed logging to data/watchdog.log

Usage:
    python run_daemon.py

    # To stop from another terminal:
    python -c "from src.services.watchdog import create_stop_signal; create_stop_signal()"
"""

import sys
import signal
from pathlib import Path

# Add Dev to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.watchdog import Watchdog


def main():
    """Main entry point."""
    print()
    print("=" * 60)
    print("  AI TRADER - 24/7 DAEMON MODE")
    print("=" * 60)
    print()
    print("Starting auto-trading with watchdog monitoring...")
    print("Press Ctrl+C to stop")
    print()
    print("Features:")
    print("  - Heartbeat monitoring every 30 seconds")
    print("  - Auto-restart on crash (max 5/hour)")
    print("  - Graceful shutdown support")
    print()
    print("Logs: Dev/data/watchdog.log")
    print()

    # Create and start watchdog
    watchdog = Watchdog()

    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\nShutdown requested...")
        watchdog.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)

    # Start watchdog (blocking)
    try:
        watchdog.start(start_service=True)
    except Exception as e:
        print(f"Fatal error: {e}")
        watchdog.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
