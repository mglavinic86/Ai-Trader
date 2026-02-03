"""
Adaptive Settings Manager - Self-tuning trading parameters based on learned patterns.

This module automatically adjusts trading settings based on historical performance:
- Analyzes what settings would have improved past trades
- Tracks which setting combinations lead to better results
- Automatically adjusts settings within safe bounds
- Reverts adjustments that don't improve performance

Usage:
    from src.analysis.adaptive_settings import adaptive_settings

    # After learning from trades, optimize settings
    adjustments = adaptive_settings.optimize_settings()

    # Get recommended settings for specific context
    settings = adaptive_settings.get_optimal_settings("EUR_USD", "LONDON")
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from src.utils.logger import logger
from src.utils.database import db


@dataclass
class SettingAdjustment:
    """Record of a setting adjustment."""
    setting_name: str
    old_value: Any
    new_value: Any
    reason: str
    timestamp: str
    trades_before: int
    win_rate_before: float


@dataclass
class OptimalSettings:
    """Optimal settings for a specific context."""
    context: str  # e.g., "EUR_USD_LONDON" or "global"
    settings: Dict[str, Any]
    confidence: float  # 0-100, how confident we are in these settings
    based_on_trades: int
    last_updated: str


class AdaptiveSettingsManager:
    """
    Self-tuning settings manager that learns optimal parameters.

    Analyzes historical trades and adjusts:
    - Risk parameters (within hard limits)
    - Entry criteria (confidence, spread, ATR)
    - Exit parameters (R:R, hold time)
    - Session/instrument preferences
    """

    # Settings that CAN be auto-adjusted (with bounds)
    TUNABLE_SETTINGS = {
        "min_confidence_threshold": {"min": 50, "max": 80, "step": 5, "default": 55},
        "target_rr": {"min": 1.2, "max": 3.0, "step": 0.1, "default": 2.0},
        "max_spread_pips": {"min": 1.0, "max": 4.0, "step": 0.5, "default": 2.0},
        "min_atr_pips": {"min": 2.0, "max": 5.0, "step": 0.5, "default": 3.0},
        "max_sl_pips": {"min": 5.0, "max": 20.0, "step": 1.0, "default": 10.0},
        "risk_per_trade_percent": {"min": 0.5, "max": 2.0, "step": 0.25, "default": 1.0},
        "max_hold_minutes": {"min": 30, "max": 240, "step": 30, "default": 120},
        "scan_interval_seconds": {"min": 15, "max": 60, "step": 5, "default": 30},
    }

    # Settings that CANNOT be auto-adjusted (hard limits)
    FIXED_SETTINGS = [
        "max_risk_per_trade",  # Always 3% max
        "max_daily_drawdown",  # Always 5% max
        "max_weekly_drawdown", # Always 10% max
    ]

    # Minimum trades needed before adjusting
    MIN_TRADES_FOR_ADJUSTMENT = 5

    # Performance thresholds
    POOR_PERFORMANCE_THRESHOLD = 0.35  # Below 35% win rate
    GOOD_PERFORMANCE_THRESHOLD = 0.55  # Above 55% win rate

    def __init__(self):
        """Initialize adaptive settings manager."""
        self._init_tables()
        self._load_current_settings()
        logger.info("AdaptiveSettingsManager initialized")

    def _init_tables(self):
        """Create tables for tracking adjustments."""
        with db._connection() as conn:
            cursor = conn.cursor()

            # Track all setting adjustments
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS setting_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_name TEXT NOT NULL,
                    context TEXT DEFAULT 'global',
                    old_value TEXT,
                    new_value TEXT,
                    reason TEXT,
                    trades_before INTEGER,
                    win_rate_before REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Track optimal settings per context
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS optimal_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context TEXT UNIQUE NOT NULL,
                    settings TEXT NOT NULL,  -- JSON
                    confidence REAL DEFAULT 50,
                    based_on_trades INTEGER DEFAULT 0,
                    last_updated TEXT
                )
            """)

            # Track setting performance
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS setting_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_name TEXT NOT NULL,
                    setting_value TEXT NOT NULL,
                    context TEXT DEFAULT 'global',
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    total_pnl_pips REAL DEFAULT 0,
                    avg_mfe REAL DEFAULT 0,
                    avg_mae REAL DEFAULT 0,
                    last_updated TEXT,
                    UNIQUE(setting_name, setting_value, context)
                )
            """)

    def _load_current_settings(self):
        """Load current trading settings."""
        try:
            config_path = Path("settings/auto_trading.json")
            if config_path.exists():
                with open(config_path) as f:
                    self.current_settings = json.load(f)
            else:
                self.current_settings = {}
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self.current_settings = {}

    def analyze_and_optimize(self) -> Dict[str, Any]:
        """
        Main entry point: Analyze performance and optimize settings.

        Returns:
            Dict with adjustments made and recommendations
        """
        result = {
            "adjustments_made": [],
            "recommendations": [],
            "analysis": {}
        }

        # Get performance data
        performance = self._get_performance_analysis()
        result["analysis"] = performance

        if performance["total_trades"] < self.MIN_TRADES_FOR_ADJUSTMENT:
            result["recommendations"].append(
                f"Need {self.MIN_TRADES_FOR_ADJUSTMENT} trades for optimization, have {performance['total_trades']}"
            )
            return result

        # Analyze each tunable setting
        for setting_name, bounds in self.TUNABLE_SETTINGS.items():
            adjustment = self._analyze_setting(setting_name, bounds, performance)
            if adjustment:
                result["adjustments_made"].append(adjustment)

        # Analyze instrument-specific settings
        instrument_adjustments = self._analyze_instruments(performance)
        result["adjustments_made"].extend(instrument_adjustments)

        # Analyze session-specific settings
        session_adjustments = self._analyze_sessions(performance)
        result["adjustments_made"].extend(session_adjustments)

        # Apply adjustments
        if result["adjustments_made"]:
            self._apply_adjustments(result["adjustments_made"])

        return result

    def _get_performance_analysis(self) -> Dict[str, Any]:
        """Get comprehensive performance analysis."""
        analysis = {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl_pips": 0,
            "avg_winner_pips": 0,
            "avg_loser_pips": 0,
            "by_instrument": {},
            "by_session": {},
            "by_confidence_range": {},
            "by_rr_achieved": {},
            "stopped_out_then_reversed": 0,
            "reached_2r_but_closed_earlier": 0,
        }

        with db._connection() as conn:
            cursor = conn.cursor()

            # Overall stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN pnl_pips > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(pnl_pips) as total_pnl,
                    AVG(CASE WHEN pnl_pips > 0 THEN pnl_pips END) as avg_win,
                    AVG(CASE WHEN pnl_pips < 0 THEN pnl_pips END) as avg_loss
                FROM trade_analyses
            """)
            row = cursor.fetchone()
            if row and row[0]:
                analysis["total_trades"] = row[0]
                analysis["win_rate"] = row[1] / row[0] if row[0] > 0 else 0
                analysis["total_pnl_pips"] = row[2] or 0
                analysis["avg_winner_pips"] = row[3] or 0
                analysis["avg_loser_pips"] = abs(row[4] or 0)

            # By instrument
            cursor.execute("""
                SELECT
                    instrument,
                    COUNT(*) as total,
                    SUM(CASE WHEN pnl_pips > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(pnl_pips) as pnl,
                    AVG(mfe_pips) as avg_mfe,
                    AVG(mae_pips) as avg_mae
                FROM trade_analyses
                GROUP BY instrument
            """)
            for row in cursor.fetchall():
                analysis["by_instrument"][row[0]] = {
                    "trades": row[1],
                    "win_rate": row[2] / row[1] if row[1] > 0 else 0,
                    "pnl_pips": row[3] or 0,
                    "avg_mfe": row[4] or 0,
                    "avg_mae": row[5] or 0
                }

            # By session
            cursor.execute("""
                SELECT
                    session,
                    COUNT(*) as total,
                    SUM(CASE WHEN pnl_pips > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(pnl_pips) as pnl
                FROM trade_analyses
                GROUP BY session
            """)
            for row in cursor.fetchall():
                if row[0]:
                    analysis["by_session"][row[0]] = {
                        "trades": row[1],
                        "win_rate": row[2] / row[1] if row[1] > 0 else 0,
                        "pnl_pips": row[3] or 0
                    }

            # Stop hunts (stopped out then price reversed)
            cursor.execute("""
                SELECT COUNT(*) FROM trade_analyses WHERE stop_hunt = 1
            """)
            analysis["stopped_out_then_reversed"] = cursor.fetchone()[0] or 0

            # Reached 2R but closed earlier
            cursor.execute("""
                SELECT COUNT(*) FROM trade_analyses
                WHERE reached_2r = 1 AND mfe_r_multiple < 2.0
            """)
            analysis["reached_2r_but_closed_earlier"] = cursor.fetchone()[0] or 0

        return analysis

    def _analyze_setting(
        self,
        setting_name: str,
        bounds: Dict,
        performance: Dict
    ) -> Optional[Dict]:
        """Analyze if a setting should be adjusted."""

        current_value = self._get_current_value(setting_name, bounds["default"])

        # Specific analysis for each setting type
        if setting_name == "max_sl_pips":
            return self._analyze_stop_loss(current_value, bounds, performance)

        elif setting_name == "target_rr":
            return self._analyze_target_rr(current_value, bounds, performance)

        elif setting_name == "min_confidence_threshold":
            return self._analyze_confidence_threshold(current_value, bounds, performance)

        elif setting_name == "risk_per_trade_percent":
            return self._analyze_risk_percent(current_value, bounds, performance)

        return None

    def _analyze_stop_loss(
        self,
        current_value: float,
        bounds: Dict,
        performance: Dict
    ) -> Optional[Dict]:
        """Analyze if stop loss should be adjusted."""

        # If many stop hunts, widen SL
        stop_hunt_rate = (
            performance["stopped_out_then_reversed"] / performance["total_trades"]
            if performance["total_trades"] > 0 else 0
        )

        if stop_hunt_rate > 0.3 and current_value < bounds["max"]:
            new_value = min(current_value + bounds["step"], bounds["max"])
            return {
                "setting": "scalping.max_sl_pips",
                "old_value": current_value,
                "new_value": new_value,
                "reason": f"High stop hunt rate ({stop_hunt_rate*100:.0f}%) - widening SL"
            }

        # If win rate is good and avg MAE is low, can tighten SL
        if performance["win_rate"] > 0.5:
            with db._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT AVG(mae_pips) FROM trade_analyses WHERE pnl_pips > 0")
                avg_winner_mae = cursor.fetchone()[0] or 5

            if avg_winner_mae < current_value * 0.5 and current_value > bounds["min"]:
                new_value = max(current_value - bounds["step"], bounds["min"])
                return {
                    "setting": "scalping.max_sl_pips",
                    "old_value": current_value,
                    "new_value": new_value,
                    "reason": f"Winners have low MAE ({avg_winner_mae:.1f} pips) - tightening SL"
                }

        return None

    def _analyze_target_rr(
        self,
        current_value: float,
        bounds: Dict,
        performance: Dict
    ) -> Optional[Dict]:
        """Analyze if target R:R should be adjusted."""

        # Check how often trades reach various R multiples
        with db._connection() as conn:
            cursor = conn.cursor()

            # Get MFE distribution
            cursor.execute("""
                SELECT
                    AVG(mfe_r_multiple) as avg_mfe_r,
                    SUM(CASE WHEN mfe_r_multiple >= 1.5 THEN 1 ELSE 0 END) as reached_1_5r,
                    SUM(CASE WHEN mfe_r_multiple >= 2.0 THEN 1 ELSE 0 END) as reached_2r,
                    SUM(CASE WHEN mfe_r_multiple >= 2.5 THEN 1 ELSE 0 END) as reached_2_5r,
                    COUNT(*) as total
                FROM trade_analyses
            """)
            row = cursor.fetchone()

            if not row or row[4] == 0:
                return None

            avg_mfe_r = row[0] or 1
            reached_1_5r_rate = row[1] / row[4]
            reached_2r_rate = row[2] / row[4]
            reached_2_5r_rate = row[3] / row[4]

        # If current target rarely reached but lower target often reached
        if current_value >= 2.0 and reached_2r_rate < 0.3 and reached_1_5r_rate > 0.5:
            new_value = max(1.5, current_value - 0.5)
            return {
                "setting": "scalping.target_rr",
                "old_value": current_value,
                "new_value": new_value,
                "reason": f"Only {reached_2r_rate*100:.0f}% reach 2R, but {reached_1_5r_rate*100:.0f}% reach 1.5R - lowering target"
            }

        # If trades often exceed target significantly, raise it
        if reached_2_5r_rate > 0.4 and current_value < 2.5:
            new_value = min(current_value + 0.5, bounds["max"])
            return {
                "setting": "scalping.target_rr",
                "old_value": current_value,
                "new_value": new_value,
                "reason": f"{reached_2_5r_rate*100:.0f}% reach 2.5R - raising target for more profit"
            }

        return None

    def _analyze_confidence_threshold(
        self,
        current_value: int,
        bounds: Dict,
        performance: Dict
    ) -> Optional[Dict]:
        """Analyze if confidence threshold should be adjusted."""

        # Get win rate by confidence ranges
        with db._connection() as conn:
            cursor = conn.cursor()

            # This requires trades table which has confidence_score
            cursor.execute("""
                SELECT
                    CASE
                        WHEN t.confidence_score < 60 THEN 'low'
                        WHEN t.confidence_score < 75 THEN 'medium'
                        ELSE 'high'
                    END as conf_range,
                    COUNT(*) as total,
                    SUM(CASE WHEN ta.pnl_pips > 0 THEN 1 ELSE 0 END) as wins
                FROM trades t
                JOIN trade_analyses ta ON t.trade_id = ta.trade_id
                WHERE t.confidence_score IS NOT NULL
                GROUP BY conf_range
            """)

            ranges = {}
            for row in cursor.fetchall():
                if row[1] > 0:
                    ranges[row[0]] = {
                        "trades": row[1],
                        "win_rate": row[2] / row[1]
                    }

        # If low confidence trades perform well, lower threshold
        if "low" in ranges and ranges["low"]["trades"] >= 3:
            if ranges["low"]["win_rate"] > 0.5 and current_value > bounds["min"]:
                new_value = max(current_value - bounds["step"], bounds["min"])
                return {
                    "setting": "min_confidence_threshold",
                    "old_value": current_value,
                    "new_value": new_value,
                    "reason": f"Low confidence trades win {ranges['low']['win_rate']*100:.0f}% - can lower threshold"
                }

        # If overall win rate is poor, raise threshold
        if performance["win_rate"] < self.POOR_PERFORMANCE_THRESHOLD and current_value < bounds["max"]:
            new_value = min(current_value + bounds["step"], bounds["max"])
            return {
                "setting": "min_confidence_threshold",
                "old_value": current_value,
                "new_value": new_value,
                "reason": f"Poor win rate ({performance['win_rate']*100:.0f}%) - raising threshold"
            }

        return None

    def _analyze_risk_percent(
        self,
        current_value: float,
        bounds: Dict,
        performance: Dict
    ) -> Optional[Dict]:
        """Analyze if risk percent should be adjusted."""

        # Reduce risk during losing streaks
        with db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pnl_pips FROM trade_analyses
                ORDER BY created_at DESC LIMIT 5
            """)
            recent = [r[0] for r in cursor.fetchall()]

        if len(recent) >= 5:
            recent_losses = sum(1 for p in recent if p < 0)

            # 4+ losses in last 5 trades - reduce risk
            if recent_losses >= 4 and current_value > bounds["min"]:
                new_value = max(current_value - bounds["step"], bounds["min"])
                return {
                    "setting": "risk_per_trade_percent",
                    "old_value": current_value,
                    "new_value": new_value,
                    "reason": f"Losing streak ({recent_losses}/5 losses) - reducing risk"
                }

            # 4+ wins in last 5 trades and good overall - can increase
            recent_wins = 5 - recent_losses
            if recent_wins >= 4 and performance["win_rate"] > 0.55 and current_value < bounds["max"]:
                new_value = min(current_value + bounds["step"], bounds["max"])
                return {
                    "setting": "risk_per_trade_percent",
                    "old_value": current_value,
                    "new_value": new_value,
                    "reason": f"Winning streak ({recent_wins}/5 wins) - increasing risk"
                }

        return None

    def _analyze_instruments(self, performance: Dict) -> List[Dict]:
        """Analyze and potentially disable poorly performing instruments."""
        adjustments = []

        for instrument, stats in performance["by_instrument"].items():
            if stats["trades"] >= self.MIN_TRADES_FOR_ADJUSTMENT:
                # Disable instruments with consistently poor performance
                if stats["win_rate"] < 0.25 and stats["pnl_pips"] < -20:
                    adjustments.append({
                        "setting": f"instrument_disabled.{instrument}",
                        "old_value": False,
                        "new_value": True,
                        "reason": f"{instrument}: {stats['win_rate']*100:.0f}% win rate, {stats['pnl_pips']:.0f} pips - DISABLE"
                    })

        return adjustments

    def _analyze_sessions(self, performance: Dict) -> List[Dict]:
        """Analyze session performance and adjust preferences."""
        adjustments = []

        best_session = None
        best_win_rate = 0
        worst_session = None
        worst_win_rate = 1

        for session, stats in performance["by_session"].items():
            if stats["trades"] >= 3:
                if stats["win_rate"] > best_win_rate:
                    best_win_rate = stats["win_rate"]
                    best_session = session
                if stats["win_rate"] < worst_win_rate:
                    worst_win_rate = stats["win_rate"]
                    worst_session = session

        if worst_session and worst_win_rate < 0.3:
            adjustments.append({
                "setting": f"session_warning.{worst_session}",
                "old_value": None,
                "new_value": "avoid",
                "reason": f"{worst_session} session: only {worst_win_rate*100:.0f}% win rate - AVOID"
            })

        if best_session and best_win_rate > 0.6:
            adjustments.append({
                "setting": f"session_preferred.{best_session}",
                "old_value": None,
                "new_value": "preferred",
                "reason": f"{best_session} session: {best_win_rate*100:.0f}% win rate - PREFER"
            })

        return adjustments

    def _get_current_value(self, setting_name: str, default: Any) -> Any:
        """Get current value of a setting."""
        if "." in setting_name:
            parts = setting_name.split(".")
            value = self.current_settings
            for part in parts:
                value = value.get(part, {})
            return value if value != {} else default
        return self.current_settings.get(setting_name, default)

    def _apply_adjustments(self, adjustments: List[Dict]):
        """Apply adjustments to settings file."""

        # Reload current settings
        self._load_current_settings()

        for adj in adjustments:
            setting = adj["setting"]
            new_value = adj["new_value"]

            # Skip non-config adjustments (warnings, disabled instruments)
            if setting.startswith("instrument_disabled") or setting.startswith("session_"):
                # Log these as recommendations
                self._log_adjustment(adj)
                continue

            # Apply to config
            if "." in setting:
                parts = setting.split(".")
                target = self.current_settings
                for part in parts[:-1]:
                    if part not in target:
                        target[part] = {}
                    target = target[part]
                target[parts[-1]] = new_value
            else:
                self.current_settings[setting] = new_value

            # Log adjustment
            self._log_adjustment(adj)
            logger.info(f"AUTO-TUNED: {setting} = {new_value} ({adj['reason']})")

        # Save updated config
        config_path = Path("settings/auto_trading.json")
        with open(config_path, "w") as f:
            json.dump(self.current_settings, f, indent=2)

        logger.info(f"Applied {len(adjustments)} setting adjustments")

    def _log_adjustment(self, adjustment: Dict):
        """Log adjustment to database."""
        with db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO setting_adjustments
                (setting_name, old_value, new_value, reason, trades_before, win_rate_before)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                adjustment["setting"],
                str(adjustment.get("old_value")),
                str(adjustment["new_value"]),
                adjustment["reason"],
                0,  # TODO: track trades
                0   # TODO: track win rate
            ))

    def get_adjustment_history(self, limit: int = 20) -> List[Dict]:
        """Get history of setting adjustments."""
        with db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT setting_name, old_value, new_value, reason, created_at
                FROM setting_adjustments
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            return [
                {
                    "setting": row[0],
                    "old_value": row[1],
                    "new_value": row[2],
                    "reason": row[3],
                    "timestamp": row[4]
                }
                for row in cursor.fetchall()
            ]

    def get_recommendations(self) -> List[str]:
        """Get current recommendations based on analysis."""
        recommendations = []

        performance = self._get_performance_analysis()

        if performance["total_trades"] < self.MIN_TRADES_FOR_ADJUSTMENT:
            recommendations.append(
                f"Nedovoljno tradeova za optimizaciju ({performance['total_trades']}/{self.MIN_TRADES_FOR_ADJUSTMENT})"
            )
            return recommendations

        # Check overall health
        if performance["win_rate"] < 0.4:
            recommendations.append(
                f"UPOZORENJE: Nizak win rate ({performance['win_rate']*100:.0f}%) - razmotri pauzu"
            )

        # Check for stop hunts
        if performance["total_trades"] > 0:
            stop_hunt_rate = performance["stopped_out_then_reversed"] / performance["total_trades"]
            if stop_hunt_rate > 0.25:
                recommendations.append(
                    f"Povecaj SL - {stop_hunt_rate*100:.0f}% tradeova stopano pa reversano"
                )

        # Check instruments
        for inst, stats in performance["by_instrument"].items():
            if stats["trades"] >= 3 and stats["win_rate"] < 0.25:
                recommendations.append(f"IZBJEGAVAJ {inst}: {stats['win_rate']*100:.0f}% win rate")
            elif stats["trades"] >= 3 and stats["win_rate"] > 0.65:
                recommendations.append(f"PREFERIRAJ {inst}: {stats['win_rate']*100:.0f}% win rate")

        # Check R:R
        if performance["reached_2r_but_closed_earlier"] > 0:
            rate = performance["reached_2r_but_closed_earlier"] / performance["total_trades"]
            if rate > 0.2:
                recommendations.append(
                    f"Propusteno {rate*100:.0f}% 2R targeta - razmotri trailing stop"
                )

        return recommendations


# Singleton instance
adaptive_settings = AdaptiveSettingsManager()


# Convenience function
def optimize_and_apply() -> Dict[str, Any]:
    """Run optimization and apply adjustments."""
    return adaptive_settings.analyze_and_optimize()
