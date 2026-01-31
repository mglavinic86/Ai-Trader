"""
SQLite Database for trade logging and RAG error memory.

Tables:
- trades: All executed trades
- decisions: All analysis decisions
- errors: Trade errors for RAG learning

Usage:
    from src.utils.database import Database, db

    # Log a trade
    db.log_trade({...})

    # Query similar errors
    errors = db.find_similar_errors("EUR_USD", "LONG")
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from src.utils.logger import logger


# Database path
_dev_dir = Path(__file__).parent.parent.parent
_db_path = _dev_dir / "data" / "trades.db"


class Database:
    """SQLite database manager for AI Trader."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database.

        Args:
            db_path: Path to SQLite file (uses default if None)
        """
        self.db_path = db_path or _db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
        logger.info(f"Database initialized: {self.db_path}")

    @contextmanager
    def _connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_tables(self):
        """Create database tables if they don't exist."""
        with self._connection() as conn:
            cursor = conn.cursor()

            # Trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL,
                    exit_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    units INTEGER,
                    risk_amount REAL,
                    risk_percent REAL,
                    confidence_score INTEGER,
                    pnl REAL,
                    pnl_percent REAL,
                    status TEXT DEFAULT 'OPEN',
                    closed_at TEXT,
                    close_reason TEXT,
                    bull_case TEXT,
                    bear_case TEXT,
                    sentiment_score REAL,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Decisions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    technical_score INTEGER,
                    fundamental_score INTEGER,
                    sentiment_score REAL,
                    confidence_score INTEGER,
                    bull_case TEXT,
                    bear_case TEXT,
                    recommendation TEXT,
                    decision TEXT NOT NULL,
                    trade_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Errors table (RAG memory)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    direction TEXT,
                    loss_amount REAL,
                    loss_percent REAL,
                    error_category TEXT NOT NULL,
                    root_cause TEXT,
                    lessons TEXT,
                    tags TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_instrument ON trades(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_instrument ON errors(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_category ON errors(error_category)")

    # ===================
    # Trade Operations
    # ===================

    def log_trade(self, trade_data: dict) -> int:
        """
        Log a new trade to database.

        Args:
            trade_data: Trade details dict

        Returns:
            Trade row ID
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO trades (
                    trade_id, timestamp, instrument, direction,
                    entry_price, stop_loss, take_profit, units,
                    risk_amount, risk_percent, confidence_score,
                    bull_case, bear_case, sentiment_score, status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get("trade_id"),
                trade_data.get("timestamp", datetime.now().isoformat()),
                trade_data.get("instrument"),
                trade_data.get("direction"),
                trade_data.get("entry_price"),
                trade_data.get("stop_loss"),
                trade_data.get("take_profit"),
                trade_data.get("units"),
                trade_data.get("risk_amount"),
                trade_data.get("risk_percent"),
                trade_data.get("confidence_score"),
                trade_data.get("bull_case"),
                trade_data.get("bear_case"),
                trade_data.get("sentiment_score"),
                "OPEN",
                trade_data.get("notes")
            ))

            logger.info(f"Trade logged to DB: {trade_data.get('trade_id')}")
            return cursor.lastrowid

    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        pnl: float,
        pnl_percent: float,
        close_reason: str = "MANUAL"
    ) -> bool:
        """
        Close a trade and record P/L.

        Args:
            trade_id: Trade ID
            exit_price: Exit price
            pnl: Profit/loss amount
            pnl_percent: P/L as percentage
            close_reason: Reason for close (MANUAL, SL, TP, etc.)

        Returns:
            True if successful
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE trades SET
                    exit_price = ?,
                    pnl = ?,
                    pnl_percent = ?,
                    status = 'CLOSED',
                    closed_at = ?,
                    close_reason = ?
                WHERE trade_id = ?
            """, (
                exit_price,
                pnl,
                pnl_percent,
                datetime.now().isoformat(),
                close_reason,
                trade_id
            ))

            logger.info(f"Trade closed in DB: {trade_id}, P/L: {pnl:.2f}")
            return cursor.rowcount > 0

    def get_trade(self, trade_id: str) -> Optional[dict]:
        """Get trade by ID."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_open_trades(self) -> list[dict]:
        """Get all open trades."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_trades_today(self) -> list[dict]:
        """Get all trades from today."""
        today = datetime.now().strftime("%Y-%m-%d")
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM trades WHERE timestamp LIKE ? ORDER BY timestamp DESC",
                (f"{today}%",)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_daily_pnl(self) -> float:
        """Get total P/L for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE closed_at LIKE ?",
                (f"{today}%",)
            )
            result = cursor.fetchone()
            return float(result[0]) if result else 0.0

    # ===================
    # Decision Operations
    # ===================

    def log_decision(self, decision_data: dict) -> int:
        """
        Log an analysis decision.

        Args:
            decision_data: Decision details

        Returns:
            Decision row ID
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO decisions (
                    timestamp, instrument, technical_score, fundamental_score,
                    sentiment_score, confidence_score, bull_case, bear_case,
                    recommendation, decision, trade_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision_data.get("timestamp", datetime.now().isoformat()),
                decision_data.get("instrument"),
                decision_data.get("technical_score"),
                decision_data.get("fundamental_score"),
                decision_data.get("sentiment_score"),
                decision_data.get("confidence_score"),
                decision_data.get("bull_case"),
                decision_data.get("bear_case"),
                decision_data.get("recommendation"),
                decision_data.get("decision"),
                decision_data.get("trade_id")
            ))

            return cursor.lastrowid

    # ===================
    # Error/RAG Operations
    # ===================

    def log_error(self, error_data: dict) -> int:
        """
        Log a trade error for RAG learning.

        Args:
            error_data: Error details

        Returns:
            Error row ID
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            # Convert tags list to JSON string
            tags = error_data.get("tags", [])
            tags_json = json.dumps(tags) if tags else "[]"

            cursor.execute("""
                INSERT INTO errors (
                    trade_id, timestamp, instrument, direction,
                    loss_amount, loss_percent, error_category,
                    root_cause, lessons, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                error_data.get("trade_id"),
                error_data.get("timestamp", datetime.now().isoformat()),
                error_data.get("instrument"),
                error_data.get("direction"),
                error_data.get("loss_amount"),
                error_data.get("loss_percent"),
                error_data.get("error_category"),
                error_data.get("root_cause"),
                error_data.get("lessons"),
                tags_json
            ))

            logger.warning(f"Error logged to DB: {error_data.get('trade_id')} - {error_data.get('error_category')}")
            return cursor.lastrowid

    def find_similar_errors(
        self,
        instrument: str,
        direction: Optional[str] = None,
        limit: int = 5
    ) -> list[dict]:
        """
        Find similar past errors (RAG query).

        Args:
            instrument: Currency pair
            direction: Trade direction (LONG/SHORT)
            limit: Max results

        Returns:
            List of similar errors
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            if direction:
                cursor.execute("""
                    SELECT * FROM errors
                    WHERE instrument = ? AND direction = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (instrument, direction, limit))
            else:
                cursor.execute("""
                    SELECT * FROM errors
                    WHERE instrument = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (instrument, limit))

            errors = []
            for row in cursor.fetchall():
                error = dict(row)
                # Parse tags JSON
                error["tags"] = json.loads(error.get("tags", "[]"))
                errors.append(error)

            return errors

    def get_error_categories_summary(self) -> dict:
        """Get count of errors by category."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT error_category, COUNT(*) as count
                FROM errors
                GROUP BY error_category
                ORDER BY count DESC
            """)
            return {row["error_category"]: row["count"] for row in cursor.fetchall()}

    def get_top_repeated_errors(self, limit: int = 3) -> list[dict]:
        """Get top repeated error patterns."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT error_category, instrument, COUNT(*) as count,
                       GROUP_CONCAT(lessons, ' | ') as all_lessons
                FROM errors
                GROUP BY error_category, instrument
                ORDER BY count DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # ===================
    # Statistics
    # ===================

    def get_performance_stats(self, days: int = 30) -> dict:
        """
        Get trading performance statistics.

        Args:
            days: Number of days to include

        Returns:
            Performance stats dict
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            # Total trades
            cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'CLOSED'")
            total_trades = cursor.fetchone()[0]

            # Winning trades
            cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'CLOSED' AND pnl > 0")
            winning_trades = cursor.fetchone()[0]

            # Total P/L
            cursor.execute("SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE status = 'CLOSED'")
            total_pnl = cursor.fetchone()[0]

            # Average win/loss
            cursor.execute("SELECT COALESCE(AVG(pnl), 0) FROM trades WHERE status = 'CLOSED' AND pnl > 0")
            avg_win = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(AVG(pnl), 0) FROM trades WHERE status = 'CLOSED' AND pnl < 0")
            avg_loss = cursor.fetchone()[0]

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": total_trades - winning_trades,
                "win_rate": round(win_rate, 1),
                "total_pnl": round(total_pnl, 2),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0
            }


# Singleton database instance
db = Database()
