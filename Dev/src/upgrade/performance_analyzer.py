"""
Performance Analyzer for AI Trader Self-Upgrade System.

Analyzes recent trading performance to identify losing patterns
and proposes new filters to the AI for generation.

Usage:
    from src.upgrade.performance_analyzer import PerformanceAnalyzer

    analyzer = PerformanceAnalyzer()
    patterns = analyzer.analyze_recent_performance(days=7)
    proposals = analyzer.generate_filter_proposals(patterns)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json

from src.utils.database import db
from src.utils.logger import logger


@dataclass
class LosingPattern:
    """A pattern identified in losing trades."""
    pattern_type: str  # 'instrument', 'session', 'regime', 'direction', 'combined'
    pattern_key: str   # e.g., "EUR_USD", "london", "TRENDING_SHORT"
    total_trades: int
    losing_trades: int
    total_loss: float
    avg_loss: float
    win_rate: float
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def severity(self) -> str:
        """Categorize pattern severity."""
        if self.win_rate < 20 and self.losing_trades >= 5:
            return "CRITICAL"
        elif self.win_rate < 35 and self.losing_trades >= 3:
            return "HIGH"
        elif self.win_rate < 45:
            return "MEDIUM"
        return "LOW"


@dataclass
class FilterProposal:
    """A proposed filter based on pattern analysis."""
    proposal_id: str
    pattern: LosingPattern
    filter_name: str
    filter_description: str
    filter_logic: str  # Human-readable logic description
    expected_impact: Dict[str, Any] = field(default_factory=dict)
    ai_prompt: str = ""  # Prompt to send to Claude for code generation


class PerformanceAnalyzer:
    """
    Analyzes trading performance to identify patterns for improvement.

    Identifies:
    - Losing instruments (specific pairs that consistently lose)
    - Losing sessions (time periods with poor performance)
    - Losing regimes (market conditions with poor performance)
    - Losing combinations (e.g., EUR_USD + london + TRENDING)
    """

    # Minimum trades needed to identify a pattern
    MIN_TRADES_FOR_PATTERN = 5
    MIN_LOSS_RATE_FOR_CONCERN = 0.55  # 55% loss rate

    def __init__(self):
        self._patterns: List[LosingPattern] = []

    def analyze_recent_performance(self, days: int = 7) -> List[LosingPattern]:
        """
        Analyze recent trades to identify losing patterns.

        Args:
            days: Number of days to analyze

        Returns:
            List of identified losing patterns
        """
        self._patterns = []

        # Get recent closed trades
        cutoff = datetime.now() - timedelta(days=days)

        trades = self._get_recent_trades(cutoff)
        if len(trades) < self.MIN_TRADES_FOR_PATTERN:
            logger.info(f"Not enough trades for analysis ({len(trades)} < {self.MIN_TRADES_FOR_PATTERN})")
            return []

        # Analyze by different dimensions
        self._analyze_by_instrument(trades)
        self._analyze_by_session(trades)
        self._analyze_by_regime(trades)
        self._analyze_by_direction(trades)
        self._analyze_combined_patterns(trades)

        # Sort by severity and loss amount
        self._patterns.sort(
            key=lambda p: (
                0 if p.severity == "CRITICAL" else 1 if p.severity == "HIGH" else 2,
                -abs(p.total_loss)
            )
        )

        logger.info(f"Performance analysis complete: {len(self._patterns)} patterns identified")
        return self._patterns

    def _get_recent_trades(self, cutoff: datetime) -> List[Dict]:
        """Get recent closed trades from database."""
        try:
            with db._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT
                        t.trade_id,
                        t.instrument,
                        t.direction,
                        t.pnl,
                        t.confidence_score,
                        t.closed_at,
                        t.close_reason,
                        r.regime,
                        r.regime_strength,
                        strftime('%H', t.timestamp) as hour
                    FROM trades t
                    LEFT JOIN market_regimes r ON t.trade_id = r.trade_id
                    WHERE t.status = 'CLOSED'
                    AND t.closed_at >= ?
                    AND t.pnl IS NOT NULL
                    ORDER BY t.closed_at DESC
                """, (cutoff.isoformat(),))

                trades = []
                for row in cursor.fetchall():
                    trade = dict(row)
                    # Determine session from hour
                    hour = int(trade.get("hour", 12))
                    trade["session"] = self._hour_to_session(hour)
                    trade["is_loss"] = (trade.get("pnl", 0) or 0) < 0
                    trades.append(trade)

                return trades

        except Exception as e:
            logger.error(f"Failed to get recent trades: {e}")
            return []

    def _hour_to_session(self, hour: int) -> str:
        """Convert UTC hour to trading session."""
        if 7 <= hour < 16:
            return "london"
        elif 12 <= hour < 21:
            return "newyork"
        elif 0 <= hour < 9:
            return "tokyo"
        else:
            return "sydney"

    def _analyze_by_instrument(self, trades: List[Dict]) -> None:
        """Find instruments with poor performance."""
        by_instrument = defaultdict(list)
        for t in trades:
            by_instrument[t.get("instrument", "UNKNOWN")].append(t)

        for instrument, instrument_trades in by_instrument.items():
            if len(instrument_trades) < self.MIN_TRADES_FOR_PATTERN:
                continue

            losses = [t for t in instrument_trades if t["is_loss"]]
            if len(losses) / len(instrument_trades) >= self.MIN_LOSS_RATE_FOR_CONCERN:
                total_loss = sum(t.get("pnl", 0) or 0 for t in losses)

                self._patterns.append(LosingPattern(
                    pattern_type="instrument",
                    pattern_key=instrument,
                    total_trades=len(instrument_trades),
                    losing_trades=len(losses),
                    total_loss=total_loss,
                    avg_loss=total_loss / len(losses) if losses else 0,
                    win_rate=100 * (1 - len(losses) / len(instrument_trades)),
                    details={
                        "avg_confidence": sum(t.get("confidence_score", 0) or 0 for t in losses) / len(losses) if losses else 0
                    }
                ))

    def _analyze_by_session(self, trades: List[Dict]) -> None:
        """Find trading sessions with poor performance."""
        by_session = defaultdict(list)
        for t in trades:
            by_session[t.get("session", "unknown")].append(t)

        for session, session_trades in by_session.items():
            if len(session_trades) < self.MIN_TRADES_FOR_PATTERN:
                continue

            losses = [t for t in session_trades if t["is_loss"]]
            if len(losses) / len(session_trades) >= self.MIN_LOSS_RATE_FOR_CONCERN:
                total_loss = sum(t.get("pnl", 0) or 0 for t in losses)

                self._patterns.append(LosingPattern(
                    pattern_type="session",
                    pattern_key=session,
                    total_trades=len(session_trades),
                    losing_trades=len(losses),
                    total_loss=total_loss,
                    avg_loss=total_loss / len(losses) if losses else 0,
                    win_rate=100 * (1 - len(losses) / len(session_trades)),
                    details={
                        "instruments_affected": list(set(t.get("instrument") for t in losses))
                    }
                ))

    def _analyze_by_regime(self, trades: List[Dict]) -> None:
        """Find market regimes with poor performance."""
        by_regime = defaultdict(list)
        for t in trades:
            regime = t.get("regime") or "UNKNOWN"
            by_regime[regime].append(t)

        for regime, regime_trades in by_regime.items():
            if len(regime_trades) < self.MIN_TRADES_FOR_PATTERN:
                continue

            losses = [t for t in regime_trades if t["is_loss"]]
            if len(losses) / len(regime_trades) >= self.MIN_LOSS_RATE_FOR_CONCERN:
                total_loss = sum(t.get("pnl", 0) or 0 for t in losses)

                self._patterns.append(LosingPattern(
                    pattern_type="regime",
                    pattern_key=regime,
                    total_trades=len(regime_trades),
                    losing_trades=len(losses),
                    total_loss=total_loss,
                    avg_loss=total_loss / len(losses) if losses else 0,
                    win_rate=100 * (1 - len(losses) / len(regime_trades)),
                    details={
                        "avg_regime_strength": sum(t.get("regime_strength", 0) or 0 for t in losses) / len(losses) if losses else 0
                    }
                ))

    def _analyze_by_direction(self, trades: List[Dict]) -> None:
        """Find directions with poor performance."""
        by_direction = defaultdict(list)
        for t in trades:
            by_direction[t.get("direction", "UNKNOWN")].append(t)

        for direction, direction_trades in by_direction.items():
            if len(direction_trades) < self.MIN_TRADES_FOR_PATTERN:
                continue

            losses = [t for t in direction_trades if t["is_loss"]]
            if len(losses) / len(direction_trades) >= self.MIN_LOSS_RATE_FOR_CONCERN:
                total_loss = sum(t.get("pnl", 0) or 0 for t in losses)

                self._patterns.append(LosingPattern(
                    pattern_type="direction",
                    pattern_key=direction,
                    total_trades=len(direction_trades),
                    losing_trades=len(losses),
                    total_loss=total_loss,
                    avg_loss=total_loss / len(losses) if losses else 0,
                    win_rate=100 * (1 - len(losses) / len(direction_trades))
                ))

    def _analyze_combined_patterns(self, trades: List[Dict]) -> None:
        """Find combined patterns (e.g., instrument + session + regime)."""
        # Instrument + Session
        by_instr_session = defaultdict(list)
        for t in trades:
            key = f"{t.get('instrument', '')}_{t.get('session', '')}"
            by_instr_session[key].append(t)

        for key, combo_trades in by_instr_session.items():
            if len(combo_trades) < 3:  # Lower threshold for combinations
                continue

            losses = [t for t in combo_trades if t["is_loss"]]
            if len(losses) >= 3 and len(losses) / len(combo_trades) >= 0.65:
                total_loss = sum(t.get("pnl", 0) or 0 for t in losses)
                parts = key.split("_")

                self._patterns.append(LosingPattern(
                    pattern_type="combined",
                    pattern_key=key,
                    total_trades=len(combo_trades),
                    losing_trades=len(losses),
                    total_loss=total_loss,
                    avg_loss=total_loss / len(losses) if losses else 0,
                    win_rate=100 * (1 - len(losses) / len(combo_trades)),
                    details={
                        "instrument": parts[0] if len(parts) > 0 else "",
                        "session": parts[1] if len(parts) > 1 else ""
                    }
                ))

        # Instrument + Direction
        by_instr_dir = defaultdict(list)
        for t in trades:
            key = f"{t.get('instrument', '')}_{t.get('direction', '')}"
            by_instr_dir[key].append(t)

        for key, combo_trades in by_instr_dir.items():
            if len(combo_trades) < 3:
                continue

            losses = [t for t in combo_trades if t["is_loss"]]
            if len(losses) >= 3 and len(losses) / len(combo_trades) >= 0.65:
                total_loss = sum(t.get("pnl", 0) or 0 for t in losses)
                parts = key.split("_")

                self._patterns.append(LosingPattern(
                    pattern_type="combined",
                    pattern_key=key,
                    total_trades=len(combo_trades),
                    losing_trades=len(losses),
                    total_loss=total_loss,
                    avg_loss=total_loss / len(losses) if losses else 0,
                    win_rate=100 * (1 - len(losses) / len(combo_trades)),
                    details={
                        "instrument": parts[0] if len(parts) > 0 else "",
                        "direction": parts[1] if len(parts) > 1 else ""
                    }
                ))

    def generate_filter_proposals(
        self,
        patterns: List[LosingPattern],
        max_proposals: int = 3
    ) -> List[FilterProposal]:
        """
        Generate filter proposals based on identified patterns.

        Args:
            patterns: List of losing patterns from analysis
            max_proposals: Maximum number of proposals to generate

        Returns:
            List of filter proposals ready for AI code generation
        """
        proposals = []

        for pattern in patterns[:max_proposals]:
            if pattern.severity in ["CRITICAL", "HIGH"]:
                proposal = self._create_proposal_for_pattern(pattern)
                if proposal:
                    proposals.append(proposal)

        return proposals

    def _create_proposal_for_pattern(self, pattern: LosingPattern) -> Optional[FilterProposal]:
        """Create a filter proposal for a specific pattern."""
        proposal_id = f"proposal_{pattern.pattern_type}_{pattern.pattern_key}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if pattern.pattern_type == "instrument":
            return FilterProposal(
                proposal_id=proposal_id,
                pattern=pattern,
                filter_name=f"block_{pattern.pattern_key.lower()}_filter",
                filter_description=f"Temporarily block trading on {pattern.pattern_key} due to {pattern.losing_trades} losses (win rate: {pattern.win_rate:.1f}%)",
                filter_logic=f"Block all signals for instrument == '{pattern.pattern_key}'",
                expected_impact={
                    "signals_blocked_estimate": pattern.total_trades,
                    "loss_prevented_estimate": abs(pattern.total_loss)
                },
                ai_prompt=self._build_instrument_filter_prompt(pattern)
            )

        elif pattern.pattern_type == "session":
            return FilterProposal(
                proposal_id=proposal_id,
                pattern=pattern,
                filter_name=f"block_{pattern.pattern_key}_session_filter",
                filter_description=f"Block trading during {pattern.pattern_key} session due to poor performance",
                filter_logic=f"Block signals when session == '{pattern.pattern_key}'",
                expected_impact={
                    "signals_blocked_estimate": pattern.total_trades,
                    "loss_prevented_estimate": abs(pattern.total_loss)
                },
                ai_prompt=self._build_session_filter_prompt(pattern)
            )

        elif pattern.pattern_type == "regime":
            return FilterProposal(
                proposal_id=proposal_id,
                pattern=pattern,
                filter_name=f"block_{pattern.pattern_key.lower()}_regime_filter",
                filter_description=f"Block trading in {pattern.pattern_key} regime due to poor performance",
                filter_logic=f"Block signals when market_regime == '{pattern.pattern_key}'",
                expected_impact={
                    "signals_blocked_estimate": pattern.total_trades,
                    "loss_prevented_estimate": abs(pattern.total_loss)
                },
                ai_prompt=self._build_regime_filter_prompt(pattern)
            )

        elif pattern.pattern_type == "combined":
            return FilterProposal(
                proposal_id=proposal_id,
                pattern=pattern,
                filter_name=f"block_combined_{pattern.pattern_key.lower().replace('_', '_and_')}_filter",
                filter_description=f"Block trading for combination: {pattern.pattern_key}",
                filter_logic=f"Block signals matching the combination pattern",
                expected_impact={
                    "signals_blocked_estimate": pattern.total_trades,
                    "loss_prevented_estimate": abs(pattern.total_loss)
                },
                ai_prompt=self._build_combined_filter_prompt(pattern)
            )

        return None

    def _build_instrument_filter_prompt(self, pattern: LosingPattern) -> str:
        """Build AI prompt for instrument filter generation."""
        return f"""Generate a Python filter class that blocks trading on {pattern.pattern_key}.

Pattern Analysis:
- Instrument: {pattern.pattern_key}
- Total trades: {pattern.total_trades}
- Losing trades: {pattern.losing_trades}
- Win rate: {pattern.win_rate:.1f}%
- Total loss: {pattern.total_loss:.2f} EUR
- Average loss: {pattern.avg_loss:.2f} EUR

Requirements:
1. Create a class that inherits from BaseFilter
2. The check() method should return FilterResult(passed=False) for {pattern.pattern_key}
3. Include option to re-enable after N wins or time period
4. Follow the BaseFilter interface exactly

The filter should be temporary and include a mechanism to automatically
re-enable trading once conditions improve (e.g., after 5 consecutive wins elsewhere,
or after 24 hours with no activity).
"""

    def _build_session_filter_prompt(self, pattern: LosingPattern) -> str:
        """Build AI prompt for session filter generation."""
        return f"""Generate a Python filter class that blocks trading during {pattern.pattern_key} session.

Pattern Analysis:
- Session: {pattern.pattern_key}
- Total trades: {pattern.total_trades}
- Losing trades: {pattern.losing_trades}
- Win rate: {pattern.win_rate:.1f}%
- Total loss: {pattern.total_loss:.2f} EUR
- Affected instruments: {pattern.details.get('instruments_affected', [])}

Requirements:
1. Create a class that inherits from BaseFilter
2. The check() method should determine current session from timestamp
3. Block signals when current session matches '{pattern.pattern_key}'
4. Include logic to detect session from UTC hour
"""

    def _build_regime_filter_prompt(self, pattern: LosingPattern) -> str:
        """Build AI prompt for regime filter generation."""
        return f"""Generate a Python filter class that blocks trading in {pattern.pattern_key} market regime.

Pattern Analysis:
- Market Regime: {pattern.pattern_key}
- Total trades: {pattern.total_trades}
- Losing trades: {pattern.losing_trades}
- Win rate: {pattern.win_rate:.1f}%
- Total loss: {pattern.total_loss:.2f} EUR
- Average regime strength: {pattern.details.get('avg_regime_strength', 0):.1f}%

Requirements:
1. Create a class that inherits from BaseFilter
2. The check() method should read market_regime from signal_data
3. Block signals when market_regime == '{pattern.pattern_key}'
4. Consider regime strength - maybe only block when strength > 60%
"""

    def _build_combined_filter_prompt(self, pattern: LosingPattern) -> str:
        """Build AI prompt for combined pattern filter generation."""
        details = pattern.details
        conditions = []

        if details.get("instrument"):
            conditions.append(f"instrument == '{details['instrument']}'")
        if details.get("session"):
            conditions.append(f"session == '{details['session']}'")
        if details.get("direction"):
            conditions.append(f"direction == '{details['direction']}'")

        return f"""Generate a Python filter class that blocks the specific combination pattern.

Pattern Analysis:
- Pattern: {pattern.pattern_key}
- Total trades: {pattern.total_trades}
- Losing trades: {pattern.losing_trades}
- Win rate: {pattern.win_rate:.1f}%
- Total loss: {pattern.total_loss:.2f} EUR

Conditions to check (ALL must match to block):
{chr(10).join('- ' + c for c in conditions)}

Requirements:
1. Create a class that inherits from BaseFilter
2. The check() method should verify ALL conditions match
3. Only block when the exact combination is detected
4. Be precise - don't block broader patterns
"""

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get a summary of the latest analysis."""
        critical = [p for p in self._patterns if p.severity == "CRITICAL"]
        high = [p for p in self._patterns if p.severity == "HIGH"]
        medium = [p for p in self._patterns if p.severity == "MEDIUM"]

        total_loss = sum(p.total_loss for p in self._patterns)

        return {
            "total_patterns": len(self._patterns),
            "critical_count": len(critical),
            "high_count": len(high),
            "medium_count": len(medium),
            "total_potential_loss_prevented": abs(total_loss),
            "patterns": [
                {
                    "type": p.pattern_type,
                    "key": p.pattern_key,
                    "severity": p.severity,
                    "win_rate": f"{p.win_rate:.1f}%",
                    "total_loss": f"{p.total_loss:.2f}",
                    "trades": p.total_trades
                }
                for p in self._patterns[:10]  # Top 10
            ]
        }
