"""
Logging setup using loguru.

Three log types:
1. Trade Log - every executed trade
2. Decision Log - every analysis
3. Error Log - all losses with root cause

Usage:
    from src.utils.logger import logger, log_trade, log_decision, log_error

    logger.info("General message")
    log_trade(trade_data)
    log_decision(decision_data)
    log_error(error_data)
"""

import sys
from pathlib import Path
from datetime import datetime
from loguru import logger as _logger

from src.utils.config import config

# Get paths
_dev_dir = Path(__file__).parent.parent.parent
_logs_dir = _dev_dir / "logs"

# Ensure log directories exist
(_logs_dir / "trades").mkdir(parents=True, exist_ok=True)
(_logs_dir / "decisions").mkdir(parents=True, exist_ok=True)
(_logs_dir / "errors").mkdir(parents=True, exist_ok=True)

# Remove default handler
_logger.remove()

# Add console handler
_logger.add(
    sys.stderr,
    level=config.LOG_LEVEL,
    format="<level>{level: <8}</level> | <cyan>{message}</cyan>",
    colorize=True
)

# Add general file handler
_logger.add(
    _logs_dir / "app_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    rotation="1 day",
    retention="30 days"
)

# Export configured logger
logger = _logger


def log_trade(trade_data: dict) -> None:
    """
    Log executed trade to trades folder.

    Args:
        trade_data: Dict with trade details
            - trade_id: str
            - instrument: str
            - direction: str (LONG/SHORT)
            - entry_price: float
            - stop_loss: float
            - take_profit: float
            - units: int
            - risk_amount: float
            - risk_percent: float
            - confidence_score: int
    """
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = _logs_dir / "trades" / f"trades_{today}.log"

    timestamp = datetime.now().isoformat()

    log_entry = (
        f"\n{'='*60}\n"
        f"TRADE: {trade_data.get('trade_id', 'N/A')}\n"
        f"Time: {timestamp}\n"
        f"{'='*60}\n"
        f"Instrument: {trade_data.get('instrument')}\n"
        f"Direction:  {trade_data.get('direction')}\n"
        f"Entry:      {trade_data.get('entry_price')}\n"
        f"Stop Loss:  {trade_data.get('stop_loss')}\n"
        f"Take Profit: {trade_data.get('take_profit')}\n"
        f"Units:      {trade_data.get('units')}\n"
        f"Risk:       ${trade_data.get('risk_amount', 0):.2f} ({trade_data.get('risk_percent', 0)*100:.1f}%)\n"
        f"Confidence: {trade_data.get('confidence_score')}%\n"
        f"{'='*60}\n"
    )

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

    logger.info(f"Trade logged: {trade_data.get('trade_id')} - {trade_data.get('instrument')} {trade_data.get('direction')}")


def log_decision(decision_data: dict) -> None:
    """
    Log analysis decision to decisions folder.

    Args:
        decision_data: Dict with decision details
            - instrument: str
            - technical_score: int
            - sentiment_score: float
            - confidence_score: int
            - bull_case: str
            - bear_case: str
            - recommendation: str
            - decision: str (TRADE/SKIP/WAIT)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = _logs_dir / "decisions" / f"decisions_{today}.log"

    timestamp = datetime.now().isoformat()

    log_entry = (
        f"\n{'='*60}\n"
        f"DECISION: {decision_data.get('instrument')}\n"
        f"Time: {timestamp}\n"
        f"{'='*60}\n"
        f"Technical Score:  {decision_data.get('technical_score')}\n"
        f"Sentiment Score:  {decision_data.get('sentiment_score')}\n"
        f"Confidence Score: {decision_data.get('confidence_score')}\n"
        f"\nBULL CASE:\n{decision_data.get('bull_case', 'N/A')}\n"
        f"\nBEAR CASE:\n{decision_data.get('bear_case', 'N/A')}\n"
        f"\nRecommendation: {decision_data.get('recommendation')}\n"
        f"Decision: {decision_data.get('decision')}\n"
        f"{'='*60}\n"
    )

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

    logger.debug(f"Decision logged: {decision_data.get('instrument')} -> {decision_data.get('decision')}")


def log_error(error_data: dict) -> None:
    """
    Log trade error/loss to errors folder.

    Args:
        error_data: Dict with error details
            - trade_id: str
            - instrument: str
            - loss_amount: float
            - error_category: str (NEWS_IGNORED, OVERCONFIDENT, etc.)
            - root_cause: str
            - lessons: str
    """
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = _logs_dir / "errors" / f"errors_{today}.log"

    timestamp = datetime.now().isoformat()

    log_entry = (
        f"\n{'='*60}\n"
        f"ERROR: {error_data.get('trade_id')}\n"
        f"Time: {timestamp}\n"
        f"{'='*60}\n"
        f"Instrument: {error_data.get('instrument')}\n"
        f"Loss: ${error_data.get('loss_amount', 0):.2f}\n"
        f"Category: {error_data.get('error_category')}\n"
        f"\nRoot Cause:\n{error_data.get('root_cause', 'N/A')}\n"
        f"\nLessons Learned:\n{error_data.get('lessons', 'N/A')}\n"
        f"{'='*60}\n"
    )

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

    logger.warning(f"Error logged: {error_data.get('trade_id')} - {error_data.get('error_category')}")
