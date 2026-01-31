"""
Trade Lifecycle Manager - Handles trade closure and learning.

Central handler for the trade lifecycle:
1. Records trade closure in database
2. Analyzes losses
3. Logs errors for RAG
4. Generates lessons

Usage:
    from src.trading.trade_lifecycle import trade_closed_handler

    # When a trade is closed:
    trade_closed_handler(
        trade_id="T123",
        instrument="EUR_USD",
        direction="LONG",
        entry_price=1.0850,
        exit_price=1.0820,
        pnl=-30.0,
        pnl_percent=-0.6,
        close_reason="MANUAL",
        confidence_score=75,
        technical_score=65,
        sentiment_score=0.3,
        adversarial_adjustment=-5
    )
"""

from datetime import datetime
from typing import Optional

from src.utils.logger import logger
from src.utils.database import db
from src.core.settings_manager import settings_manager
from src.analysis.error_analyzer import ErrorAnalyzer, ErrorCategory


def trade_closed_handler(
    trade_id: str,
    instrument: str,
    direction: str,
    entry_price: float,
    exit_price: float,
    pnl: float,
    pnl_percent: float,
    close_reason: str = "MANUAL",
    # Original analysis data (for error analysis)
    confidence_score: Optional[int] = None,
    technical_score: Optional[int] = None,
    sentiment_score: Optional[float] = None,
    adversarial_adjustment: Optional[int] = None,
    bull_case: Optional[str] = None,
    bear_case: Optional[str] = None,
    # Market context
    atr: Optional[float] = None,
    price_move_pips: Optional[float] = None,
    bear_strength: Optional[int] = None
) -> dict:
    """
    Central handler for trade closure.

    Called when a trade is closed (manually, SL, TP, or emergency).
    Records the trade, analyzes errors if loss, and generates lessons.

    Args:
        trade_id: Unique trade identifier
        instrument: Currency pair (e.g., "EUR_USD")
        direction: Trade direction ("LONG" or "SHORT")
        entry_price: Entry price
        exit_price: Exit price
        pnl: Profit/loss amount
        pnl_percent: P/L as percentage of account
        close_reason: Reason for close (MANUAL, SL, TP, EMERGENCY)

        # Original analysis data
        confidence_score: Original confidence score (0-100)
        technical_score: Technical analysis score (0-100)
        sentiment_score: Sentiment score (-1 to +1)
        adversarial_adjustment: Adversarial adjustment value

        # Market context
        atr: Average True Range at time of trade
        price_move_pips: How much price moved
        bear_strength: Strength of bear case (0-100)

    Returns:
        dict with:
        - success: bool
        - trade_updated: bool
        - error_logged: bool
        - lesson_added: bool
        - error_category: str (if loss)
    """
    result = {
        "success": False,
        "trade_updated": False,
        "error_logged": False,
        "lesson_added": False,
        "error_category": None
    }

    logger.info(
        f"Trade closed handler: {trade_id} {instrument} {direction} "
        f"PnL: {pnl:+.2f} ({pnl_percent:+.2f}%) - {close_reason}"
    )

    try:
        # === STEP 1: Update trade in database ===
        trade_updated = db.close_trade(
            trade_id=trade_id,
            exit_price=exit_price,
            pnl=pnl,
            pnl_percent=pnl_percent,
            close_reason=close_reason
        )
        result["trade_updated"] = trade_updated

        if not trade_updated:
            # Trade might not be in DB (opened before system was in place)
            logger.warning(f"Trade {trade_id} not found in database, skipping update")

        # === STEP 2: If loss, analyze error ===
        if pnl < 0:
            logger.info(f"Analyzing loss for trade {trade_id}")

            # Build trade data for analyzer
            trade_data = {
                "trade_id": trade_id,
                "instrument": instrument,
                "direction": direction,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "confidence_score": confidence_score or 0,
                "sentiment_score": sentiment_score or 0,
                "bull_case": bull_case,
                "bear_case": bear_case,
                "timestamp": _get_trade_timestamp(trade_id),
                "closed_at": datetime.now().isoformat()
            }

            # Build market context
            market_context = {
                "technical_score": technical_score or 0,
                "adversarial_adjustment": adversarial_adjustment or 0,
                "atr": atr or 0,
                "price_move_pips": price_move_pips or _calculate_price_move(
                    entry_price, exit_price, instrument
                ),
                "bear_strength": bear_strength or 0
            }

            # Analyze the error
            analyzer = ErrorAnalyzer()
            analysis = analyzer.analyze_loss(trade_data, market_context)

            result["error_category"] = analysis.category.value

            # === STEP 3: Log error to database for RAG ===
            error_data = {
                "trade_id": trade_id,
                "timestamp": datetime.now().isoformat(),
                "instrument": instrument,
                "direction": direction,
                "loss_amount": abs(pnl),
                "loss_percent": abs(pnl_percent),
                "error_category": analysis.category.value,
                "root_cause": analysis.root_cause,
                "lessons": analysis.lesson,
                "tags": analysis.tags
            }

            db.log_error(error_data)
            result["error_logged"] = True

            logger.info(
                f"Error logged: {analysis.category.value} - {analysis.root_cause}"
            )

            # === STEP 4: Add lesson to knowledge base if significant ===
            if analysis.should_add_lesson and analysis.lesson_text:
                settings_manager.add_lesson(analysis.lesson_text)
                result["lesson_added"] = True

                logger.info(
                    f"Lesson added to knowledge base for {instrument} "
                    f"({analysis.category.value})"
                )

        result["success"] = True

    except Exception as e:
        logger.exception(f"Error in trade_closed_handler: {e}")
        result["success"] = False

    return result


def _get_trade_timestamp(trade_id: str) -> str:
    """Get original trade timestamp from database."""
    try:
        trade = db.get_trade(trade_id)
        if trade:
            return trade.get("timestamp", datetime.now().isoformat())
    except Exception:
        pass
    return datetime.now().isoformat()


def _calculate_price_move(
    entry_price: float,
    exit_price: float,
    instrument: str
) -> float:
    """Calculate price move in pips."""
    if entry_price == 0:
        return 0

    diff = abs(exit_price - entry_price)

    # JPY pairs have 2 decimal places, others have 4
    if "JPY" in instrument:
        pips = diff * 100
    else:
        pips = diff * 10000

    return round(pips, 1)


def get_learning_stats() -> dict:
    """
    Get statistics about the learning system.

    Returns:
        dict with error category counts, recent lessons, etc.
    """
    try:
        # Error category breakdown
        categories = db.get_error_categories_summary()

        # Top repeated errors
        repeated = db.get_top_repeated_errors(limit=3)

        # Performance impact
        stats = db.get_performance_stats()

        return {
            "error_categories": categories,
            "top_repeated_errors": repeated,
            "total_errors_logged": sum(categories.values()) if categories else 0,
            "performance_stats": stats
        }

    except Exception as e:
        logger.error(f"Error getting learning stats: {e}")
        return {}


# Convenience function for simple closure
def record_trade_close(
    instrument: str,
    exit_price: float,
    pnl: float,
    close_reason: str = "MANUAL"
) -> dict:
    """
    Simplified trade closure for cases where we don't have full context.

    Tries to find the trade in database by instrument and updates it.

    Args:
        instrument: Currency pair
        exit_price: Exit price
        pnl: Profit/loss amount
        close_reason: Reason for close

    Returns:
        Result dict
    """
    # Find open trade for this instrument
    open_trades = db.get_open_trades()
    matching = [t for t in open_trades if t.get("instrument") == instrument]

    if not matching:
        logger.warning(f"No open trade found for {instrument} in database")
        return {"success": False, "error": "No matching trade found"}

    trade = matching[0]

    # Calculate pnl_percent (rough estimate)
    # Assume 50,000 EUR account for demo
    account_balance = 50000
    pnl_percent = (pnl / account_balance) * 100

    return trade_closed_handler(
        trade_id=trade.get("trade_id", "UNKNOWN"),
        instrument=instrument,
        direction=trade.get("direction", "UNKNOWN"),
        entry_price=trade.get("entry_price", 0),
        exit_price=exit_price,
        pnl=pnl,
        pnl_percent=pnl_percent,
        close_reason=close_reason,
        confidence_score=trade.get("confidence_score"),
        sentiment_score=trade.get("sentiment_score"),
        bull_case=trade.get("bull_case"),
        bear_case=trade.get("bear_case")
    )
