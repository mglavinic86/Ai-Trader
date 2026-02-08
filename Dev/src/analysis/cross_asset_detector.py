"""
Cross-Asset Divergence Detection.

Detects institutional activity through correlation anomalies between
correlated instruments. When normally-correlated pairs diverge
significantly, it signals targeted institutional flow.

Example:
  EUR/USD going up while GBP/USD goes down (normally correlated ~0.85)
  → EUR buying is SPECIFIC to EUR, not general USD weakness
  → Stronger signal for EUR/USD LONG

Confidence modifiers: -10 to +15 based on divergence strength.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from src.utils.logger import logger


@dataclass
class DivergenceSignal:
    """Signal of divergence between two instruments."""
    pair1: str
    pair2: str
    divergence_sigma: float
    expected_correlation: float
    current_correlation: float
    implication: str  # "pair1_LONG_preference" / "pair1_SHORT_preference" / "neutral"
    confidence_modifier: int
    reasoning: str

    def to_dict(self) -> dict:
        return {
            "pair1": self.pair1,
            "pair2": self.pair2,
            "divergence_sigma": round(self.divergence_sigma, 2),
            "expected_corr": round(self.expected_correlation, 2),
            "current_corr": round(self.current_correlation, 2),
            "implication": self.implication,
            "confidence_modifier": self.confidence_modifier,
            "reasoning": self.reasoning,
        }


# Known correlations (baselines)
CORRELATION_PAIRS = {
    ("EUR_USD", "GBP_USD"): {"expected": 0.85, "type": "positive"},
    ("EUR_USD", "XAU_USD"): {"expected": 0.40, "type": "positive"},
    ("GBP_USD", "XAU_USD"): {"expected": 0.30, "type": "positive"},
    # BTC has no stable forex correlation, skip
}

DIVERGENCE_THRESHOLD_SIGMA = 1.5  # Min sigma for a signal
CORRELATION_WINDOW = 30  # 30 bars for rolling correlation


class CrossAssetDetector:
    """Detects divergences between correlated instruments."""

    def __init__(self, client, db):
        self.client = client
        self.db = db
        self._correlation_cache: Dict[str, float] = {}
        self._cache_expiry: Optional[datetime] = None
        self.cache_duration_minutes = 30

    def analyze(
        self,
        target_instrument: str,
        target_direction: str,
    ) -> List[DivergenceSignal]:
        """
        Analyze divergences for a target instrument.

        Args:
            target_instrument: The instrument we're considering trading
            target_direction: LONG or SHORT

        Returns:
            List of DivergenceSignal for all correlated pairs
        """
        signals = []

        for (pair1, pair2), config in CORRELATION_PAIRS.items():
            # Check if target is in this pair
            if target_instrument not in (pair1, pair2):
                continue

            other = pair2 if target_instrument == pair1 else pair1

            try:
                # Get candles for both instruments
                target_candles = self._get_candles_cached(target_instrument)
                other_candles = self._get_candles_cached(other)

                if not target_candles or not other_candles:
                    continue

                # Calculate rolling correlation
                current_corr = self._calculate_rolling_correlation(
                    target_candles, other_candles
                )

                if current_corr is None:
                    continue

                expected_corr = config["expected"]

                # Calculate divergence in sigma
                diff = abs(current_corr - expected_corr)
                # Approximate std dev of correlation (~0.15 for forex)
                corr_std = 0.15
                divergence_sigma = diff / corr_std if corr_std > 0 else 0

                if divergence_sigma < DIVERGENCE_THRESHOLD_SIGMA:
                    continue

                # Interpret the divergence
                signal = self._interpret_divergence(
                    target_instrument, other,
                    expected_corr, current_corr,
                    target_direction, divergence_sigma,
                )
                signals.append(signal)

                # Log to DB
                self._log_snapshot(
                    target_instrument, other,
                    current_corr, expected_corr,
                    divergence_sigma, signal.implication,
                )

            except Exception as e:
                logger.warning(f"Cross-asset analysis failed for {target_instrument}/{other}: {e}")

        return signals

    def get_confidence_modifier(
        self,
        instrument: str,
        direction: str,
    ) -> int:
        """
        Get summary confidence modifier from all divergences.

        Max: +15 (strong divergence in favor of trade)
        Min: -10 (divergence against trade)
        """
        try:
            signals = self.analyze(instrument, direction)
        except Exception:
            return 0

        if not signals:
            return 0

        total = sum(s.confidence_modifier for s in signals)
        return max(-10, min(15, total))

    def _calculate_rolling_correlation(
        self,
        candles1: List[Dict],
        candles2: List[Dict],
        window: int = CORRELATION_WINDOW,
    ) -> Optional[float]:
        """Calculate Pearson correlation on close prices."""
        # Align by using the same number of bars
        n = min(len(candles1), len(candles2), window)
        if n < 10:
            return None

        closes1 = [c["close"] for c in candles1[-n:]]
        closes2 = [c["close"] for c in candles2[-n:]]

        # Calculate returns (more stable than raw prices)
        returns1 = [(closes1[i] - closes1[i-1]) / closes1[i-1]
                     for i in range(1, len(closes1))]
        returns2 = [(closes2[i] - closes2[i-1]) / closes2[i-1]
                     for i in range(1, len(closes2))]

        if len(returns1) < 5:
            return None

        # Pearson correlation
        n_r = len(returns1)
        mean1 = sum(returns1) / n_r
        mean2 = sum(returns2) / n_r

        cov = sum((r1 - mean1) * (r2 - mean2) for r1, r2 in zip(returns1, returns2)) / n_r
        std1 = math.sqrt(sum((r - mean1) ** 2 for r in returns1) / n_r)
        std2 = math.sqrt(sum((r - mean2) ** 2 for r in returns2) / n_r)

        if std1 == 0 or std2 == 0:
            return None

        return cov / (std1 * std2)

    def _interpret_divergence(
        self,
        target: str,
        other: str,
        expected_corr: float,
        current_corr: float,
        target_direction: str,
        divergence_sigma: float,
    ) -> DivergenceSignal:
        """
        Interpret what a divergence means for the target instrument.

        Logic:
        - Positive correlation dropping → one instrument diverging
        - If target is going UP while correlated peer is DOWN → specific buying
        - If both going same way (normal correlation) → general market move
        """
        corr_drop = expected_corr - current_corr

        # Determine implication
        if corr_drop > 0:
            # Correlation dropped (diverging)
            if target_direction == "LONG":
                # Target going long while pair diverges → specific buying
                implication = f"{target}_LONG_preference"
                modifier = min(15, int(divergence_sigma * 5))
                reasoning = (
                    f"Correlation with {other} dropped from {expected_corr:.2f} to {current_corr:.2f} "
                    f"({divergence_sigma:.1f}σ). Suggests targeted {target} buying, not general move."
                )
            else:
                # Target going short while pair diverges
                implication = f"{target}_SHORT_preference"
                modifier = min(15, int(divergence_sigma * 5))
                reasoning = (
                    f"Correlation with {other} dropped from {expected_corr:.2f} to {current_corr:.2f} "
                    f"({divergence_sigma:.1f}σ). Suggests targeted {target} selling."
                )
        else:
            # Correlation increased or reversed
            if abs(current_corr) > abs(expected_corr):
                # Stronger than expected correlation
                implication = "neutral"
                modifier = 0
                reasoning = (
                    f"Correlation with {other} at {current_corr:.2f} (expected {expected_corr:.2f}). "
                    f"General market move, no specific edge."
                )
            else:
                # Negative correlation (unusual)
                implication = f"{target}_{target_direction}_preference"
                modifier = min(10, int(divergence_sigma * 3))
                reasoning = (
                    f"Unusual correlation reversal with {other}: {current_corr:.2f} vs expected {expected_corr:.2f}. "
                    f"Strong divergence suggests institutional activity."
                )

        return DivergenceSignal(
            pair1=target,
            pair2=other,
            divergence_sigma=divergence_sigma,
            expected_correlation=expected_corr,
            current_correlation=current_corr,
            implication=implication,
            confidence_modifier=modifier,
            reasoning=reasoning,
        )

    def _get_candles_cached(self, instrument: str) -> Optional[List[Dict]]:
        """Get M5 candles with caching."""
        cache_key = f"candles_{instrument}"
        now = datetime.now(timezone.utc)

        # Check cache
        if (self._cache_expiry and now < self._cache_expiry
                and cache_key in self._correlation_cache):
            return self._correlation_cache[cache_key]

        try:
            candles = self.client.get_candles(instrument, "M5", 50)
            self._correlation_cache[cache_key] = candles
            self._cache_expiry = now + timedelta(minutes=self.cache_duration_minutes)
            return candles
        except Exception as e:
            logger.warning(f"Failed to get candles for {instrument}: {e}")
            return None

    def _log_snapshot(self, pair1, pair2, current_corr, expected_corr,
                      divergence_sigma, implication):
        """Log correlation snapshot to DB."""
        try:
            with self.db._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO correlation_snapshots (
                        timestamp, pair1, pair2,
                        correlation_30bar, expected_correlation,
                        divergence_sigma, implication
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    pair1, pair2,
                    current_corr, expected_corr,
                    divergence_sigma, implication,
                ))
        except Exception as e:
            logger.warning(f"Failed to log correlation snapshot: {e}")
