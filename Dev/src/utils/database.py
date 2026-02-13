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
from datetime import datetime, timedelta
from typing import Optional
from contextlib import contextmanager

from src.utils.logger import logger


# Database path
_dev_dir = Path(__file__).parent.parent.parent
_db_path = _dev_dir / "data" / "trades.db"


def _to_int_or_none(value):
    if value is None:
        return None
    return 1 if bool(value) else 0


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

            # LLM decisions table (advisory + approval log)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    recommendation TEXT,
                    direction TEXT,
                    confidence_adjustment INTEGER,
                    summary TEXT,
                    risk_notes TEXT,
                    strategy_notes TEXT,
                    approved INTEGER DEFAULT 0,
                    executed INTEGER DEFAULT 0,
                    trade_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Execution quality logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    trade_id TEXT,
                    order_id TEXT,
                    instrument TEXT NOT NULL,
                    side TEXT,
                    requested_price REAL,
                    fill_price REAL,
                    slippage_pips REAL,
                    spread_pips REAL,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Auto-trading scanner statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scanner_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    instruments_scanned INTEGER,
                    signals_found INTEGER,
                    signals_executed INTEGER,
                    scan_duration_ms INTEGER,
                    mode TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Auto-trading cooldown log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cooldown_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    reason TEXT,
                    loss_streak INTEGER,
                    pnl_at_start REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Auto-trading signal log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auto_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    direction TEXT,
                    confidence INTEGER,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    risk_reward REAL,
                    executed INTEGER DEFAULT 0,
                    skip_reason TEXT,
                    trade_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # SMC v2 setup labels (shadow/live evaluation telemetry)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS setup_labels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    direction TEXT,
                    setup_grade TEXT,
                    confidence INTEGER,
                    risk_reward REAL,
                    allow_trade INTEGER DEFAULT 0,
                    within_killzone INTEGER,
                    news_clear INTEGER,
                    htf_poi_gate INTEGER,
                    sweep_valid INTEGER,
                    fvg_valid INTEGER,
                    direction_confirmed INTEGER,
                    choch_or_bos INTEGER,
                    rr_pass INTEGER,
                    sl_cap_pass INTEGER,
                    reason TEXT,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Add trade_source column to trades if not exists
            try:
                cursor.execute("ALTER TABLE trades ADD COLUMN trade_source TEXT DEFAULT 'MANUAL'")
            except sqlite3.OperationalError:
                pass  # Column already exists
            try:
                cursor.execute("ALTER TABLE setup_labels ADD COLUMN fvg_valid INTEGER")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # AI Activity Log - centralized logging of all AI decisions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    instrument TEXT,
                    direction TEXT,

                    -- Analysis scores
                    technical_score INTEGER,
                    sentiment_score REAL,
                    adversarial_score REAL,
                    confidence INTEGER,

                    -- Decision
                    decision TEXT,
                    reasoning TEXT,

                    -- Additional context
                    details TEXT,
                    duration_ms INTEGER,

                    -- Reference
                    signal_id INTEGER,
                    trade_id TEXT,

                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # AI Override Log - tracks override decisions and outcomes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS override_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    instrument TEXT NOT NULL,
                    direction TEXT,

                    -- Original rejection
                    original_skip_reason TEXT,
                    original_confidence INTEGER,

                    -- AI Override decision
                    override_recommended INTEGER DEFAULT 0,
                    ai_confidence INTEGER,
                    ai_reasoning TEXT,
                    suggested_adjustment TEXT,

                    -- What was applied
                    adjustment_applied TEXT,
                    adjustment_value TEXT,

                    -- Result (populated later)
                    trade_executed INTEGER DEFAULT 0,
                    trade_id TEXT,
                    trade_outcome TEXT,
                    pnl REAL,

                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Market Regimes table - tracks regime history per instrument (Phase 1 Enhancement)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_regimes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    instrument TEXT NOT NULL,
                    timeframe TEXT NOT NULL,

                    -- Regime classification
                    regime TEXT NOT NULL,
                    regime_strength INTEGER,

                    -- Underlying indicators
                    adx REAL,
                    bollinger_width REAL,
                    bollinger_width_percentile REAL,
                    atr_pips REAL,
                    trend TEXT,
                    trend_strength REAL,

                    -- For learning
                    trade_taken INTEGER DEFAULT 0,
                    trade_id TEXT,
                    trade_outcome TEXT,
                    pnl REAL,

                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ===================
            # Self-Upgrade System Tables
            # ===================

            # AI-generated proposals
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS upgrade_proposals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    proposal_type TEXT,
                    proposal_name TEXT,
                    trigger_reason TEXT,
                    generated_code TEXT,
                    ast_valid INTEGER DEFAULT 0,
                    backtest_result TEXT,
                    robustness_score REAL DEFAULT 0.0,
                    deployed INTEGER DEFAULT 0,
                    rolled_back INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Deployed filters
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deployed_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filter_name TEXT UNIQUE,
                    filter_type TEXT,
                    enabled INTEGER DEFAULT 1,
                    signals_blocked INTEGER DEFAULT 0,
                    estimated_pnl_impact REAL DEFAULT 0.0,
                    rolled_back INTEGER DEFAULT 0,
                    deployed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Upgrade audit log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS upgrade_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    action TEXT,
                    proposal_id TEXT,
                    success INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # SMC Analysis log - tracks Smart Money Concepts decisions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS smc_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    instrument TEXT NOT NULL,
                    htf_bias TEXT,
                    htf_structure TEXT,
                    sweep_detected INTEGER DEFAULT 0,
                    sweep_details TEXT,
                    choch_detected INTEGER DEFAULT 0,
                    bos_detected INTEGER DEFAULT 0,
                    fvg_count INTEGER DEFAULT 0,
                    ob_count INTEGER DEFAULT 0,
                    premium_discount TEXT,
                    setup_grade TEXT,
                    direction TEXT,
                    entry_zone TEXT,
                    stop_loss REAL,
                    take_profit REAL,
                    confidence INTEGER,
                    executed INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ===================
            # ISI (Institutional Sequence Intelligence) Tables
            # ===================

            # Confidence calibration parameters (Platt Scaling)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calibration_params (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    param_a REAL,
                    param_b REAL,
                    training_trades INTEGER,
                    training_win_rate REAL,
                    brier_score REAL,
                    active INTEGER DEFAULT 1
                )
            """)

            # Sequence tracker states (institutional cycle per instrument)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sequence_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    instrument TEXT,
                    current_phase INTEGER,
                    phase_name TEXT,
                    phase_confidence REAL,
                    phase_entered_at TEXT,
                    accumulation_range_high REAL,
                    accumulation_range_low REAL,
                    sweep_level REAL,
                    sweep_direction TEXT,
                    displacement_magnitude REAL,
                    expected_target REAL,
                    active INTEGER DEFAULT 1
                )
            """)

            # Sequence phase transitions log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sequence_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    instrument TEXT,
                    old_phase INTEGER,
                    new_phase INTEGER,
                    old_phase_name TEXT,
                    new_phase_name TEXT,
                    reason TEXT,
                    smc_grade TEXT,
                    trade_taken INTEGER DEFAULT 0,
                    trade_id TEXT,
                    trade_outcome TEXT,
                    pnl REAL
                )
            """)

            # Sequence completions (full cycle tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sequence_completions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instrument TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    phases_completed INTEGER,
                    max_phase_reached INTEGER,
                    total_duration_minutes INTEGER,
                    was_traded INTEGER DEFAULT 0,
                    trade_id TEXT,
                    trade_pnl REAL
                )
            """)

            # Cross-asset correlation snapshots
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS correlation_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    pair1 TEXT,
                    pair2 TEXT,
                    correlation_30bar REAL,
                    expected_correlation REAL,
                    divergence_sigma REAL,
                    implication TEXT
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_instrument ON trades(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_source ON trades(trade_source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_instrument ON errors(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_category ON errors(error_category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_instrument ON llm_decisions(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_time ON llm_decisions(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_instrument ON execution_logs(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_time ON execution_logs(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scanner_time ON scanner_stats(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_time ON auto_signals(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_instrument ON auto_signals(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_setup_labels_time ON setup_labels(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_setup_labels_instrument ON setup_labels(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_setup_labels_grade ON setup_labels(setup_grade)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_log(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_type ON activity_log(activity_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_instrument ON activity_log(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_override_time ON override_log(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_override_instrument ON override_log(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_regime_time ON market_regimes(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_regime_instrument ON market_regimes(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_regime_type ON market_regimes(regime)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_proposals_time ON upgrade_proposals(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_proposals_deployed ON upgrade_proposals(deployed)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_filters_name ON deployed_filters(filter_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON upgrade_audit_log(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON upgrade_audit_log(action)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_smc_time ON smc_analysis(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_smc_instrument ON smc_analysis(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_smc_grade ON smc_analysis(setup_grade)")

            # ISI indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_calibration_active ON calibration_params(active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_seq_states_instrument ON sequence_states(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_seq_states_active ON sequence_states(active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_seq_transitions_instrument ON sequence_transitions(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_seq_transitions_time ON sequence_transitions(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_seq_completions_instrument ON sequence_completions(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_corr_snapshots_time ON correlation_snapshots(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_corr_snapshots_pairs ON correlation_snapshots(pair1, pair2)")

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

    def update_trade_source(self, trade_id: str, source: str) -> bool:
        """Update the trade_source field for an existing trade."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE trades SET trade_source = ? WHERE trade_id = ?",
                (source, trade_id)
            )
            return cursor.rowcount > 0

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

    def get_daily_pnl(self, auto_only: bool = False) -> float:
        """
        Get realized P/L for today.

        Args:
            auto_only: If True, include only AUTO_* trade sources.
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            base_sql = """
                SELECT COALESCE(SUM(pnl), 0)
                FROM trades
                WHERE status = 'CLOSED'
                  AND pnl IS NOT NULL
                  AND close_reason != 'SYNC_CLOSED_PENDING_RECON'
                  AND DATE(REPLACE(SUBSTR(COALESCE(closed_at, timestamp), 1, 19), 'T', ' ')) = DATE('now', 'localtime')
            """
            if auto_only:
                base_sql += " AND COALESCE(trade_source, 'MANUAL') LIKE 'AUTO_%'"
            cursor.execute(base_sql)
            result = cursor.fetchone()
            return float(result[0]) if result else 0.0

    def get_weekly_pnl(self, auto_only: bool = False) -> float:
        """
        Get realized P/L for current week (Monday local time -> now).

        Args:
            auto_only: If True, include only AUTO_* trade sources.
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            base_sql = """
                SELECT COALESCE(SUM(pnl), 0)
                FROM trades
                WHERE status = 'CLOSED'
                  AND pnl IS NOT NULL
                  AND close_reason != 'SYNC_CLOSED_PENDING_RECON'
                  AND DATE(REPLACE(SUBSTR(COALESCE(closed_at, timestamp), 1, 19), 'T', ' ')) >= DATE('now', 'localtime', 'weekday 1', '-7 days')
            """
            if auto_only:
                base_sql += " AND COALESCE(trade_source, 'MANUAL') LIKE 'AUTO_%'"
            cursor.execute(base_sql)
            result = cursor.fetchone()
            return float(result[0]) if result else 0.0

    def get_pending_recon_count(self, days: int = 7) -> int:
        """Count closed trades waiting for MT5 reconciliation (no confirmed P/L yet)."""
        cutoff = datetime.now() - timedelta(days=days)
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM trades
                WHERE status = 'CLOSED'
                  AND pnl IS NULL
                  AND close_reason = 'SYNC_CLOSED_PENDING_RECON'
                  AND COALESCE(closed_at, timestamp) >= ?
                """,
                (cutoff.isoformat(),),
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0

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
    # LLM Decisions
    # ===================

    def log_llm_decision(self, data: dict) -> int:
        """Log an LLM decision for audit trail."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO llm_decisions (
                    timestamp, instrument, recommendation, direction,
                    confidence_adjustment, summary, risk_notes, strategy_notes,
                    approved, executed, trade_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", datetime.now().isoformat()),
                data.get("instrument"),
                data.get("recommendation"),
                data.get("direction"),
                data.get("confidence_adjustment"),
                data.get("summary"),
                json.dumps(data.get("risk_notes", [])),
                json.dumps(data.get("strategy_notes", [])),
                int(data.get("approved", 0)),
                int(data.get("executed", 0)),
                data.get("trade_id")
            ))
            return cursor.lastrowid

    def update_llm_decision(self, decision_id: int, **updates) -> bool:
        """Update an LLM decision (approved/executed/trade_id)."""
        if not updates:
            return False

        fields = []
        values = []
        for k, v in updates.items():
            fields.append(f"{k} = ?")
            values.append(v)

        values.append(decision_id)

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE llm_decisions SET {', '.join(fields)} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0

    def get_recent_llm_decisions(self, limit: int = 20) -> list[dict]:
        """Get recent LLM decisions."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM llm_decisions ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item["risk_notes"] = json.loads(item.get("risk_notes", "[]"))
                item["strategy_notes"] = json.loads(item.get("strategy_notes", "[]"))
                results.append(item)
            return results

    def log_execution(self, data: dict) -> int:
        """Log execution quality for an order."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO execution_logs (
                    timestamp, trade_id, order_id, instrument, side,
                    requested_price, fill_price, slippage_pips, spread_pips, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", datetime.now().isoformat()),
                data.get("trade_id"),
                data.get("order_id"),
                data.get("instrument"),
                data.get("side"),
                data.get("requested_price"),
                data.get("fill_price"),
                data.get("slippage_pips"),
                data.get("spread_pips"),
                data.get("notes")
            ))
            return cursor.lastrowid

    # ===================
    # MT5 Sync
    # ===================

    def sync_from_mt5(self, mt5_trades: list[dict]) -> dict:
        """
        Sync closed trades from MT5 history into database.

        This method imports trades that were executed directly in MT5
        (not through the AI Trader system) so they appear in the dashboard.

        Args:
            mt5_trades: List of trade dicts from MT5Client.get_history()

        Returns:
            Dict with sync results:
            - total: Total trades in MT5 history
            - imported: Number of new trades imported
            - skipped: Number of trades already in DB
            - errors: Number of import errors
            - trades_imported: List of imported trade_ids
        """
        results = {
            "total": len(mt5_trades),
            "imported": 0,
            "skipped": 0,
            "errors": 0,
            "trades_imported": []
        }

        for trade in mt5_trades:
            trade_id = trade.get("trade_id")

            # Check if trade already exists
            existing = self.get_trade(trade_id)
            if existing:
                # If trade exists but is still OPEN in DB, update it with MT5 close data.
                if str(existing.get("status", "")).upper() == "OPEN":
                    try:
                        with self._connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE trades SET
                                    status = 'CLOSED',
                                    exit_price = ?,
                                    pnl = ?,
                                    pnl_percent = ?,
                                    closed_at = ?,
                                    close_reason = COALESCE(close_reason, 'MT5_SYNC')
                                WHERE trade_id = ? AND status = 'OPEN'
                            """, (
                                trade.get("exit_price"),
                                trade.get("pnl"),
                                trade.get("pnl_percent"),
                                trade.get("closed_at"),
                                trade_id,
                            ))
                        results["imported"] += 1
                        results["trades_imported"].append(trade_id)
                        logger.info(
                            f"Synced close for existing OPEN trade {trade_id}: "
                            f"{trade.get('instrument')} {trade.get('direction')} P/L: {trade.get('pnl')}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to sync-close existing trade {trade_id}: {e}")
                        results["errors"] += 1
                elif (
                    str(existing.get("status", "")).upper() == "CLOSED"
                    and str(existing.get("close_reason", "")).upper() in {
                        "SYNC_CLOSED_NO_PNL",
                        "SYNC_CLOSED_ESTIMATED_SL",
                        "SYNC_CLOSED_PENDING_RECON",
                    }
                    and trade.get("closed_at")
                ):
                    # Reconcile previously closed-without-PnL rows once MT5 history appears.
                    try:
                        with self._connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE trades SET
                                    exit_price = ?,
                                    pnl = ?,
                                    pnl_percent = ?,
                                    closed_at = ?,
                                    close_reason = 'MT5_SYNC_RECON'
                                WHERE trade_id = ? AND status = 'CLOSED'
                            """, (
                                trade.get("exit_price"),
                                trade.get("pnl"),
                                trade.get("pnl_percent"),
                                trade.get("closed_at"),
                                trade_id,
                            ))
                        results["imported"] += 1
                        results["trades_imported"].append(trade_id)
                        logger.info(
                            f"Reconciled previously pending closed trade {trade_id} with MT5 P/L: {trade.get('pnl')}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to reconcile pending trade {trade_id}: {e}")
                        results["errors"] += 1
                else:
                    results["skipped"] += 1
                continue

            # Fallback match when MT5 history uses a different identifier than local trade_id.
            # Reconcile pending/no-PnL rows by instrument+direction+time proximity.
            try:
                with self._connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT
                            trade_id,
                            ABS(strftime('%s', COALESCE(closed_at, timestamp)) - strftime('%s', ?)) AS delta_sec
                        FROM trades
                        WHERE status = 'CLOSED'
                          AND pnl IS NULL
                          AND instrument = ?
                          AND direction = ?
                          AND close_reason IN ('SYNC_CLOSED_NO_PNL', 'SYNC_CLOSED_ESTIMATED_SL', 'SYNC_CLOSED_PENDING_RECON')
                        ORDER BY delta_sec ASC
                        LIMIT 1
                        """,
                        (
                            trade.get("closed_at") or trade.get("opened_at") or datetime.now().isoformat(),
                            trade.get("instrument"),
                            trade.get("direction"),
                        ),
                    )
                    pending_match = cursor.fetchone()
                    if pending_match and int(pending_match[1] or 10**9) <= 12 * 3600:
                        matched_trade_id = pending_match[0]
                        cursor.execute(
                            """
                            UPDATE trades SET
                                exit_price = ?,
                                pnl = ?,
                                pnl_percent = ?,
                                closed_at = ?,
                                close_reason = 'MT5_SYNC_RECON',
                                notes = COALESCE(notes, '') || ?
                            WHERE trade_id = ? AND status = 'CLOSED'
                            """,
                            (
                                trade.get("exit_price"),
                                trade.get("pnl"),
                                trade.get("pnl_percent"),
                                trade.get("closed_at"),
                                f" | mt5_trade_id={trade_id}",
                                matched_trade_id,
                            ),
                        )
                        if cursor.rowcount > 0:
                            results["imported"] += 1
                            results["trades_imported"].append(matched_trade_id)
                            logger.info(
                                f"Reconciled pending trade {matched_trade_id} "
                                f"using MT5 trade {trade_id}: P/L {trade.get('pnl')}"
                            )
                            continue
            except Exception as e:
                logger.warning(f"Pending fallback reconciliation failed for MT5 trade {trade_id}: {e}")

            try:
                with self._connection() as conn:
                    cursor = conn.cursor()

                    # Insert as closed trade
                    cursor.execute("""
                        INSERT INTO trades (
                            trade_id, timestamp, instrument, direction,
                            entry_price, exit_price, stop_loss, take_profit,
                            units, pnl, pnl_percent, status, closed_at,
                            close_reason, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade_id,
                        trade.get("opened_at"),
                        trade.get("instrument"),
                        trade.get("direction"),
                        trade.get("entry_price"),
                        trade.get("exit_price"),
                        trade.get("stop_loss"),
                        trade.get("take_profit"),
                        trade.get("units"),
                        trade.get("pnl"),
                        trade.get("pnl_percent"),
                        "CLOSED",
                        trade.get("closed_at"),
                        "MT5_SYNC",
                        f"Synced from MT5. Commission: {trade.get('commission', 0)}, Swap: {trade.get('swap', 0)}"
                    ))

                results["imported"] += 1
                results["trades_imported"].append(trade_id)
                logger.info(f"Synced trade {trade_id}: {trade.get('instrument')} {trade.get('direction')} P/L: {trade.get('pnl')}")

            except Exception as e:
                logger.error(f"Failed to sync trade {trade_id}: {e}")
                results["errors"] += 1

        logger.info(f"MT5 sync complete: {results['imported']} imported, {results['skipped']} skipped, {results['errors']} errors")
        return results

    def get_existing_trade_ids(self) -> set[str]:
        """Get set of all trade_ids in database."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT trade_id FROM trades")
            return {row[0] for row in cursor.fetchall()}

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

    def get_recent_trades(self, days: int = 30) -> list[dict]:
        """Get closed trades in last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM trades WHERE status = 'CLOSED' AND closed_at >= ? ORDER BY closed_at ASC",
                (cutoff.isoformat(),)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_drawdown_stats(self, days: int = 30) -> dict:
        """Approximate drawdown from closed trades over last N days."""
        trades = self.get_recent_trades(days)
        if not trades:
            return {"max_drawdown_pct": 0.0, "max_drawdown_abs": 0.0, "net_pnl": 0.0}

        equity = 0.0
        peak = 0.0
        max_dd_abs = 0.0
        max_dd_pct = 0.0

        for t in trades:
            equity += t.get("pnl", 0) or 0
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd_abs:
                max_dd_abs = dd
                max_dd_pct = (dd / peak * 100) if peak > 0 else 0.0

        return {
            "max_drawdown_pct": round(max_dd_pct, 2),
            "max_drawdown_abs": round(max_dd_abs, 2),
            "net_pnl": round(equity, 2)
        }

    # ===================
    # Auto-Trading Operations
    # ===================

    def log_scanner_stats(self, data: dict) -> int:
        """Log scanner statistics."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scanner_stats (
                    timestamp, instruments_scanned, signals_found,
                    signals_executed, scan_duration_ms, mode
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", datetime.now().isoformat()),
                data.get("instruments_scanned", 0),
                data.get("signals_found", 0),
                data.get("signals_executed", 0),
                data.get("scan_duration_ms", 0),
                data.get("mode", "scalping")
            ))
            return cursor.lastrowid

    def log_auto_signal(self, data: dict) -> int:
        """Log an auto-trading signal."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO auto_signals (
                    timestamp, instrument, direction, confidence,
                    entry_price, stop_loss, take_profit, risk_reward,
                    executed, skip_reason, trade_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", datetime.now().isoformat()),
                data.get("instrument"),
                data.get("direction"),
                data.get("confidence"),
                data.get("entry_price"),
                data.get("stop_loss"),
                data.get("take_profit"),
                data.get("risk_reward"),
                int(data.get("executed", 0)),
                data.get("skip_reason"),
                data.get("trade_id")
            ))
            return cursor.lastrowid

    def log_setup_label(self, data: dict) -> int:
        """Log SMC v2 setup evaluation label (used for shadow training/analysis)."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO setup_labels (
                    timestamp, instrument, direction, setup_grade, confidence, risk_reward,
                    allow_trade, within_killzone, news_clear, htf_poi_gate, sweep_valid, fvg_valid,
                    direction_confirmed, choch_or_bos, rr_pass, sl_cap_pass, reason, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", datetime.now().isoformat()),
                data.get("instrument"),
                data.get("direction"),
                data.get("setup_grade"),
                data.get("confidence"),
                data.get("risk_reward"),
                int(bool(data.get("allow_trade", False))),
                _to_int_or_none(data.get("within_killzone")),
                _to_int_or_none(data.get("news_clear")),
                _to_int_or_none(data.get("htf_poi_gate")),
                _to_int_or_none(data.get("sweep_valid")),
                _to_int_or_none(data.get("fvg_valid")),
                _to_int_or_none(data.get("direction_confirmed")),
                _to_int_or_none(data.get("choch_or_bos")),
                _to_int_or_none(data.get("rr_pass")),
                _to_int_or_none(data.get("sl_cap_pass")),
                data.get("reason"),
                json.dumps(data.get("details", {}))
            ))
            return cursor.lastrowid

    def update_auto_signal_result(
        self,
        instrument: str,
        direction: str,
        executed: bool,
        skip_reason: str = None,
        trade_id: str = None
    ) -> bool:
        """Update the most recent auto_signal with execution result."""
        with self._connection() as conn:
            cursor = conn.cursor()
            # Update the most recent signal for this instrument/direction
            cursor.execute("""
                UPDATE auto_signals SET
                    executed = ?,
                    skip_reason = ?,
                    trade_id = ?
                WHERE id = (
                    SELECT id FROM auto_signals
                    WHERE instrument = ? AND direction = ?
                    ORDER BY id DESC LIMIT 1
                )
            """, (
                1 if executed else 0,
                skip_reason,
                trade_id,
                instrument,
                direction
            ))
            return cursor.rowcount > 0

    def log_cooldown(self, data: dict) -> int:
        """Log a cooldown event."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cooldown_log (
                    started_at, ended_at, reason, loss_streak, pnl_at_start
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                data.get("started_at", datetime.now().isoformat()),
                data.get("ended_at"),
                data.get("reason"),
                data.get("loss_streak"),
                data.get("pnl_at_start")
            ))
            return cursor.lastrowid

    def get_auto_trading_stats(self, days: int = 7) -> dict:
        """Get auto-trading statistics for last N days."""
        cutoff = datetime.now() - timedelta(days=days)

        with self._connection() as conn:
            cursor = conn.cursor()

            # Total auto trades
            cursor.execute("""
                SELECT COUNT(*) FROM trades
                WHERE trade_source IN ('AUTO_SCALPING', 'AUTO_SCALPING_LIMIT')
                AND timestamp >= ?
            """, (cutoff.isoformat(),))
            total_auto_trades = cursor.fetchone()[0]

            # Auto trades P/L
            cursor.execute("""
                SELECT COALESCE(SUM(pnl), 0) FROM trades
                WHERE trade_source IN ('AUTO_SCALPING', 'AUTO_SCALPING_LIMIT')
                AND status = 'CLOSED'
                AND closed_at >= ?
            """, (cutoff.isoformat(),))
            auto_pnl = cursor.fetchone()[0]

            # Signals generated
            cursor.execute("""
                SELECT COUNT(*) FROM auto_signals
                WHERE timestamp >= ?
            """, (cutoff.isoformat(),))
            total_signals = cursor.fetchone()[0]

            # Signals executed
            cursor.execute("""
                SELECT COUNT(*) FROM auto_signals
                WHERE executed = 1 AND timestamp >= ?
            """, (cutoff.isoformat(),))
            executed_signals = cursor.fetchone()[0]

            # Scanner stats
            cursor.execute("""
                SELECT COUNT(*), COALESCE(AVG(scan_duration_ms), 0)
                FROM scanner_stats
                WHERE timestamp >= ?
            """, (cutoff.isoformat(),))
            row = cursor.fetchone()
            total_scans = row[0]
            avg_scan_duration = row[1]
            if total_scans == 0:
                # Fallback for environments where scanner_stats wasn't historically persisted.
                cursor.execute("""
                    SELECT COUNT(*), COALESCE(AVG(duration_ms), 0)
                    FROM activity_log
                    WHERE activity_type = 'SCAN_COMPLETE'
                    AND timestamp >= ?
                """, (cutoff.isoformat(),))
                fallback_row = cursor.fetchone()
                total_scans = fallback_row[0]
                avg_scan_duration = fallback_row[1]

            # Cooldowns
            cursor.execute("""
                SELECT COUNT(*) FROM cooldown_log
                WHERE started_at >= ?
            """, (cutoff.isoformat(),))
            cooldowns = cursor.fetchone()[0]

            return {
                "total_auto_trades": total_auto_trades,
                "auto_pnl": round(auto_pnl, 2),
                "total_signals": total_signals,
                "executed_signals": executed_signals,
                "execution_rate": round(executed_signals / total_signals * 100, 1) if total_signals > 0 else 0,
                "total_scans": total_scans,
                "avg_scan_duration_ms": round(avg_scan_duration, 1),
                "cooldowns_triggered": cooldowns
            }

    def get_recent_auto_signals(self, limit: int = 50) -> list[dict]:
        """Get recent auto-trading signals."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM auto_signals
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_smc_v2_shadow_stats(self, hours: int = 24) -> dict:
        """Get SMC v2 shadow evaluation stats for the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN allow_trade = 1 THEN 1 ELSE 0 END) as allow_count,
                    SUM(CASE WHEN allow_trade = 0 THEN 1 ELSE 0 END) as block_count
                FROM setup_labels
                WHERE timestamp >= ?
            """, (cutoff.isoformat(),))
            row = cursor.fetchone()
            total = row["total"] or 0
            allow_count = row["allow_count"] or 0
            block_count = row["block_count"] or 0

            cursor.execute("""
                SELECT setup_grade, COUNT(*) as cnt
                FROM setup_labels
                WHERE timestamp >= ?
                GROUP BY setup_grade
                ORDER BY cnt DESC
            """, (cutoff.isoformat(),))
            grades = {r["setup_grade"] or "UNKNOWN": r["cnt"] for r in cursor.fetchall()}

            cursor.execute("""
                SELECT reason, COUNT(*) as cnt
                FROM setup_labels
                WHERE timestamp >= ? AND allow_trade = 0
                GROUP BY reason
                ORDER BY cnt DESC
                LIMIT 5
            """, (cutoff.isoformat(),))
            top_block_reasons = [{"reason": r["reason"], "count": r["cnt"]} for r in cursor.fetchall()]

            return {
                "total": total,
                "allow_count": allow_count,
                "block_count": block_count,
                "allow_rate": round((allow_count / total) * 100, 1) if total > 0 else 0.0,
                "block_rate": round((block_count / total) * 100, 1) if total > 0 else 0.0,
                "by_grade": grades,
                "top_block_reasons": top_block_reasons,
            }

    def get_recent_setup_labels(self, limit: int = 50) -> list[dict]:
        """Get recent SMC v2 setup labels with parsed details."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM setup_labels
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("details"):
                    try:
                        item["details"] = json.loads(item["details"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                rows.append(item)
            return rows

    def get_smc_v2_gate_stats(self, hours: int = 24) -> dict:
        """Get per-gate pass/fail rates for setup_labels."""
        cutoff = datetime.now() - timedelta(hours=hours)
        gates = [
            "within_killzone",
            "news_clear",
            "htf_poi_gate",
            "sweep_valid",
            "fvg_valid",
            "direction_confirmed",
            "choch_or_bos",
            "rr_pass",
            "sl_cap_pass",
        ]
        results = {
            g: {"pass_count": 0, "fail_count": 0, "total": 0, "pass_rate": 0.0}
            for g in gates
        }
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM setup_labels
                WHERE timestamp >= ?
            """, (cutoff.isoformat(),))
            rows = cursor.fetchall()

            def _coerce_bool_int(v):
                if v is None:
                    return None
                if isinstance(v, bool):
                    return 1 if v else 0
                if isinstance(v, (int, float)):
                    return 1 if int(v) != 0 else 0
                if isinstance(v, str):
                    s = v.strip().lower()
                    if s in ("1", "true", "yes"):
                        return 1
                    if s in ("0", "false", "no"):
                        return 0
                return None

            for row in rows:
                item = dict(row)
                details = {}
                if item.get("details"):
                    try:
                        details = json.loads(item["details"]) or {}
                    except (json.JSONDecodeError, TypeError):
                        details = {}

                # Backfill gates from payload details when gate columns were null.
                direct_gates = details.get("gates") if isinstance(details, dict) else {}
                raw_details = details.get("raw_details") if isinstance(details, dict) else {}
                nested_gates = {}
                if isinstance(raw_details, dict):
                    rg = raw_details.get("gates")
                    if isinstance(rg, dict):
                        nested_gates = rg

                for gate in gates:
                    gate_value = _coerce_bool_int(item.get(gate))
                    if gate_value is None:
                        gate_value = _coerce_bool_int(direct_gates.get(gate) if isinstance(direct_gates, dict) else None)
                    if gate_value is None:
                        gate_value = _coerce_bool_int(nested_gates.get(gate) if isinstance(nested_gates, dict) else None)
                    if gate_value is None:
                        continue
                    results[gate]["total"] += 1
                    if gate_value == 1:
                        results[gate]["pass_count"] += 1
                    else:
                        results[gate]["fail_count"] += 1

            for gate in gates:
                total = results[gate]["total"]
                pass_count = results[gate]["pass_count"]
                results[gate]["pass_rate"] = round((pass_count / total) * 100, 1) if total > 0 else 0.0
        return results

    def get_smc_v2_by_instrument(self, hours: int = 24) -> list[dict]:
        """Get SMC v2 shadow stats grouped by instrument."""
        cutoff = datetime.now() - timedelta(hours=hours)
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    instrument,
                    COUNT(*) as total,
                    SUM(CASE WHEN allow_trade = 1 THEN 1 ELSE 0 END) as allow_count,
                    SUM(CASE WHEN allow_trade = 0 THEN 1 ELSE 0 END) as block_count
                FROM setup_labels
                WHERE timestamp >= ?
                GROUP BY instrument
                ORDER BY total DESC
            """, (cutoff.isoformat(),))
            rows = []
            for row in cursor.fetchall():
                total = row["total"] or 0
                allow_count = row["allow_count"] or 0
                block_count = row["block_count"] or 0
                rows.append({
                    "instrument": row["instrument"],
                    "total": total,
                    "allow_count": allow_count,
                    "block_count": block_count,
                    "allow_rate": round((allow_count / total) * 100, 1) if total > 0 else 0.0,
                    "block_rate": round((block_count / total) * 100, 1) if total > 0 else 0.0,
                })
            return rows

    def get_auto_trades_by_instrument(self, days: int = 7) -> dict:
        """Get auto trades grouped by instrument."""
        cutoff = datetime.now() - timedelta(days=days)

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT instrument, COUNT(*) as count, COALESCE(SUM(pnl), 0) as pnl
                FROM trades
                WHERE trade_source IN ('AUTO_SCALPING', 'AUTO_SCALPING_LIMIT')
                AND timestamp >= ?
                GROUP BY instrument
                ORDER BY count DESC
            """, (cutoff.isoformat(),))
            return {row["instrument"]: {"count": row["count"], "pnl": row["pnl"]}
                    for row in cursor.fetchall()}

    # ===================
    # AI Activity Log
    # ===================

    def log_activity(self, data: dict) -> int:
        """
        Log an AI activity event.

        Activity types:
        - SCAN_START: Scanner starting a scan cycle
        - SCAN_COMPLETE: Scanner finished scanning all instruments
        - ANALYZING: Analyzing a specific instrument
        - SIGNAL_GENERATED: Signal met confidence threshold
        - SIGNAL_REJECTED: Signal below threshold, with reason
        - TRADE_EXECUTED: Trade was executed
        - TRADE_SKIPPED: Trade skipped (cooldown, limits, etc.)
        - COOLDOWN_START: Entered cooldown period
        - COOLDOWN_END: Exited cooldown period
        - EMERGENCY_STOP: Emergency stop triggered
        - ERROR: An error occurred

        Args:
            data: Activity details dict

        Returns:
            Activity row ID
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            # Serialize details to JSON if dict
            details = data.get("details")
            if isinstance(details, dict):
                details = json.dumps(details)

            cursor.execute("""
                INSERT INTO activity_log (
                    timestamp, activity_type, instrument, direction,
                    technical_score, sentiment_score, adversarial_score, confidence,
                    decision, reasoning, details, duration_ms,
                    signal_id, trade_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", datetime.now().isoformat()),
                data.get("activity_type"),
                data.get("instrument"),
                data.get("direction"),
                data.get("technical_score"),
                data.get("sentiment_score"),
                data.get("adversarial_score"),
                data.get("confidence"),
                data.get("decision"),
                data.get("reasoning"),
                details,
                data.get("duration_ms"),
                data.get("signal_id"),
                data.get("trade_id")
            ))

            return cursor.lastrowid

    def get_recent_activities(self, limit: int = 100, activity_types: list = None) -> list[dict]:
        """
        Get recent AI activities.

        Args:
            limit: Max number of activities
            activity_types: Filter by types (optional)

        Returns:
            List of activity dicts
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            if activity_types:
                placeholders = ",".join("?" * len(activity_types))
                cursor.execute(f"""
                    SELECT * FROM activity_log
                    WHERE activity_type IN ({placeholders})
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (*activity_types, limit))
            else:
                cursor.execute("""
                    SELECT * FROM activity_log
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

            results = []
            for row in cursor.fetchall():
                item = dict(row)
                # Parse JSON details if present
                if item.get("details"):
                    try:
                        item["details"] = json.loads(item["details"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                results.append(item)
            return results

    def get_activities_for_instrument(self, instrument: str, limit: int = 50) -> list[dict]:
        """Get recent activities for a specific instrument."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM activity_log
                WHERE instrument = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (instrument, limit))

            results = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("details"):
                    try:
                        item["details"] = json.loads(item["details"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                results.append(item)
            return results

    def get_activity_stats(self, hours: int = 24) -> dict:
        """
        Get activity statistics for the last N hours.

        Returns:
            Dict with counts by activity type
        """
        cutoff = datetime.now() - timedelta(hours=hours)

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT activity_type, COUNT(*) as count
                FROM activity_log
                WHERE timestamp >= ?
                GROUP BY activity_type
            """, (cutoff.isoformat(),))

            stats = {row["activity_type"]: row["count"] for row in cursor.fetchall()}

            # Add summary
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT instrument) as instruments_analyzed
                FROM activity_log
                WHERE timestamp >= ?
            """, (cutoff.isoformat(),))
            row = cursor.fetchone()
            stats["total_activities"] = row["total"]
            stats["instruments_analyzed"] = row["instruments_analyzed"]

            return stats

    def clear_old_activities(self, days: int = 7) -> int:
        """
        Clear activities older than N days.

        Returns:
            Number of rows deleted
        """
        cutoff = datetime.now() - timedelta(days=days)
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM activity_log WHERE timestamp < ?",
                (cutoff.isoformat(),)
            )
            return cursor.rowcount

    def sync_trades_with_mt5(
        self,
        mt5_positions: list[dict],
        mt5_history: list[dict] = None,
        mt5_client=None,
    ) -> dict:
        """
        Sync stale OPEN trades in DB with actual MT5 positions.

        If a trade is OPEN in DB but not in MT5 positions, it was likely
        closed externally (manually or by SL/TP). Mark it as SYNC_CLOSED
        and fetch the actual P/L from MT5 history.

        Args:
            mt5_positions: List of current MT5 position dicts with 'trade_id' or 'ticket'
            mt5_history: Optional list of closed trades from MT5 history (for P/L lookup)

        Returns:
            Dict with sync results:
            - checked: Number of DB open trades checked
            - closed: List of trade_ids that were sync-closed
            - closed_with_pnl: Number of trades closed with actual P/L data
            - still_open: Number still matching MT5
        """
        results = {
            "checked": 0,
            "closed": [],
            "closed_with_pnl": 0,
            "still_open": 0,
            "reconciled": 0,
            "pending_reconciled": 0,
        }

        # Get all open trades from DB
        db_open_trades = self.get_open_trades()
        results["checked"] = len(db_open_trades)

        if not db_open_trades:
            return results

        # Build set of MT5 position IDs (could be ticket or trade_id)
        mt5_ids = set()
        mt5_instruments = set()  # Also track instruments with open positions
        for pos in mt5_positions:
            if pos.get("trade_id"):
                mt5_ids.add(str(pos["trade_id"]))
            if pos.get("ticket"):
                mt5_ids.add(str(pos["ticket"]))
            # Track which instruments have open positions
            if pos.get("instrument"):
                mt5_instruments.add(pos["instrument"])

        fetched_history = []
        # Build lookup dict from MT5 history for P/L data
        history_lookup = {}
        if mt5_history:
            fetched_history = list(mt5_history)
            for h in mt5_history:
                tid = str(h.get("trade_id", ""))
                if tid:
                    history_lookup[tid] = h

        # If no history provided, try to fetch it.
        # Prefer caller-provided MT5 client to avoid creating transient clients
        # that can trigger unnecessary MT5 shutdown/reconnect churn.
        if mt5_history is None and not history_lookup:
            try:
                client = mt5_client
                if client is None:
                    from src.trading.mt5_client import MT5Client
                    client = MT5Client()
                if client.is_connected():
                    for lookback_days in (1, 3, 7, 30):
                        fetched_history = client.get_history(days=lookback_days)
                        for h in fetched_history:
                            tid = str(h.get("trade_id", ""))
                            if tid:
                                history_lookup[tid] = h
                        if history_lookup:
                            logger.debug(
                                f"Fetched {len(history_lookup)} trades from MT5 history for sync "
                                f"(lookback={lookback_days}d)"
                            )
                            break
            except Exception as e:
                logger.warning(f"Could not fetch MT5 history for sync: {e}")

        # Safety guard:
        # If MT5 returned no open positions and we also have no history to validate closure,
        # do not force-close DB trades (likely transient connection/data issue).
        if db_open_trades and not mt5_positions and not history_lookup:
            logger.warning(
                "DB sync skipped forced-close: no MT5 positions and no MT5 history available"
            )
            results["still_open"] = len(db_open_trades)
            return results

        # Check each DB open trade
        for trade in db_open_trades:
            trade_id = trade.get("trade_id")
            if not trade_id:
                continue

            # Check if trade exists in MT5 (by ID)
            if str(trade_id) not in mt5_ids:
                # Trade ID not found in MT5 positions
                # BUT check if there's still an open position for same instrument
                # This handles case where trade_id doesn't match MT5 ticket
                trade_instrument = trade.get("instrument")
                if trade_instrument and trade_instrument in mt5_instruments:
                    # There's still an open position for this instrument
                    # Don't close - likely the same trade with different ID
                    logger.debug(f"Trade {trade_id} ({trade_instrument}) - ID not found but instrument still has open position, skipping close")
                    results["still_open"] += 1
                    continue

                # Trade is OPEN in DB but not in MT5 - close it
                # Try to get actual P/L from history
                history_data = history_lookup.get(str(trade_id))

                if history_data:
                    # We have actual close data from MT5
                    exit_price = history_data.get("exit_price", 0)
                    pnl = history_data.get("pnl", 0)
                    pnl_percent = history_data.get("pnl_percent", 0)
                    closed_at = history_data.get("closed_at", datetime.now().isoformat())

                    with self._connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE trades SET
                                status = 'CLOSED',
                                exit_price = ?,
                                pnl = ?,
                                pnl_percent = ?,
                                closed_at = ?,
                                close_reason = 'SYNC_CLOSED'
                            WHERE trade_id = ? AND status = 'OPEN'
                        """, (
                            exit_price,
                            pnl,
                            pnl_percent,
                            closed_at,
                            trade_id
                        ))

                    results["closed_with_pnl"] += 1
                    logger.info(f"Sync-closed trade {trade_id} with P/L: {pnl:.2f} EUR")
                else:
                    # No history data - close with unknown P/L
                    # No MT5 close deal data yet -> close as pending reconciliation without guessing P/L.
                    with self._connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE trades SET
                                status = 'CLOSED',
                                pnl = NULL,
                                pnl_percent = NULL,
                                closed_at = ?,
                                close_reason = ?
                            WHERE trade_id = ? AND status = 'OPEN'
                        """, (
                            datetime.now().isoformat(),
                            "SYNC_CLOSED_PENDING_RECON",
                            trade_id
                        ))
                    logger.warning(
                        f"Sync-closed trade {trade_id} without MT5 history "
                        f"(reason=SYNC_CLOSED_PENDING_RECON)"
                    )

                results["closed"].append(trade_id)
            else:
                results["still_open"] += 1

        if results["closed"]:
            logger.info(f"DB Sync: Closed {len(results['closed'])} trades ({results['closed_with_pnl']} with P/L data)")

        # Reconcile previously pending-closed trades once MT5 history becomes available.
        if fetched_history:
            try:
                recon = self.sync_from_mt5(fetched_history)
                results["reconciled"] = int(recon.get("imported", 0) or 0)
                if results["reconciled"] > 0:
                    logger.info(f"DB Sync: Reconciled/imported {results['reconciled']} trade(s) from MT5 history")
            except Exception as e:
                logger.warning(f"Failed pending-trade reconciliation during sync: {e}")

        # Direct per-position reconciliation for rows still pending P/L.
        if mt5_client is not None:
            try:
                results["pending_reconciled"] = self.reconcile_pending_closed_with_mt5(mt5_client)
                if results["pending_reconciled"] > 0:
                    logger.info(f"DB Sync: Reconciled {results['pending_reconciled']} pending trade(s) via position lookup")
            except Exception as e:
                logger.warning(f"Pending reconciliation via position lookup failed: {e}")

        return results

    def reconcile_pending_closed_with_mt5(self, mt5_client, lookback_days: int = 30, limit: int = 50) -> int:
        """
        Reconcile CLOSED trades that have no P/L yet using MT5 position-based lookup.
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT trade_id
                FROM trades
                WHERE status = 'CLOSED'
                  AND pnl IS NULL
                  AND close_reason IN ('SYNC_CLOSED_NO_PNL', 'SYNC_CLOSED_ESTIMATED_SL', 'SYNC_CLOSED_PENDING_RECON')
                ORDER BY datetime(COALESCE(closed_at, timestamp)) DESC
                LIMIT ?
                """,
                (int(limit),),
            )
            pending_ids = [str(row[0]) for row in cursor.fetchall() if row[0] is not None]

        if not pending_ids:
            return 0

        reconciled = 0
        for trade_id in pending_ids:
            try:
                mt5_trade = mt5_client.get_closed_trade_by_position(trade_id, days=lookback_days)
                if not mt5_trade:
                    continue
                if str(mt5_trade.get("trade_id")) != str(trade_id):
                    continue

                with self._connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        UPDATE trades SET
                            exit_price = ?,
                            pnl = ?,
                            pnl_percent = ?,
                            closed_at = ?,
                            close_reason = 'MT5_SYNC_RECON'
                        WHERE trade_id = ? AND status = 'CLOSED' AND pnl IS NULL
                        """,
                        (
                            mt5_trade.get("exit_price"),
                            mt5_trade.get("pnl"),
                            mt5_trade.get("pnl_percent"),
                            mt5_trade.get("closed_at"),
                            trade_id,
                        ),
                    )
                    if cursor.rowcount > 0:
                        reconciled += 1
            except Exception as e:
                logger.debug(f"Pending reconcile failed for trade {trade_id}: {e}")

        return reconciled

    # ===================
    # AI Override Operations
    # ===================

    def log_override(self, data: dict) -> int:
        """
        Log an AI override decision.

        Args:
            data: Override details dict

        Returns:
            Override row ID
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO override_log (
                    timestamp, instrument, direction,
                    original_skip_reason, original_confidence,
                    override_recommended, ai_confidence, ai_reasoning,
                    suggested_adjustment, adjustment_applied, adjustment_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", datetime.now().isoformat()),
                data.get("instrument"),
                data.get("direction"),
                data.get("original_skip_reason"),
                data.get("original_confidence"),
                int(data.get("override_recommended", 0)),
                data.get("ai_confidence"),
                data.get("ai_reasoning"),
                data.get("suggested_adjustment"),
                data.get("adjustment_applied"),
                data.get("adjustment_value"),
            ))

            logger.info(f"Override logged: {data.get('instrument')} - recommended={data.get('override_recommended')}")
            return cursor.lastrowid

    def update_override_result(
        self,
        instrument: str,
        direction: str,
        trade_executed: bool = False,
        trade_id: str = None,
        trade_outcome: str = None,
        pnl: float = None
    ) -> bool:
        """
        Update the most recent override with trade result.

        Args:
            instrument: Instrument symbol
            direction: Trade direction
            trade_executed: Whether trade was executed
            trade_id: Trade ID if executed
            trade_outcome: WIN/LOSS/BREAKEVEN
            pnl: Profit/loss amount

        Returns:
            True if updated successfully
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE override_log SET
                    trade_executed = ?,
                    trade_id = ?,
                    trade_outcome = ?,
                    pnl = ?
                WHERE id = (
                    SELECT id FROM override_log
                    WHERE instrument = ? AND direction = ?
                    AND override_recommended = 1
                    ORDER BY id DESC LIMIT 1
                )
            """, (
                1 if trade_executed else 0,
                trade_id,
                trade_outcome,
                pnl,
                instrument,
                direction
            ))
            return cursor.rowcount > 0

    def get_override_stats(self, days: int = 7) -> dict:
        """
        Get AI override statistics for the last N days.

        Returns:
            Dict with override statistics
        """
        cutoff = datetime.now() - timedelta(days=days)

        with self._connection() as conn:
            cursor = conn.cursor()

            # Total overrides evaluated
            cursor.execute("""
                SELECT COUNT(*) FROM override_log
                WHERE timestamp >= ?
            """, (cutoff.isoformat(),))
            total_evaluated = cursor.fetchone()[0]

            # Overrides recommended
            cursor.execute("""
                SELECT COUNT(*) FROM override_log
                WHERE override_recommended = 1 AND timestamp >= ?
            """, (cutoff.isoformat(),))
            total_recommended = cursor.fetchone()[0]

            # Overrides executed
            cursor.execute("""
                SELECT COUNT(*) FROM override_log
                WHERE trade_executed = 1 AND timestamp >= ?
            """, (cutoff.isoformat(),))
            total_executed = cursor.fetchone()[0]

            # Override wins/losses
            cursor.execute("""
                SELECT trade_outcome, COUNT(*) as count, COALESCE(SUM(pnl), 0) as total_pnl
                FROM override_log
                WHERE trade_executed = 1 AND trade_outcome IS NOT NULL
                AND timestamp >= ?
                GROUP BY trade_outcome
            """, (cutoff.isoformat(),))
            outcomes = {row["trade_outcome"]: {"count": row["count"], "pnl": row["total_pnl"]}
                       for row in cursor.fetchall()}

            # Overrides by adjustment type
            cursor.execute("""
                SELECT adjustment_applied, COUNT(*) as count,
                       SUM(CASE WHEN trade_outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN trade_outcome = 'LOSS' THEN 1 ELSE 0 END) as losses
                FROM override_log
                WHERE trade_executed = 1 AND adjustment_applied IS NOT NULL
                AND timestamp >= ?
                GROUP BY adjustment_applied
            """, (cutoff.isoformat(),))
            by_adjustment = {row["adjustment_applied"]: {
                "count": row["count"],
                "wins": row["wins"],
                "losses": row["losses"],
                "win_rate": (row["wins"] / row["count"] * 100) if row["count"] > 0 else 0
            } for row in cursor.fetchall()}

            wins = outcomes.get("WIN", {}).get("count", 0)
            losses = outcomes.get("LOSS", {}).get("count", 0)
            total_with_outcome = wins + losses

            return {
                "total_evaluated": total_evaluated,
                "total_recommended": total_recommended,
                "total_executed": total_executed,
                "recommendation_rate": round(total_recommended / total_evaluated * 100, 1) if total_evaluated > 0 else 0,
                "execution_rate": round(total_executed / total_recommended * 100, 1) if total_recommended > 0 else 0,
                "outcomes": outcomes,
                "win_rate": round(wins / total_with_outcome * 100, 1) if total_with_outcome > 0 else 0,
                "by_adjustment": by_adjustment,
            }

    def get_recent_overrides(self, limit: int = 50) -> list[dict]:
        """Get recent override decisions."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM override_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            results = []
            for row in cursor.fetchall():
                item = dict(row)
                # Parse JSON if present
                if item.get("suggested_adjustment"):
                    try:
                        item["suggested_adjustment"] = json.loads(item["suggested_adjustment"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                results.append(item)
            return results


    # ===================
    # Market Regime Operations (Phase 1 Enhancement)
    # ===================

    def log_market_regime(self, data: dict) -> int:
        """
        Log a market regime observation.

        Args:
            data: Regime details dict

        Returns:
            Regime row ID
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO market_regimes (
                    timestamp, instrument, timeframe,
                    regime, regime_strength,
                    adx, bollinger_width, bollinger_width_percentile,
                    atr_pips, trend, trend_strength
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp", datetime.now().isoformat()),
                data.get("instrument"),
                data.get("timeframe", "M5"),
                data.get("regime"),
                data.get("regime_strength"),
                data.get("adx"),
                data.get("bollinger_width"),
                data.get("bollinger_width_percentile"),
                data.get("atr_pips"),
                data.get("trend"),
                data.get("trend_strength"),
            ))

            return cursor.lastrowid

    def update_regime_trade_result(
        self,
        instrument: str,
        regime: str,
        trade_id: str,
        trade_outcome: str,
        pnl: float
    ) -> bool:
        """
        Update the most recent regime entry with trade result.

        Args:
            instrument: Instrument symbol
            regime: The regime that was active
            trade_id: Trade ID
            trade_outcome: WIN/LOSS/BREAKEVEN
            pnl: Profit/loss amount

        Returns:
            True if updated successfully
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE market_regimes SET
                    trade_taken = 1,
                    trade_id = ?,
                    trade_outcome = ?,
                    pnl = ?
                WHERE id = (
                    SELECT id FROM market_regimes
                    WHERE instrument = ? AND regime = ?
                    ORDER BY id DESC LIMIT 1
                )
            """, (
                trade_id,
                trade_outcome,
                pnl,
                instrument,
                regime
            ))
            return cursor.rowcount > 0

    def get_regime_stats(self, instrument: str = None, days: int = 30) -> dict:
        """
        Get regime statistics for learning.

        Args:
            instrument: Filter by instrument (optional)
            days: Number of days to include

        Returns:
            Dict with regime statistics
        """
        cutoff = datetime.now() - timedelta(days=days)

        with self._connection() as conn:
            cursor = conn.cursor()

            # Base query
            if instrument:
                cursor.execute("""
                    SELECT regime, COUNT(*) as count,
                           SUM(CASE WHEN trade_taken = 1 THEN 1 ELSE 0 END) as trades_taken,
                           SUM(CASE WHEN trade_outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                           SUM(CASE WHEN trade_outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                           COALESCE(SUM(pnl), 0) as total_pnl,
                           AVG(adx) as avg_adx,
                           AVG(bollinger_width) as avg_bb_width
                    FROM market_regimes
                    WHERE instrument = ? AND timestamp >= ?
                    GROUP BY regime
                """, (instrument, cutoff.isoformat()))
            else:
                cursor.execute("""
                    SELECT regime, COUNT(*) as count,
                           SUM(CASE WHEN trade_taken = 1 THEN 1 ELSE 0 END) as trades_taken,
                           SUM(CASE WHEN trade_outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                           SUM(CASE WHEN trade_outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                           COALESCE(SUM(pnl), 0) as total_pnl,
                           AVG(adx) as avg_adx,
                           AVG(bollinger_width) as avg_bb_width
                    FROM market_regimes
                    WHERE timestamp >= ?
                    GROUP BY regime
                """, (cutoff.isoformat(),))

            stats = {}
            for row in cursor.fetchall():
                regime = row["regime"]
                trades = row["trades_taken"]
                wins = row["wins"] or 0
                losses = row["losses"] or 0

                stats[regime] = {
                    "observations": row["count"],
                    "trades_taken": trades,
                    "wins": wins,
                    "losses": losses,
                    "win_rate": round(wins / trades * 100, 1) if trades > 0 else 0,
                    "total_pnl": round(row["total_pnl"], 2),
                    "avg_adx": round(row["avg_adx"] or 0, 1),
                    "avg_bb_width": round(row["avg_bb_width"] or 0, 2),
                }

            return stats

    def get_regime_history(
        self,
        instrument: str,
        limit: int = 100
    ) -> list[dict]:
        """
        Get recent regime history for an instrument.

        Args:
            instrument: Instrument symbol
            limit: Max number of entries

        Returns:
            List of regime dicts
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM market_regimes
                WHERE instrument = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (instrument, limit))

            return [dict(row) for row in cursor.fetchall()]


# Singleton database instance
db = Database()
