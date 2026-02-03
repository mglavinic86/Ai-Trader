"""
Learning Engine - The brain that learns from every trade.

This module is the core of the automated learning system.
It tracks patterns, calculates statistics, and provides
intelligence for future trading decisions.

GOAL: Maximize profits by learning from every trade.

Usage:
    from src.analysis.learning_engine import LearningEngine

    engine = LearningEngine()

    # After a trade closes
    engine.learn_from_trade(trade_data, post_trade_analysis)

    # Before a new trade
    insights = engine.get_insights_for_trade("EUR_USD", "LONG", context)
    adjusted_confidence = engine.adjust_confidence(75, insights)
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.utils.logger import logger
from src.utils.database import db


@dataclass
class PatternStats:
    """Statistics for a specific pattern."""
    pattern_name: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    avg_win_pips: float = 0.0
    avg_loss_pips: float = 0.0
    win_rate: float = 0.0
    expectancy: float = 0.0  # Expected pips per trade
    last_updated: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TradeInsight:
    """Insight for a potential trade based on historical data."""
    # Warnings
    warnings: List[str] = field(default_factory=list)

    # Positive signals
    positive_signals: List[str] = field(default_factory=list)

    # Statistics
    relevant_stats: Dict[str, PatternStats] = field(default_factory=dict)

    # Confidence adjustment
    confidence_adjustment: int = 0
    adjustment_reasons: List[str] = field(default_factory=list)

    # Risk recommendation
    recommended_risk_multiplier: float = 1.0

    # Overall assessment
    should_trade: bool = True
    trade_quality_score: int = 50  # 0-100

    def to_dict(self) -> dict:
        return {
            "warnings": self.warnings,
            "positive_signals": self.positive_signals,
            "relevant_stats": {k: v.to_dict() for k, v in self.relevant_stats.items()},
            "confidence_adjustment": self.confidence_adjustment,
            "adjustment_reasons": self.adjustment_reasons,
            "recommended_risk_multiplier": self.recommended_risk_multiplier,
            "should_trade": self.should_trade,
            "trade_quality_score": self.trade_quality_score
        }

    def format_for_prompt(self) -> str:
        """Format insights for inclusion in analysis prompts."""
        lines = []

        if self.warnings:
            lines.append("⚠️ UPOZORENJA IZ PROŠLIH TRADEOVA:")
            for w in self.warnings[:5]:
                lines.append(f"  - {w}")
            lines.append("")

        if self.positive_signals:
            lines.append("✅ POZITIVNI SIGNALI:")
            for p in self.positive_signals[:3]:
                lines.append(f"  - {p}")
            lines.append("")

        if self.confidence_adjustment != 0:
            direction = "smanjen" if self.confidence_adjustment < 0 else "povećan"
            lines.append(f"📊 CONFIDENCE ADJUSTMENT: {self.confidence_adjustment:+d}% ({direction})")
            for reason in self.adjustment_reasons[:3]:
                lines.append(f"  - {reason}")
            lines.append("")

        if not self.should_trade:
            lines.append("🛑 PREPORUKA: NE TRGUJ - povijesni podaci pokazuju loše rezultate za ovaj setup")

        return "\n".join(lines)


class LearningEngine:
    """
    The Learning Engine - learns from every trade to improve future decisions.

    Key functions:
    1. Store detailed analysis of every trade
    2. Track success rates for various patterns
    3. Provide warnings when about to repeat mistakes
    4. Adjust confidence based on historical performance
    5. Eventually: Auto-approve/reject trades based on learned patterns
    """

    # Minimum trades before pattern is considered reliable
    # Higher = need more data before blocking (prevents premature blocking)
    MIN_TRADES_FOR_PATTERN = 3  # Need 3+ trades before warning
    MIN_TRADES_FOR_CRITICAL = 5  # Need 5+ losses before blocking (0% win rate)

    # Confidence adjustment limits
    MAX_CONFIDENCE_PENALTY = -25
    MAX_CONFIDENCE_BONUS = +15

    # Win rate thresholds
    POOR_WIN_RATE = 0.30  # Below this = strong warning
    LOW_WIN_RATE = 0.45   # Below this = warning
    GOOD_WIN_RATE = 0.55  # Above this = positive signal
    EXCELLENT_WIN_RATE = 0.65  # Above this = bonus

    def __init__(self):
        """Initialize the learning engine."""
        self._init_tables()
        logger.info("LearningEngine initialized")

    def _init_tables(self):
        """Create learning-specific tables if they don't exist."""
        with db._connection() as conn:
            cursor = conn.cursor()

            # Trade analyses table - stores detailed post-trade analysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    instrument TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    pnl_pips REAL,
                    pnl_amount REAL,
                    duration_hours REAL,

                    -- Market context
                    htf_trend TEXT,
                    ltf_trend TEXT,
                    trend_aligned INTEGER,
                    rsi_at_entry REAL,
                    atr_pips REAL,

                    -- Entry analysis
                    entry_quality TEXT,
                    session TEXT,
                    was_killzone INTEGER,
                    day_of_week TEXT,
                    with_trend INTEGER,
                    at_fvg INTEGER,
                    at_order_block INTEGER,
                    at_support_resistance INTEGER,

                    -- Excursion
                    mfe_pips REAL,
                    mae_pips REAL,
                    mfe_r_multiple REAL,
                    mae_r_multiple REAL,
                    reached_1r INTEGER,
                    reached_2r INTEGER,
                    stop_hunt INTEGER,

                    -- Exit
                    exit_type TEXT,
                    was_optimal_exit INTEGER,
                    reversed_after_exit INTEGER,

                    -- Outcome
                    outcome TEXT,
                    was_good_trade INTEGER,

                    -- Lessons
                    findings TEXT,  -- JSON array
                    lessons TEXT,   -- JSON array

                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Pattern statistics table - aggregated stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pattern_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,  -- e.g., 'instrument', 'session', 'trend_alignment'
                    pattern_value TEXT NOT NULL,  -- e.g., 'EUR_USD', 'LONDON', 'aligned'
                    instrument TEXT,  -- Optional: for instrument-specific patterns
                    direction TEXT,   -- Optional: LONG/SHORT specific

                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_pnl_pips REAL DEFAULT 0,
                    total_pnl_amount REAL DEFAULT 0,
                    avg_mfe_pips REAL DEFAULT 0,
                    avg_mae_pips REAL DEFAULT 0,

                    last_updated TEXT,

                    UNIQUE(pattern_type, pattern_value, instrument, direction)
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_instrument ON trade_analyses(instrument)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_outcome ON trade_analyses(outcome)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON pattern_stats(pattern_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_instrument ON pattern_stats(instrument)")

    def learn_from_trade(self, trade_data: dict, analysis: 'PostTradeAnalysis') -> dict:
        """
        Learn from a completed trade.

        This is the main entry point after a trade closes.
        It stores the analysis and updates all relevant pattern statistics.

        Args:
            trade_data: Basic trade data (from database)
            analysis: PostTradeAnalysis result

        Returns:
            Dict with learning results
        """
        result = {
            "analysis_saved": False,
            "patterns_updated": 0,
            "new_insights": []
        }

        try:
            # 1. Save detailed analysis
            self._save_analysis(analysis)
            result["analysis_saved"] = True

            # 2. Update pattern statistics
            patterns_updated = self._update_pattern_stats(analysis)
            result["patterns_updated"] = patterns_updated

            # 3. Check for new insights/warnings
            insights = self._check_for_new_insights(analysis)
            result["new_insights"] = insights

            logger.info(
                f"Learned from trade {analysis.trade_id}: "
                f"saved analysis, updated {patterns_updated} patterns"
            )

            return result

        except Exception as e:
            logger.error(f"Error learning from trade: {e}")
            return result

    def _save_analysis(self, analysis: 'PostTradeAnalysis'):
        """Save detailed analysis to database."""
        with db._connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO trade_analyses (
                    trade_id, instrument, direction, pnl_pips, pnl_amount, duration_hours,
                    htf_trend, ltf_trend, trend_aligned, rsi_at_entry, atr_pips,
                    entry_quality, session, was_killzone, day_of_week, with_trend,
                    at_fvg, at_order_block, at_support_resistance,
                    mfe_pips, mae_pips, mfe_r_multiple, mae_r_multiple,
                    reached_1r, reached_2r, stop_hunt,
                    exit_type, was_optimal_exit, reversed_after_exit,
                    outcome, was_good_trade, findings, lessons
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis.trade_id,
                analysis.instrument,
                analysis.direction,
                analysis.pnl_pips,
                analysis.pnl_amount,
                analysis.duration_hours,
                analysis.market_context.htf_trend,
                analysis.market_context.ltf_trend,
                1 if analysis.market_context.trend_aligned else 0,
                analysis.market_context.rsi_at_entry,
                analysis.market_context.atr_pips,
                analysis.entry_analysis.quality.value,
                analysis.entry_analysis.session.value,
                1 if analysis.entry_analysis.was_killzone else 0,
                analysis.entry_analysis.day_of_week,
                1 if analysis.entry_analysis.with_trend else 0,
                1 if analysis.entry_analysis.at_fvg else 0,
                1 if analysis.entry_analysis.at_order_block else 0,
                1 if analysis.entry_analysis.at_support_resistance else 0,
                analysis.excursion.mfe_pips,
                analysis.excursion.mae_pips,
                analysis.excursion.mfe_as_multiple_of_risk,
                analysis.excursion.mae_as_multiple_of_risk,
                1 if analysis.excursion.reached_1r_profit else 0,
                1 if analysis.excursion.reached_2r_profit else 0,
                1 if analysis.excursion.stop_hunt_detected else 0,
                analysis.exit_analysis.exit_type,
                1 if analysis.exit_analysis.was_optimal else 0,
                1 if analysis.exit_analysis.reversed_after_exit else 0,
                analysis.outcome.value,
                1 if analysis.was_good_trade else 0,
                json.dumps(analysis.findings),
                json.dumps(analysis.lessons)
            ))

    def _update_pattern_stats(self, analysis: 'PostTradeAnalysis') -> int:
        """Update all relevant pattern statistics."""
        count = 0
        won = analysis.pnl_pips > 0

        # Patterns to track
        patterns = [
            # Global patterns
            ("instrument", analysis.instrument, None, None),
            ("instrument_direction", f"{analysis.instrument}_{analysis.direction}", None, None),
            ("session", analysis.entry_analysis.session.value, analysis.instrument, None),
            ("killzone", "YES" if analysis.entry_analysis.was_killzone else "NO", analysis.instrument, None),
            ("trend_aligned", "YES" if analysis.market_context.trend_aligned else "NO", analysis.instrument, None),
            ("with_trend", "YES" if analysis.entry_analysis.with_trend else "NO", analysis.instrument, analysis.direction),
            ("entry_quality", analysis.entry_analysis.quality.value, analysis.instrument, None),
            ("day_of_week", analysis.entry_analysis.day_of_week, analysis.instrument, None),
            ("htf_trend_direction", f"{analysis.market_context.htf_trend}_{analysis.direction}", analysis.instrument, None),

            # Confluence patterns
            ("at_fvg", "YES" if analysis.entry_analysis.at_fvg else "NO", analysis.instrument, None),
            ("at_order_block", "YES" if analysis.entry_analysis.at_order_block else "NO", analysis.instrument, None),
            ("at_sr", "YES" if analysis.entry_analysis.at_support_resistance else "NO", analysis.instrument, None),

            # Market regime patterns (Phase 4 Enhancement)
            ("regime", getattr(analysis, 'market_regime', 'UNKNOWN'), analysis.instrument, None),
            ("regime_direction", f"{getattr(analysis, 'market_regime', 'UNKNOWN')}_{analysis.direction}", analysis.instrument, None),
        ]

        for pattern_type, pattern_value, instrument, direction in patterns:
            self._update_single_pattern(
                pattern_type=pattern_type,
                pattern_value=pattern_value,
                instrument=instrument,
                direction=direction,
                won=won,
                pnl_pips=analysis.pnl_pips,
                pnl_amount=analysis.pnl_amount,
                mfe_pips=analysis.excursion.mfe_pips,
                mae_pips=analysis.excursion.mae_pips
            )
            count += 1

        return count

    def _update_single_pattern(
        self,
        pattern_type: str,
        pattern_value: str,
        instrument: Optional[str],
        direction: Optional[str],
        won: bool,
        pnl_pips: float,
        pnl_amount: float,
        mfe_pips: float,
        mae_pips: float
    ):
        """Update a single pattern's statistics."""
        with db._connection() as conn:
            cursor = conn.cursor()

            # Get existing stats
            cursor.execute("""
                SELECT total_trades, winning_trades, losing_trades,
                       total_pnl_pips, total_pnl_amount, avg_mfe_pips, avg_mae_pips
                FROM pattern_stats
                WHERE pattern_type = ? AND pattern_value = ?
                      AND (instrument = ? OR (instrument IS NULL AND ? IS NULL))
                      AND (direction = ? OR (direction IS NULL AND ? IS NULL))
            """, (pattern_type, pattern_value, instrument, instrument, direction, direction))

            row = cursor.fetchone()

            if row:
                # Update existing
                total = row[0] + 1
                wins = row[1] + (1 if won else 0)
                losses = row[2] + (0 if won else 1)
                total_pnl = row[3] + pnl_pips
                total_amount = row[4] + pnl_amount
                # Running average for MFE/MAE
                avg_mfe = (row[5] * row[0] + mfe_pips) / total
                avg_mae = (row[6] * row[0] + mae_pips) / total

                cursor.execute("""
                    UPDATE pattern_stats SET
                        total_trades = ?,
                        winning_trades = ?,
                        losing_trades = ?,
                        total_pnl_pips = ?,
                        total_pnl_amount = ?,
                        avg_mfe_pips = ?,
                        avg_mae_pips = ?,
                        last_updated = ?
                    WHERE pattern_type = ? AND pattern_value = ?
                          AND (instrument = ? OR (instrument IS NULL AND ? IS NULL))
                          AND (direction = ? OR (direction IS NULL AND ? IS NULL))
                """, (
                    total, wins, losses, total_pnl, total_amount, avg_mfe, avg_mae,
                    datetime.now(timezone.utc).isoformat(),
                    pattern_type, pattern_value, instrument, instrument, direction, direction
                ))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO pattern_stats (
                        pattern_type, pattern_value, instrument, direction,
                        total_trades, winning_trades, losing_trades,
                        total_pnl_pips, total_pnl_amount, avg_mfe_pips, avg_mae_pips,
                        last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern_type, pattern_value, instrument, direction,
                    1, 1 if won else 0, 0 if won else 1,
                    pnl_pips, pnl_amount, mfe_pips, mae_pips,
                    datetime.now(timezone.utc).isoformat()
                ))

    def _check_for_new_insights(self, analysis: 'PostTradeAnalysis') -> List[str]:
        """Check if this trade reveals any new important insights."""
        insights = []

        # Check for repeated pattern failures
        instrument = analysis.instrument

        # Get recent analyses for this instrument
        with db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT outcome, entry_quality, with_trend, was_killzone
                FROM trade_analyses
                WHERE instrument = ?
                ORDER BY created_at DESC
                LIMIT 5
            """, (instrument,))

            recent = cursor.fetchall()

        if len(recent) >= 3:
            # Check for losing streak
            losses = sum(1 for r in recent[:3] if 'LOSS' in r[0])
            if losses >= 3:
                insights.append(f"ALERT: {instrument} has 3 consecutive losses - review strategy!")

            # Check for poor quality entries
            poor_entries = sum(1 for r in recent[:3] if r[1] == 'POOR')
            if poor_entries >= 2:
                insights.append(f"PATTERN: {instrument} - too many POOR quality entries")

        return insights

    def get_insights_for_trade(
        self,
        instrument: str,
        direction: str,
        context: Optional[dict] = None
    ) -> TradeInsight:
        """
        Get insights for a potential trade based on historical data.

        This is called BEFORE entering a trade to provide:
        - Warnings based on past failures
        - Positive signals based on past successes
        - Confidence adjustments
        - Risk recommendations

        Args:
            instrument: Currency pair
            direction: LONG or SHORT
            context: Optional context (session, killzone, trend, etc.)

        Returns:
            TradeInsight with all relevant information
        """
        insight = TradeInsight()
        context = context or {}

        # Get relevant pattern stats
        stats = self._get_relevant_stats(instrument, direction, context)
        insight.relevant_stats = stats

        # Calculate confidence adjustment and generate warnings/signals
        total_adjustment = 0

        # 1. Check instrument-specific performance
        inst_key = f"instrument_{instrument}"
        if inst_key in stats:
            s = stats[inst_key]
            # For 0% win rate, warn even with just 1 trade (critical)
            min_trades = self.MIN_TRADES_FOR_CRITICAL if s.win_rate == 0 else self.MIN_TRADES_FOR_PATTERN

            if s.total_trades >= min_trades:
                if s.win_rate == 0:
                    insight.warnings.append(
                        f"KRITIČNO: {instrument} ima 0% win rate ({s.losing_trades} gubitka zaredom)!"
                    )
                    total_adjustment -= 20
                    insight.adjustment_reasons.append(f"0% win rate za {instrument}")
                elif s.win_rate < self.POOR_WIN_RATE:
                    insight.warnings.append(
                        f"{instrument} ima samo {s.win_rate*100:.0f}% win rate ({s.winning_trades}/{s.total_trades})"
                    )
                    total_adjustment -= 15
                    insight.adjustment_reasons.append(f"Loš win rate za {instrument}")
                elif s.win_rate < self.LOW_WIN_RATE:
                    insight.warnings.append(
                        f"{instrument} ima nizak win rate: {s.win_rate*100:.0f}%"
                    )
                    total_adjustment -= 10
                    insight.adjustment_reasons.append(f"Nizak win rate za {instrument}")
                elif s.win_rate >= self.EXCELLENT_WIN_RATE:
                    insight.positive_signals.append(
                        f"{instrument} ima odličan win rate: {s.win_rate*100:.0f}%"
                    )
                    total_adjustment += 10
                    insight.adjustment_reasons.append(f"Visok win rate za {instrument}")

        # 2. Check direction-specific performance
        dir_key = f"direction_{instrument}_{direction}"
        if dir_key in stats:
            s = stats[dir_key]
            if s.total_trades >= self.MIN_TRADES_FOR_PATTERN:
                if s.win_rate < self.POOR_WIN_RATE:
                    insight.warnings.append(
                        f"{direction} tradeovi na {instrument}: samo {s.win_rate*100:.0f}% uspješnih"
                    )
                    total_adjustment -= 10
                    insight.adjustment_reasons.append(f"Loš {direction} win rate")

        # 3. Check session performance
        session = context.get("session")
        if session:
            sess_key = f"session_{session}_{instrument}"
            if sess_key in stats:
                s = stats[sess_key]
                if s.total_trades >= self.MIN_TRADES_FOR_PATTERN:
                    if s.win_rate < self.LOW_WIN_RATE:
                        insight.warnings.append(
                            f"{session} session za {instrument}: {s.win_rate*100:.0f}% win rate"
                        )
                        total_adjustment -= 5
                    elif s.win_rate >= self.GOOD_WIN_RATE:
                        insight.positive_signals.append(
                            f"{session} session ima dobar win rate za {instrument}"
                        )
                        total_adjustment += 5

        # 4. Check killzone performance
        killzone = context.get("killzone", context.get("was_killzone"))
        if killzone is not None:
            kz_key = f"killzone_{'YES' if killzone else 'NO'}_{instrument}"
            if kz_key in stats:
                s = stats[kz_key]
                if s.total_trades >= self.MIN_TRADES_FOR_PATTERN:
                    if not killzone and s.win_rate < self.LOW_WIN_RATE:
                        insight.warnings.append(
                            f"Non-killzone entry na {instrument}: samo {s.win_rate*100:.0f}% uspješnih"
                        )
                        total_adjustment -= 10
                        insight.adjustment_reasons.append("Entry izvan killzone-a ima loše rezultate")
                    elif killzone and s.win_rate >= self.GOOD_WIN_RATE:
                        insight.positive_signals.append(
                            f"Killzone entry ima {s.win_rate*100:.0f}% win rate"
                        )
                        total_adjustment += 5

        # 5. Check trend alignment (CRITICAL for profitability!)
        with_trend = context.get("with_trend")
        if with_trend is not None:
            trend_key = f"with_trend_{'YES' if with_trend else 'NO'}_{instrument}_{direction}"
            if trend_key in stats:
                s = stats[trend_key]
                # Counter-trend with 0% win rate is critical even with 1 trade
                min_trades = self.MIN_TRADES_FOR_CRITICAL if (not with_trend and s.win_rate == 0) else self.MIN_TRADES_FOR_PATTERN

                if s.total_trades >= min_trades:
                    if not with_trend and s.win_rate == 0:
                        insight.warnings.append(
                            f"STOP! Counter-trend {direction} na {instrument}: 0/{s.total_trades} uspješnih!"
                        )
                        total_adjustment -= 25
                        insight.adjustment_reasons.append("Counter-trend ima 0% uspješnost")
                    elif not with_trend and s.win_rate < self.POOR_WIN_RATE:
                        insight.warnings.append(
                            f"Counter-trend {direction} na {instrument}: {s.win_rate*100:.0f}% win rate"
                        )
                        total_adjustment -= 15
                        insight.adjustment_reasons.append("Counter-trend trade ima jako loše rezultate")
                    elif with_trend and s.win_rate >= self.GOOD_WIN_RATE:
                        insight.positive_signals.append(
                            f"With-trend {direction} ima {s.win_rate*100:.0f}% win rate"
                        )
                        total_adjustment += 5

        # 6. Check market regime performance (Phase 4 Enhancement)
        regime = context.get("market_regime")
        if regime:
            regime_key = f"regime_{regime}_{instrument}"
            if regime_key in stats:
                s = stats[regime_key]
                if s.total_trades >= self.MIN_TRADES_FOR_PATTERN:
                    if s.win_rate < self.POOR_WIN_RATE:
                        insight.warnings.append(
                            f"{regime} regime za {instrument}: samo {s.win_rate*100:.0f}% win rate"
                        )
                        total_adjustment -= 10
                        insight.adjustment_reasons.append(f"Loš win rate u {regime} režimu")
                    elif s.win_rate >= self.EXCELLENT_WIN_RATE:
                        insight.positive_signals.append(
                            f"{regime} regime ima {s.win_rate*100:.0f}% win rate"
                        )
                        total_adjustment += 8
                        insight.adjustment_reasons.append(f"Odličan win rate u {regime} režimu")

            # Check regime + direction combination
            regime_dir_key = f"regime_direction_{regime}_{direction}_{instrument}"
            if regime_dir_key in stats:
                s = stats[regime_dir_key]
                if s.total_trades >= self.MIN_TRADES_FOR_PATTERN:
                    if s.win_rate < self.POOR_WIN_RATE:
                        insight.warnings.append(
                            f"{direction} u {regime} režimu: {s.win_rate*100:.0f}% win rate"
                        )
                        total_adjustment -= 12
                        insight.adjustment_reasons.append(f"{direction} loš u {regime}")
                    elif s.win_rate >= self.GOOD_WIN_RATE:
                        insight.positive_signals.append(
                            f"{direction} radi dobro u {regime} režimu ({s.win_rate*100:.0f}%)"
                        )
                        total_adjustment += 5

        # 7. Check for recent losing streak
        recent_losses = self._get_recent_consecutive_losses(instrument)
        if recent_losses >= 3:
            insight.warnings.append(
                f"⚠️ {instrument} ima {recent_losses} uzastopna gubitka!"
            )
            total_adjustment -= 10
            insight.adjustment_reasons.append(f"{recent_losses} uzastopna gubitka")

        # Apply limits to adjustment
        insight.confidence_adjustment = max(
            self.MAX_CONFIDENCE_PENALTY,
            min(self.MAX_CONFIDENCE_BONUS, total_adjustment)
        )

        # Calculate trade quality score
        insight.trade_quality_score = self._calculate_trade_quality(insight, context)

        # Determine risk multiplier
        if insight.trade_quality_score >= 70:
            insight.recommended_risk_multiplier = 1.0
        elif insight.trade_quality_score >= 50:
            insight.recommended_risk_multiplier = 0.75
        elif insight.trade_quality_score >= 30:
            insight.recommended_risk_multiplier = 0.5
        else:
            insight.recommended_risk_multiplier = 0.25
            insight.should_trade = False

        # Final should_trade decision
        if insight.confidence_adjustment <= -20 or insight.trade_quality_score < 30:
            insight.should_trade = False

        return insight

    def _get_relevant_stats(
        self,
        instrument: str,
        direction: str,
        context: dict
    ) -> Dict[str, PatternStats]:
        """Get all relevant pattern statistics."""
        stats = {}

        with db._connection() as conn:
            cursor = conn.cursor()

            # Get all patterns for this instrument
            cursor.execute("""
                SELECT pattern_type, pattern_value, instrument, direction,
                       total_trades, winning_trades, losing_trades,
                       total_pnl_pips, avg_mfe_pips, avg_mae_pips
                FROM pattern_stats
                WHERE instrument IS NULL OR instrument = ?
            """, (instrument,))

            for row in cursor.fetchall():
                p_type, p_value, p_inst, p_dir, total, wins, losses, pnl, mfe, mae = row

                # Create key based on specificity
                if p_inst and p_dir:
                    key = f"{p_type}_{p_value}_{p_inst}_{p_dir}"
                elif p_inst:
                    key = f"{p_type}_{p_value}_{p_inst}"
                else:
                    key = f"{p_type}_{p_value}"

                win_rate = wins / total if total > 0 else 0
                avg_win = pnl / wins if wins > 0 else 0
                avg_loss = pnl / losses if losses > 0 else 0  # Will be negative
                expectancy = (win_rate * mfe) - ((1 - win_rate) * mae)

                stats[key] = PatternStats(
                    pattern_name=key,
                    total_trades=total,
                    winning_trades=wins,
                    losing_trades=losses,
                    total_pnl=pnl,
                    avg_win_pips=mfe,  # Using MFE as proxy for avg win
                    avg_loss_pips=mae,  # Using MAE as proxy for avg loss
                    win_rate=win_rate,
                    expectancy=expectancy
                )

        return stats

    def _get_recent_consecutive_losses(self, instrument: str) -> int:
        """Get number of recent consecutive losses for an instrument."""
        with db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pnl_pips FROM trade_analyses
                WHERE instrument = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (instrument,))

            consecutive = 0
            for (pnl,) in cursor.fetchall():
                if pnl < 0:
                    consecutive += 1
                else:
                    break

            return consecutive

    def _calculate_trade_quality(self, insight: TradeInsight, context: dict) -> int:
        """Calculate overall trade quality score (0-100)."""
        score = 50  # Start neutral

        # Warnings decrease score
        score -= len(insight.warnings) * 10

        # Positive signals increase score
        score += len(insight.positive_signals) * 10

        # Context bonuses
        if context.get("killzone") or context.get("was_killzone"):
            score += 10
        if context.get("with_trend"):
            score += 15
        if context.get("at_fvg") or context.get("at_order_block"):
            score += 10

        # Trend alignment bonus
        if context.get("trend_aligned"):
            score += 10

        return max(0, min(100, score))

    def adjust_confidence(self, original_confidence: int, insight: TradeInsight) -> int:
        """
        Adjust confidence score based on historical insights.

        Args:
            original_confidence: Original confidence from analysis
            insight: TradeInsight with adjustment info

        Returns:
            Adjusted confidence score
        """
        adjusted = original_confidence + insight.confidence_adjustment
        return max(0, min(100, adjusted))

    def get_learning_summary(self, instrument: Optional[str] = None) -> dict:
        """
        Get summary of what the system has learned.

        Args:
            instrument: Optional filter by instrument

        Returns:
            Summary dict with statistics and insights
        """
        summary = {
            "total_trades_analyzed": 0,
            "instruments": {},
            "best_patterns": [],
            "worst_patterns": [],
            "key_insights": []
        }

        with db._connection() as conn:
            cursor = conn.cursor()

            # Total trades
            if instrument:
                cursor.execute(
                    "SELECT COUNT(*) FROM trade_analyses WHERE instrument = ?",
                    (instrument,)
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM trade_analyses")
            summary["total_trades_analyzed"] = cursor.fetchone()[0]

            # Get instrument stats
            cursor.execute("""
                SELECT instrument,
                       COUNT(*) as total,
                       SUM(CASE WHEN pnl_pips > 0 THEN 1 ELSE 0 END) as wins,
                       SUM(pnl_pips) as total_pnl,
                       SUM(pnl_amount) as total_amount
                FROM trade_analyses
                GROUP BY instrument
            """)

            for row in cursor.fetchall():
                inst, total, wins, pnl_pips, pnl_amount = row
                summary["instruments"][inst] = {
                    "total_trades": total,
                    "win_rate": (wins / total * 100) if total > 0 else 0,
                    "total_pnl_pips": round(pnl_pips or 0, 1),
                    "total_pnl_amount": round(pnl_amount or 0, 2)
                }

            # Best patterns (highest win rate with enough trades)
            cursor.execute("""
                SELECT pattern_type, pattern_value, instrument,
                       total_trades, winning_trades,
                       CAST(winning_trades AS FLOAT) / total_trades as win_rate
                FROM pattern_stats
                WHERE total_trades >= 3
                ORDER BY win_rate DESC
                LIMIT 5
            """)

            for row in cursor.fetchall():
                summary["best_patterns"].append({
                    "pattern": f"{row[0]}: {row[1]}" + (f" ({row[2]})" if row[2] else ""),
                    "trades": row[3],
                    "win_rate": round(row[5] * 100, 1)
                })

            # Worst patterns
            cursor.execute("""
                SELECT pattern_type, pattern_value, instrument,
                       total_trades, winning_trades,
                       CAST(winning_trades AS FLOAT) / total_trades as win_rate
                FROM pattern_stats
                WHERE total_trades >= 3
                ORDER BY win_rate ASC
                LIMIT 5
            """)

            for row in cursor.fetchall():
                summary["worst_patterns"].append({
                    "pattern": f"{row[0]}: {row[1]}" + (f" ({row[2]})" if row[2] else ""),
                    "trades": row[3],
                    "win_rate": round(row[5] * 100, 1)
                })

        # Generate key insights
        if summary["worst_patterns"]:
            worst = summary["worst_patterns"][0]
            if worst["win_rate"] < 30:
                summary["key_insights"].append(
                    f"IZBJEGAVAJ: {worst['pattern']} ima samo {worst['win_rate']}% win rate"
                )

        if summary["best_patterns"]:
            best = summary["best_patterns"][0]
            if best["win_rate"] > 60:
                summary["key_insights"].append(
                    f"PREFERIRAJ: {best['pattern']} ima {best['win_rate']}% win rate"
                )

        return summary


    def get_regime_learning_stats(
        self,
        instrument: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get learning statistics grouped by market regime.

        Phase 4 Enhancement: Provides insights on which regimes
        work best for each instrument.

        Args:
            instrument: Optional filter by instrument

        Returns:
            Dict with regime statistics
        """
        stats = {
            "regimes": {},
            "best_regime": None,
            "worst_regime": None,
            "recommendations": []
        }

        with db._connection() as conn:
            cursor = conn.cursor()

            if instrument:
                cursor.execute("""
                    SELECT pattern_value, total_trades, winning_trades, total_pnl_pips
                    FROM pattern_stats
                    WHERE pattern_type = 'regime' AND instrument = ?
                    AND total_trades >= 3
                    ORDER BY total_trades DESC
                """, (instrument,))
            else:
                cursor.execute("""
                    SELECT pattern_value, SUM(total_trades), SUM(winning_trades), SUM(total_pnl_pips)
                    FROM pattern_stats
                    WHERE pattern_type = 'regime'
                    GROUP BY pattern_value
                    HAVING SUM(total_trades) >= 3
                    ORDER BY SUM(total_trades) DESC
                """)

            best_wr = 0.0
            worst_wr = 1.0

            for row in cursor.fetchall():
                regime, total, wins, pnl = row
                win_rate = wins / total if total > 0 else 0

                stats["regimes"][regime] = {
                    "total_trades": total,
                    "wins": wins,
                    "losses": total - wins,
                    "win_rate": round(win_rate * 100, 1),
                    "total_pnl": round(pnl or 0, 1),
                }

                if win_rate > best_wr:
                    best_wr = win_rate
                    stats["best_regime"] = regime
                if win_rate < worst_wr:
                    worst_wr = win_rate
                    stats["worst_regime"] = regime

        # Generate recommendations
        if stats["regimes"]:
            for regime, data in stats["regimes"].items():
                if data["win_rate"] < 30:
                    stats["recommendations"].append(
                        f"IZBJEGAVAJ: {regime} regime ima samo {data['win_rate']}% win rate"
                    )
                elif data["win_rate"] > 60:
                    stats["recommendations"].append(
                        f"PREFERIRAJ: {regime} regime ima {data['win_rate']}% win rate"
                    )

        return stats

    def get_regime_adjustment(
        self,
        instrument: str,
        direction: str,
        regime: str
    ) -> int:
        """
        Get confidence adjustment for a specific regime.

        Args:
            instrument: Currency pair
            direction: LONG or SHORT
            regime: Market regime (TRENDING, RANGING, etc.)

        Returns:
            Confidence adjustment (-25 to +15)
        """
        with db._connection() as conn:
            cursor = conn.cursor()

            # Check regime + direction + instrument combo
            cursor.execute("""
                SELECT total_trades, winning_trades
                FROM pattern_stats
                WHERE pattern_type = 'regime_direction'
                AND pattern_value = ?
                AND instrument = ?
            """, (f"{regime}_{direction}", instrument))

            row = cursor.fetchone()
            if not row or row[0] < self.MIN_TRADES_FOR_PATTERN:
                return 0

            total, wins = row
            win_rate = wins / total

            if win_rate == 0:
                return -20
            elif win_rate < self.POOR_WIN_RATE:
                return -15
            elif win_rate < self.LOW_WIN_RATE:
                return -8
            elif win_rate >= self.EXCELLENT_WIN_RATE:
                return +10
            elif win_rate >= self.GOOD_WIN_RATE:
                return +5

            return 0


# Singleton instance
learning_engine = LearningEngine()


# Convenience functions
def learn_from_trade(trade_data: dict, analysis) -> dict:
    """Learn from a completed trade."""
    return learning_engine.learn_from_trade(trade_data, analysis)


def get_trade_insights(instrument: str, direction: str, context: dict = None) -> TradeInsight:
    """Get insights for a potential trade."""
    return learning_engine.get_insights_for_trade(instrument, direction, context)


def adjust_confidence_from_history(confidence: int, instrument: str, direction: str, context: dict = None) -> tuple[int, TradeInsight]:
    """Adjust confidence based on historical data."""
    insight = learning_engine.get_insights_for_trade(instrument, direction, context)
    adjusted = learning_engine.adjust_confidence(confidence, insight)
    return adjusted, insight
