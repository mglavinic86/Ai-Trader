#!/usr/bin/env python3
"""
AI Trader - Interactive Forex Trading Assistant

Main entry point for the trading interface.

Usage:
    python trader.py

Commands:
    help              Show available commands
    analyze EUR/USD   Full AI analysis
    price EUR/USD     Current price
    account           Account status
    positions         Open positions
    trade             Start trade workflow
    emergency         Close all positions
    settings          View settings
    skills            List AI skills
    exit              Exit

For more information, see:
    - settings/system_prompt.md - AI behavior
    - settings/skills/          - Additional skills
    - settings/knowledge/       - Domain knowledge
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.interface import run_interface


def main():
    """Main entry point."""
    print("Starting AI Trader...")
    run_interface()


if __name__ == "__main__":
    main()
