"""
MT5 History Sync Utility.

Syncs closed trades from MetaTrader 5 into the AI Trader database.
This allows the dashboard to show trades executed directly in MT5.

Usage:
    # From Python
    from src.utils.mt5_sync import sync_mt5_history, get_sync_status

    result = sync_mt5_history(days=30)
    print(f"Imported {result['imported']} trades")

    # From CLI
    python -m src.utils.mt5_sync --days 30
"""

from datetime import datetime, timezone
from typing import Optional

from src.trading.mt5_client import MT5Client, MT5Error
from src.utils.database import db
from src.utils.logger import logger


def _run_post_trade_analysis(trade: dict) -> dict:
    """Run post-trade analysis, feed learning engine, and optimize settings."""
    try:
        from src.analysis.post_trade_analyzer import PostTradeAnalyzer
        from src.analysis.learning_engine import learning_engine
        from src.analysis.adaptive_settings import adaptive_settings

        analyzer = PostTradeAnalyzer()
        analysis = analyzer.analyze_trade(trade)

        # Feed to learning engine
        result = learning_engine.learn_from_trade(trade, analysis)

        logger.info(f"Post-trade analysis complete for {trade['trade_id']}: {analysis.outcome.value}")

        # Run adaptive settings optimization after every trade
        try:
            optimization = adaptive_settings.analyze_and_optimize()
            if optimization.get("adjustments_made"):
                for adj in optimization["adjustments_made"]:
                    logger.info(f"SELF-TUNED: {adj['setting']} -> {adj['new_value']} ({adj['reason']})")
            result["settings_optimized"] = len(optimization.get("adjustments_made", []))
        except Exception as opt_err:
            logger.warning(f"Adaptive settings optimization failed: {opt_err}")
            result["settings_optimized"] = 0

        return {
            "success": True,
            "outcome": analysis.outcome.value,
            "was_good_trade": analysis.was_good_trade,
            "patterns_updated": result.get("patterns_updated", 0),
            "settings_optimized": result.get("settings_optimized", 0)
        }
    except Exception as e:
        logger.warning(f"Post-trade analysis failed for {trade.get('trade_id')}: {e}")
        return {"success": False, "error": str(e)}


def sync_mt5_history(
    days: int = 30,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    client: Optional[MT5Client] = None
) -> dict:
    """
    Sync MT5 trade history to database.

    Fetches closed trades from MT5 and imports any that aren't
    already in the database.

    Args:
        days: Number of days to sync (default 30)
        from_date: Start date (overrides days)
        to_date: End date (defaults to now)
        client: Optional MT5Client instance (creates new if not provided)

    Returns:
        Dict with sync results:
        - success: Whether sync completed successfully
        - total: Total trades found in MT5
        - imported: Number of new trades imported
        - skipped: Number of trades already in DB
        - errors: Number of import errors
        - mt5_balance: Current MT5 balance
        - db_total_pnl: Total P/L in database after sync
        - message: Human readable summary
    """
    result = {
        "success": False,
        "total": 0,
        "imported": 0,
        "skipped": 0,
        "errors": 0,
        "mt5_balance": None,
        "db_total_pnl": None,
        "message": ""
    }

    try:
        # Connect to MT5
        if client is None:
            client = MT5Client()

        if not client.is_connected():
            result["message"] = "Failed to connect to MT5"
            logger.error(result["message"])
            return result

        # Get account info
        account = client.get_account()
        result["mt5_balance"] = account.get("balance")

        # Fetch history from MT5
        logger.info(f"Fetching MT5 history for last {days} days...")
        mt5_trades = client.get_history(days=days, from_date=from_date, to_date=to_date)

        if not mt5_trades:
            result["success"] = True
            result["message"] = "No closed trades found in MT5 history"
            return result

        # Sync to database
        sync_result = db.sync_from_mt5(mt5_trades)

        result["total"] = sync_result["total"]
        result["imported"] = sync_result["imported"]
        result["skipped"] = sync_result["skipped"]
        result["errors"] = sync_result["errors"]

        # Run post-trade analysis on imported trades to feed learning engine
        analyzed_count = 0
        if sync_result["imported"] > 0:
            logger.info(f"Running post-trade analysis on {sync_result['imported']} new trades...")
            for trade in mt5_trades:
                if trade.get("trade_id") in sync_result.get("trades_imported", []):
                    analysis_result = _run_post_trade_analysis(trade)
                    if analysis_result.get("success"):
                        analyzed_count += 1

        result["analyzed"] = analyzed_count

        # Get updated stats
        stats = db.get_performance_stats()
        result["db_total_pnl"] = stats.get("total_pnl", 0)

        result["success"] = True
        result["message"] = (
            f"Sync complete: {result['imported']} imported, "
            f"{analyzed_count} analyzed for learning, "
            f"{result['skipped']} already in DB"
        )

        logger.info(result["message"])
        return result

    except MT5Error as e:
        result["message"] = f"MT5 error: {e}"
        logger.error(result["message"])
        return result

    except Exception as e:
        result["message"] = f"Sync error: {e}"
        logger.error(result["message"])
        return result


def get_sync_status() -> dict:
    """
    Get current sync status.

    Compares MT5 account state with database to show if sync is needed.

    Returns:
        Dict with:
        - mt5_connected: Whether MT5 is connected
        - mt5_balance: Current MT5 balance
        - mt5_closed_trades: Number of closed trades in MT5 (last 30 days)
        - db_closed_trades: Number of closed trades in database
        - needs_sync: Whether sync is recommended
        - balance_diff: Difference between MT5 and DB P/L
    """
    status = {
        "mt5_connected": False,
        "mt5_balance": None,
        "mt5_closed_trades": 0,
        "db_closed_trades": 0,
        "needs_sync": False,
        "balance_diff": None
    }

    try:
        client = MT5Client()

        if not client.is_connected():
            return status

        status["mt5_connected"] = True

        # Get MT5 info
        account = client.get_account()
        status["mt5_balance"] = account.get("balance")

        # Count MT5 history
        mt5_trades = client.get_history(days=30)
        status["mt5_closed_trades"] = len(mt5_trades)

        # Count DB trades
        db_stats = db.get_performance_stats()
        status["db_closed_trades"] = db_stats.get("total_trades", 0)

        # Check if sync needed
        if status["mt5_closed_trades"] > status["db_closed_trades"]:
            status["needs_sync"] = True

        # Calculate balance difference
        db_pnl = db_stats.get("total_pnl", 0)
        mt5_pnl = sum(t.get("pnl", 0) for t in mt5_trades)
        status["balance_diff"] = round(mt5_pnl - db_pnl, 2)

        if abs(status["balance_diff"]) > 1:
            status["needs_sync"] = True

        return status

    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return status


def auto_sync_if_needed(threshold_trades: int = 1) -> Optional[dict]:
    """
    Automatically sync if there are new trades.

    Args:
        threshold_trades: Minimum new trades to trigger sync

    Returns:
        Sync result if sync was performed, None otherwise
    """
    status = get_sync_status()

    if not status["mt5_connected"]:
        return None

    trade_diff = status["mt5_closed_trades"] - status["db_closed_trades"]

    if trade_diff >= threshold_trades or status["needs_sync"]:
        logger.info(f"Auto-sync triggered: {trade_diff} new trades detected")
        return sync_mt5_history()

    return None


def bootstrap_learning(days: int = 30) -> dict:
    """
    Analyze all existing trades and feed learning engine.

    Use this to bootstrap learning from historical trades
    that were synced before the learning engine was added.

    Args:
        days: Analyze trades from last N days

    Returns:
        Dict with bootstrap results
    """
    result = {
        "success": False,
        "trades_found": 0,
        "trades_analyzed": 0,
        "already_analyzed": 0,
        "errors": 0,
        "patterns_total": 0
    }

    try:
        from src.analysis.post_trade_analyzer import PostTradeAnalyzer
        from src.analysis.learning_engine import learning_engine

        # Get all closed trades from database
        with db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT trade_id, timestamp, closed_at, instrument, direction,
                       entry_price, exit_price, pnl, pnl_percent
                FROM trades
                WHERE status = 'CLOSED'
                ORDER BY closed_at DESC
            """)
            trades = [dict(row) for row in cursor.fetchall()]

        result["trades_found"] = len(trades)

        if not trades:
            result["success"] = True
            result["message"] = "No trades to analyze"
            return result

        # Check which are already analyzed
        with db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT trade_id FROM trade_analyses")
            analyzed_ids = {row[0] for row in cursor.fetchall()}

        analyzer = PostTradeAnalyzer()

        for trade in trades:
            trade_id = trade.get("trade_id")

            if trade_id in analyzed_ids:
                result["already_analyzed"] += 1
                continue

            try:
                # Run analysis
                analysis = analyzer.analyze_trade({
                    "trade_id": trade_id,
                    "instrument": trade.get("instrument"),
                    "direction": trade.get("direction"),
                    "entry_price": trade.get("entry_price"),
                    "exit_price": trade.get("exit_price"),
                    "opened_at": trade.get("timestamp"),
                    "closed_at": trade.get("closed_at") or trade.get("timestamp"),
                    "pnl": trade.get("pnl")
                })

                # Feed to learning engine
                learn_result = learning_engine.learn_from_trade(trade, analysis)
                result["trades_analyzed"] += 1
                result["patterns_total"] += learn_result.get("patterns_updated", 0)

                logger.info(f"Bootstrapped learning for {trade_id}: {analysis.outcome.value}")

            except Exception as e:
                logger.warning(f"Failed to analyze {trade_id}: {e}")
                result["errors"] += 1

        result["success"] = True
        result["message"] = (
            f"Bootstrap complete: {result['trades_analyzed']} analyzed, "
            f"{result['already_analyzed']} already done, "
            f"{result['errors']} errors"
        )

        logger.info(result["message"])
        return result

    except Exception as e:
        result["message"] = f"Bootstrap failed: {e}"
        logger.error(result["message"])
        return result


# CLI interface
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Sync MT5 trade history to database")
    parser.add_argument("--days", type=int, default=30, help="Days of history to sync")
    parser.add_argument("--status", action="store_true", help="Show sync status only")
    parser.add_argument("--auto", action="store_true", help="Auto-sync if needed")
    parser.add_argument("--bootstrap", action="store_true", help="Bootstrap learning from existing trades")
    parser.add_argument("--summary", action="store_true", help="Show learning summary")

    args = parser.parse_args()

    print("=" * 60)
    print("MT5 History Sync")
    print("=" * 60)

    if args.status:
        status = get_sync_status()
        print(f"\nMT5 Connected: {status['mt5_connected']}")
        print(f"MT5 Balance: {status['mt5_balance']}")
        print(f"MT5 Closed Trades (30d): {status['mt5_closed_trades']}")
        print(f"DB Closed Trades: {status['db_closed_trades']}")
        print(f"Needs Sync: {status['needs_sync']}")
        print(f"P/L Difference: {status['balance_diff']}")
        sys.exit(0)

    if args.bootstrap:
        print("\nBootstrapping learning from existing trades...")
        result = bootstrap_learning(days=args.days)
        print(f"\nResult: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"Trades found: {result['trades_found']}")
        print(f"Analyzed: {result['trades_analyzed']}")
        print(f"Already done: {result['already_analyzed']}")
        print(f"Errors: {result['errors']}")
        print(f"Patterns updated: {result['patterns_total']}")
        sys.exit(0 if result['success'] else 1)

    if args.summary:
        from src.analysis.learning_engine import learning_engine
        summary = learning_engine.get_learning_summary()
        print("\n=== LEARNING SUMMARY ===")
        print(f"Total trades analyzed: {summary['total_trades_analyzed']}")
        print("\nBy Instrument:")
        for inst, data in summary['instruments'].items():
            print(f"  {inst}: {data['total_trades']} trades, "
                  f"{data['win_rate']:.1f}% win rate, "
                  f"{data['total_pnl_pips']:.1f} pips")
        print("\nBest Patterns:")
        for p in summary['best_patterns'][:3]:
            print(f"  {p['pattern']}: {p['win_rate']}% ({p['trades']} trades)")
        print("\nWorst Patterns:")
        for p in summary['worst_patterns'][:3]:
            print(f"  {p['pattern']}: {p['win_rate']}% ({p['trades']} trades)")
        print("\nKey Insights:")
        for insight in summary['key_insights']:
            print(f"  - {insight}")
        sys.exit(0)

    if args.auto:
        result = auto_sync_if_needed()
        if result is None:
            print("No sync needed")
            sys.exit(0)
    else:
        result = sync_mt5_history(days=args.days)

    print(f"\nResult: {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"Message: {result['message']}")
    print(f"\nMT5 Balance: {result['mt5_balance']}")
    print(f"Total in MT5: {result['total']}")
    print(f"Imported: {result['imported']}")
    print(f"Skipped: {result['skipped']}")
    print(f"Errors: {result['errors']}")
    print(f"DB Total P/L: {result['db_total_pnl']}")

    print("=" * 60)
    sys.exit(0 if result['success'] else 1)
