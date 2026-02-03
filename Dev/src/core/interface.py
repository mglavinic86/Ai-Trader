"""
Interactive Interface for AI Trader.

This is the main entry point for user interaction.

Usage:
    python trader.py
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' library not installed. Using basic output.")

from src.utils.config import config
from src.utils.logger import logger
from src.utils.database import db
from src.trading.mt5_client import MT5Client, MT5Error
from src.trading.orders import OrderManager
from src.trading.position_sizer import calculate_position_size, calculate_risk_reward
from src.trading.risk_manager import RiskManager
from src.market.indicators import TechnicalAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.analysis.adversarial import AdversarialEngine
from src.analysis.confidence import ConfidenceCalculator
from src.analysis.llm_engine import LLMEngine
from src.core.settings_manager import settings_manager


class TradingInterface:
    """
    Interactive trading interface.

    Provides CLI commands for:
    - Market analysis
    - Trade execution
    - Account management
    - Settings management
    """

    def __init__(self):
        """Initialize interface."""
        self.console = Console() if RICH_AVAILABLE else None
        self.running = True

        # Components
        self.client = None
        self.order_manager = None
        self.risk_manager = RiskManager()
        self.technical_analyzer = TechnicalAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.adversarial_engine = AdversarialEngine()
        self.confidence_calculator = ConfidenceCalculator()
        self.llm_engine = LLMEngine()

        # State
        self.connected = False
        self.last_analysis = None
        self.last_llm_result = None
        self.last_llm_decision_id = None

    def print(self, message: str, style: str = None):
        """Print message to console."""
        if self.console:
            self.console.print(message, style=style)
        else:
            print(message)

    def print_panel(self, content: str, title: str = None):
        """Print content in a panel."""
        if self.console:
            self.console.print(Panel(content, title=title))
        else:
            print(f"\n=== {title} ===")
            print(content)
            print("=" * 40)

    def print_error(self, message: str):
        """Print error message."""
        self.print(f"[X] {message}", style="red")

    def print_success(self, message: str):
        """Print success message."""
        self.print(f"[OK] {message}", style="green")

    def print_warning(self, message: str):
        """Print warning message."""
        self.print(f"[!] {message}", style="yellow")

    def start(self):
        """Start the interactive interface."""
        self._show_welcome()
        self._connect()

        while self.running:
            try:
                self._main_loop()
            except KeyboardInterrupt:
                self.print("\n")
                if Confirm.ask("Exit AI Trader?", default=False) if RICH_AVAILABLE else input("Exit? (y/n): ").lower() == 'y':
                    self.running = False
            except Exception as e:
                self.print_error(f"Error: {e}")
                logger.exception("Interface error")

        self._show_goodbye()

    def _show_welcome(self):
        """Show welcome message."""
        welcome = """
   _    ___   _____               _
  / \\  |_ _| |_   _| __ __ _  __| | ___ _ __
 / _ \\  | |    | || '__/ _` |/ _` |/ _ \\ '__|
/ ___ \\ | |    | || | | (_| | (_| |  __/ |
/_/   \\_\\___|   |_||_|  \\__,_|\\__,_|\\___|_|

Forex Trading Assistant v1.0
        """
        self.print(welcome, style="cyan bold")
        self.print("Type 'help' for commands\n")

    def _show_goodbye(self):
        """Show goodbye message."""
        self.print("\nGoodbye! Trade safe. [UP]", style="cyan")

    def _connect(self):
        """Connect to MT5."""
        is_valid, error = config.validate()

        if not is_valid:
            self.print_warning(f"Not connected: {error}")
            self.print("Add MT5 credentials to .env and make sure MT5 terminal is running\n")
            self.connected = False
            return

        try:
            self.client = MT5Client()
            self.order_manager = OrderManager(self.client)

            if self.client.is_connected():
                account = self.client.get_account()
                self.connected = True
                mode = "DEMO" if config.is_demo() else "LIVE"
                self.print_success(f"Connected to MT5 ({mode})")
                self.print(f"   Balance: {account['currency']} {account['balance']:,.2f}\n")
            else:
                self.print_error("Could not connect to MT5")
                self.connected = False

        except MT5Error as e:
            self.print_error(f"Connection error: {e}")
            self.connected = False

    def _main_loop(self):
        """Main command loop."""
        prompt = "AI Trader> " if self.connected else "AI Trader (offline)> "

        if RICH_AVAILABLE:
            cmd = Prompt.ask(prompt).strip()
        else:
            cmd = input(prompt).strip()

        if not cmd:
            return

        parts = cmd.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # Command handlers
        handlers = {
            "help": self._cmd_help,
            "h": self._cmd_help,
            "?": self._cmd_help,
            "analyze": self._cmd_analyze,
            "a": self._cmd_analyze,
            "price": self._cmd_price,
            "p": self._cmd_price,
            "account": self._cmd_account,
            "acc": self._cmd_account,
            "positions": self._cmd_positions,
            "pos": self._cmd_positions,
            "trade": self._cmd_trade,
            "t": self._cmd_trade,
            "approve": self._cmd_approve_llm,
            "approve_llm": self._cmd_approve_llm,
            "llm_trade": self._cmd_approve_llm,
            "llm": self._cmd_approve_llm,
            "close": self._cmd_close,
            "emergency": self._cmd_emergency,
            "report": self._cmd_report,
            "settings": self._cmd_settings,
            "skills": self._cmd_skills,
            "prompt": self._cmd_prompt,
            "clear": self._cmd_clear,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "q": self._cmd_exit,
        }

        handler = handlers.get(command)
        if handler:
            handler(args)
        else:
            self.print_error(f"Unknown command: {command}")
            self.print("Type 'help' for available commands")

    # === COMMAND HANDLERS ===

    def _cmd_help(self, args):
        """Show help."""
        help_text = """
[LIST] AVAILABLE COMMANDS
----------------------

ANALYSIS:
  analyze <PAIR>    Full AI analysis (e.g., analyze EUR/USD)
  price <PAIR>      Current price
  a, p              Short aliases

TRADING:
  trade             Start trade workflow
  approve llm       Approve LLM recommendation for trade
  close <PAIR>      Close position
  emergency         Close ALL positions

ACCOUNT:
  account           Account status
  positions         Open positions
  report            Daily report

SETTINGS:
  settings          View settings
  skills            List skills
  prompt            View system prompt

OTHER:
  clear             Clear screen
  help              This help
  exit              Exit

EXAMPLES:
  analyze EUR/USD
  price GBP/USD
  trade
"""
        self.print_panel(help_text, title="Help")

    def _cmd_analyze(self, args):
        """Analyze a currency pair."""
        if not self.connected:
            self.print_error("Not connected to MT5")
            return

        if not args:
            self.print_error("Usage: analyze <PAIR> (e.g., analyze EUR/USD)")
            return

        instrument = args[0].upper().replace("/", "_")
        self.print(f"\n[SEARCH] Analyzing {instrument}...\n")

        try:
            # Get price
            price = self.client.get_price(instrument)
            self.print(f"[PRICE] Price: {price['bid']:.5f} / {price['ask']:.5f} (spread: {price['spread_pips']:.1f} pips)")

            # Get candles for analysis
            candles = self.client.get_candles(instrument, "H4", 100)

            if len(candles) < 20:
                self.print_error("Not enough data for analysis")
                return

            # Technical analysis
            technical = self.technical_analyzer.analyze(candles, instrument)
            self.print(technical.format_summary())

            # Sentiment analysis
            sentiment = self.sentiment_analyzer.analyze(candles, technical)
            self.print(sentiment.format_summary())

            # Adversarial analysis
            adversarial = self.adversarial_engine.analyze(
                technical, sentiment, instrument, "LONG"
            )
            self.print(adversarial.format_summary())

            # Check RAG for similar errors
            similar_errors = db.find_similar_errors(instrument, limit=3)
            rag_warnings = len(similar_errors)

            if similar_errors:
                self.print_warning(f"Found {rag_warnings} similar past error(s):")
                for err in similar_errors:
                    self.print(f"   • {err['error_category']}: {err['root_cause'][:50]}...")

            # Calculate confidence
            confidence = self.confidence_calculator.calculate(
                technical, sentiment, adversarial, rag_warnings
            )
            self.print(confidence.format_summary())

            # Store for trade command
            self.last_analysis = {
                "instrument": instrument,
                "price": price,
                "technical": technical,
                "sentiment": sentiment,
                "adversarial": adversarial,
                "confidence": confidence,
                "timestamp": datetime.now()
            }

            # LLM advisory
            self.last_llm_result = None
            self.last_llm_decision_id = None
            llm_result = self.llm_engine.analyze(
                instrument=instrument,
                price=price,
                technical=technical,
                sentiment=sentiment,
                adversarial=adversarial,
                rag_errors=similar_errors
            )
            if llm_result:
                self.last_llm_result = llm_result
                try:
                    decision_id = db.log_llm_decision({
                        "instrument": instrument,
                        "recommendation": llm_result.recommendation,
                        "direction": llm_result.direction,
                        "confidence_adjustment": llm_result.confidence_adjustment,
                        "summary": llm_result.summary,
                        "risk_notes": llm_result.risk_notes,
                        "strategy_notes": llm_result.strategy_notes,
                        "approved": 0,
                        "executed": 0
                    })
                    self.last_llm_decision_id = decision_id
                except Exception:
                    self.last_llm_decision_id = None

                self.print_panel(
                    f"Bias: {llm_result.bias}\n"
                    f"Recommendation: {llm_result.recommendation}\n"
                    f"Direction: {llm_result.direction}\n\n"
                    f"Summary: {llm_result.summary}",
                    title="LLM Advisory"
                )
                if llm_result.recommendation.upper() == "TRADE":
                    self.print("Type 'approve llm' to prepare this trade.\n")

            # Recommendation
            if confidence.can_trade:
                self.print_success(f"Trade opportunity: {instrument}")
                self.print(f"   Use 'trade' command to proceed")
            else:
                self.print_warning(f"Not recommended to trade (confidence: {confidence.confidence_score}%)")

        except MT5Error as e:
            self.print_error(f"Analysis failed: {e}")

    def _cmd_price(self, args):
        """Get current price."""
        if not self.connected:
            self.print_error("Not connected to MT5")
            return

        if not args:
            # Default pairs
            instruments = config.DEFAULT_PAIRS
        else:
            instruments = [a.upper().replace("/", "_") for a in args]

        try:
            if len(instruments) == 1:
                price = self.client.get_price(instruments[0])
                pair = price["instrument"].replace("_", "/")
                self.print(f"\n{pair}: {price['bid']:.5f} / {price['ask']:.5f} (spread: {price['spread_pips']:.1f} pips)\n")
            else:
                prices = self.client.get_prices(instruments)
                self.print("")
                for p in prices:
                    pair = p["instrument"].replace("_", "/")
                    self.print(f"  {pair}: {p['bid']:.5f} / {p['ask']:.5f} ({p['spread_pips']:.1f} pips)")
                self.print("")

        except MT5Error as e:
            self.print_error(f"Failed to get price: {e}")

    def _cmd_account(self, args):
        """Show account info."""
        if not self.connected:
            self.print_error("Not connected to MT5")
            return

        try:
            account = self.client.get_account()
            daily_pnl = db.get_daily_pnl()

            content = f"""
Balance:     {account['currency']} {account['balance']:,.2f}
Equity:      {account['currency']} {account['nav']:,.2f}
Unrealized:  {account['currency']} {account['unrealized_pl']:+,.2f}

Margin Used:      {account['margin_used']:,.2f}
Margin Available: {account['margin_available']:,.2f}

Open Positions: {account['open_position_count']}/{config.MAX_CONCURRENT_POSITIONS}
Open Trades:    {account['open_trade_count']}

Today's P/L: {account['currency']} {daily_pnl:+,.2f}
"""
            mode = "DEMO" if config.is_demo() else "LIVE"
            self.print_panel(content, title=f"Account ({mode})")

        except MT5Error as e:
            self.print_error(f"Failed to get account: {e}")

    def _cmd_positions(self, args):
        """Show open positions."""
        if not self.connected:
            self.print_error("Not connected to MT5")
            return

        try:
            positions = self.client.get_positions()

            if not positions:
                self.print("\n[EMPTY] No open positions\n")
                return

            self.print("\n[DATA] OPEN POSITIONS\n")
            for pos in positions:
                pair = pos["instrument"].replace("_", "/")
                direction = pos["direction"]
                units = pos["long_units"] if direction == "LONG" else pos["short_units"]
                pl = pos["unrealized_pl"]
                pl_style = "green" if pl >= 0 else "red"

                self.print(f"  {pair} {direction} {units} units  P/L: ", end="")
                self.print(f"{pl:+.2f}", style=pl_style)
            self.print("")

        except MT5Error as e:
            self.print_error(f"Failed to get positions: {e}")

    def _cmd_trade(self, args):
        """Start trade workflow."""
        if not self.connected:
            self.print_error("Not connected to MT5")
            return

        if not self.last_analysis:
            self.print_warning("No recent analysis. Run 'analyze <PAIR>' first.")
            return

        analysis = self.last_analysis
        if not analysis["confidence"].can_trade:
            self.print_warning(f"Confidence too low ({analysis['confidence'].confidence_score}%). Not recommended.")
            if RICH_AVAILABLE:
                if not Confirm.ask("Proceed anyway?", default=False):
                    return
            else:
                if input("Proceed anyway? (y/n): ").lower() != 'y':
                    return

        self.print(f"\n[NOTE] TRADE SETUP: {analysis['instrument']}\n")
        self.print(f"Current Price: {analysis['price']['ask']:.5f}")
        self.print(f"Confidence: {analysis['confidence'].confidence_score}%")
        self.print(f"Risk Tier: {analysis['confidence'].risk_tier}")

        # Get trade parameters
        if RICH_AVAILABLE:
            direction = Prompt.ask("Direction", choices=["LONG", "SHORT"], default="LONG")
            sl = float(Prompt.ask("Stop Loss price"))
            tp = float(Prompt.ask("Take Profit price"))
        else:
            direction = input("Direction (LONG/SHORT): ").upper()
            sl = float(input("Stop Loss price: "))
            tp = float(input("Take Profit price: "))

        # This would continue with trade execution...
        self.print_warning("Trade execution coming in next update!")

    def _cmd_approve_llm(self, args):
        """Approve LLM recommendation and execute trade after confirmation."""
        if not self.connected:
            self.print_error("Not connected to MT5")
            return

        if not self.last_analysis:
            self.print_warning("No recent analysis. Run 'analyze <PAIR>' first.")
            return

        if not self.last_llm_result:
            self.print_warning("No LLM analysis available. Run 'analyze <PAIR>' first.")
            return

        if self.last_llm_result.recommendation.upper() != "TRADE":
            self.print_warning("LLM recommendation is SKIP. No trade prepared.")
            return

        analysis = self.last_analysis
        if not analysis["confidence"].can_trade:
            self.print_warning(f"Confidence too low ({analysis['confidence'].confidence_score}%). Not recommended.")
            return

        direction = "LONG" if analysis["technical"].trend == "BULLISH" else "SHORT"
        if self.last_llm_result.direction.upper() in ["LONG", "SHORT"]:
            direction = self.last_llm_result.direction.upper()

        price = analysis["price"]
        entry_price = price["ask"] if direction == "LONG" else price["bid"]

        atr_pips = analysis["technical"].atr_pips
        pip_value = 0.0001 if "JPY" not in analysis["instrument"] else 0.01
        if direction == "LONG":
            sl_price = entry_price - (atr_pips * 1.5 * pip_value)
            tp_price = entry_price + (atr_pips * 3.0 * pip_value)
        else:
            sl_price = entry_price + (atr_pips * 1.5 * pip_value)
            tp_price = entry_price - (atr_pips * 3.0 * pip_value)

        if self.last_llm_decision_id:
            try:
                db.update_llm_decision(self.last_llm_decision_id, approved=1)
            except Exception:
                pass

        self.print_panel(
            f"Instrument: {analysis['instrument']}\n"
            f"Direction: {direction}\n"
            f"Entry: {entry_price:.5f}\n"
            f"SL: {sl_price:.5f} ({atr_pips * 1.5:.1f} pips)\n"
            f"TP: {tp_price:.5f} ({atr_pips * 3.0:.1f} pips)\n"
            f"Confidence: {analysis['confidence'].confidence_score}%\n"
            f"Risk Tier: {analysis['confidence'].risk_tier}",
            title="LLM Trade Setup"
        )

        if RICH_AVAILABLE:
            if not Confirm.ask("Execute LLM trade now?", default=False):
                return
        else:
            if input("Execute LLM trade now? (y/n): ").lower() != 'y':
                return

        # Calculate risk amount from tier
        account = self.client.get_account()
        balance = account["balance"]
        risk_percent = analysis["confidence"].risk_percent
        risk_amount = balance * risk_percent

        # Position sizing using existing sizer
        size_result = calculate_position_size(
            equity=balance,
            confidence=analysis["confidence"].confidence_score,
            entry_price=entry_price,
            stop_loss=sl_price,
            instrument=analysis["instrument"]
        )

        if not size_result.can_trade:
            self.print_warning(f"Position size invalid: {size_result.reason}")
            return

        units = size_result.units if direction == "LONG" else -size_result.units

        result = self.order_manager.open_position(
            instrument=analysis["instrument"],
            units=units,
            stop_loss=sl_price,
            take_profit=tp_price,
            confidence=analysis["confidence"].confidence_score,
            risk_amount=risk_amount
        )

        if self.last_llm_decision_id:
            try:
                db.update_llm_decision(
                    self.last_llm_decision_id,
                    executed=1,
                    trade_id=result.order_id if result else None
                )
            except Exception:
                pass

        if result.success:
            self.print_success(f"LLM trade executed: {analysis['instrument']} {direction}")
        else:
            self.print_error(f"LLM trade failed: {result.error}")

    def _cmd_close(self, args):
        """Close a position."""
        if not self.connected:
            self.print_error("Not connected to MT5")
            return

        if not args:
            self.print_error("Usage: close <PAIR>")
            return

        instrument = args[0].upper().replace("/", "_")

        if RICH_AVAILABLE:
            if not Confirm.ask(f"Close {instrument} position?", default=False):
                return
        else:
            if input(f"Close {instrument}? (y/n): ").lower() != 'y':
                return

        try:
            # Get position info before closing (for learning)
            positions = self.client.get_positions()
            pos_info = next((p for p in positions if p["instrument"] == instrument), None)

            result = self.order_manager.close_position(instrument)
            if result.success:
                # Show P/L from raw response if available
                pnl = result.raw_response.get("pnl", 0) if result.raw_response else 0
                self.print_success(f"Position closed: {instrument} (P/L: {pnl:+.2f})")

                # Note: trade_closed_handler is called inside order_manager.close_position()
                # If it was a loss, the learning system has been triggered
                if pnl < 0:
                    self.print_warning("Loss recorded. Error analysis triggered for learning.")
            else:
                self.print_error(f"Failed: {result.error}")
        except MT5Error as e:
            self.print_error(f"Close failed: {e}")

    def _cmd_emergency(self, args):
        """Emergency close all positions."""
        if not self.connected:
            self.print_error("Not connected to MT5")
            return

        self.print_warning("⚠️  EMERGENCY CLOSE - This will close ALL positions!")

        if RICH_AVAILABLE:
            if not Confirm.ask("Are you sure?", default=False):
                return
        else:
            if input("Type 'YES' to confirm: ") != 'YES':
                return

        try:
            results = self.order_manager.close_all_positions()
            closed = sum(1 for r in results if r.success)
            self.print_success(f"Closed {closed} position(s)")
        except MT5Error as e:
            self.print_error(f"Emergency close failed: {e}")

    def _cmd_report(self, args):
        """Show daily report."""
        stats = db.get_performance_stats()
        daily_pnl = db.get_daily_pnl()
        trades_today = db.get_trades_today()

        content = f"""
[DATE] Today ({datetime.now().strftime('%Y-%m-%d')})
----------------------
Trades: {len(trades_today)}
P/L:    ${daily_pnl:+.2f}

[DATA] All Time
----------------------
Total Trades: {stats['total_trades']}
Win Rate:     {stats['win_rate']:.1f}%
Total P/L:    ${stats['total_pnl']:+.2f}
Avg Win:      ${stats['avg_win']:.2f}
Avg Loss:     ${stats['avg_loss']:.2f}
Profit Factor: {stats['profit_factor']:.2f}
"""
        self.print_panel(content, title="Performance Report")

    def _cmd_settings(self, args):
        """Show settings."""
        cfg = settings_manager.get_config()

        content = f"""
Interface: {cfg.get('interface', {}).get('name', 'AI Trader')} v{cfg.get('interface', {}).get('version', '1.0')}
Language:  {cfg.get('interface', {}).get('language', 'hr')}

AI Settings:
  Model: {cfg.get('ai', {}).get('model', 'claude')}
  Temperature: {cfg.get('ai', {}).get('temperature', 0.3)}
  Adversarial: {cfg.get('ai', {}).get('use_adversarial', True)}
  RAG: {cfg.get('ai', {}).get('use_rag', True)}
  Sentiment: {cfg.get('ai', {}).get('use_sentiment', True)}

Analysis:
  Timeframe: {cfg.get('analysis', {}).get('default_timeframe', 'H4')}
  Min R:R: {cfg.get('analysis', {}).get('min_rr_ratio', 1.5)}

Settings folder: settings/
"""
        self.print_panel(content, title="Settings")

    def _cmd_skills(self, args):
        """List available skills."""
        skills = settings_manager.list_skills()

        self.print("\n[DOCS] AVAILABLE SKILLS\n")
        for skill in skills:
            self.print(f"  • {skill}")

        self.print(f"\n  Location: settings/skills/")
        self.print("  Add new skills by creating .md files\n")

    def _cmd_prompt(self, args):
        """Show system prompt."""
        prompt = settings_manager.get_system_prompt()

        if len(prompt) > 500:
            prompt = prompt[:500] + "\n... (truncated)"

        self.print_panel(prompt, title="System Prompt (preview)")
        self.print("  Full prompt: settings/system_prompt.md\n")

    def _cmd_clear(self, args):
        """Clear screen."""
        if self.console:
            self.console.clear()
        else:
            print("\n" * 50)

    def _cmd_exit(self, args):
        """Exit the interface."""
        self.running = False


def run_interface():
    """Run the trading interface."""
    interface = TradingInterface()
    interface.start()


if __name__ == "__main__":
    run_interface()
