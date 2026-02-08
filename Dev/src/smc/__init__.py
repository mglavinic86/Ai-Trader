"""
Smart Money Concepts (SMC) Module.

Institutional price action analysis for trade decisions:
- Market Structure (CHoCH, BOS, swing points)
- Liquidity Analysis (sweep detection, session levels)
- Fair Value Gaps (FVG) and Order Blocks (OB)
- Displacement Detection
- Premium/Discount zones

Usage:
    from src.smc import SMCAnalyzer, SMCAnalysis

    analyzer = SMCAnalyzer()
    result = analyzer.analyze_htf(h4_candles, h1_candles, instrument)
    analysis = analyzer.analyze_ltf(m5_candles, result, instrument)
"""

from src.smc.smc_analyzer import SMCAnalyzer, SMCAnalysis
from src.smc.sequence_tracker import SequenceTracker, SequenceState

__all__ = ["SMCAnalyzer", "SMCAnalysis", "SequenceTracker", "SequenceState"]
