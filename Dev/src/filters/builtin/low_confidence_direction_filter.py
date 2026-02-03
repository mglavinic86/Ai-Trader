"""
Low Confidence Direction Filter - Blocks weak directional signals.

This filter prevents trades where the technical indicators
give conflicting signals about direction.
"""

from src.upgrade.base_filter import BaseFilter, FilterResult


class LowConfidenceDirectionFilter(BaseFilter):
    """
    Blocks signals with conflicting directional indicators.

    Checks that trend, MACD, and RSI all align with the proposed direction.
    """

    def __init__(self, min_alignment_score: int = 2):
        super().__init__(
            name="low_confidence_direction",
            description="Blocks signals with conflicting directional indicators",
            priority=30,
            filter_type="builtin"
        )
        self.min_alignment_score = min_alignment_score

    def check(self, signal_data: dict) -> FilterResult:
        """Check if direction indicators align."""
        direction = signal_data.get("direction", "")
        technical = signal_data.get("technical", {})

        if not direction or not technical:
            return FilterResult(passed=True)

        trend = technical.get("trend", "")
        macd_trend = technical.get("macd_trend", "")
        rsi = technical.get("rsi", 50)

        alignment_score = 0
        misalignments = []

        # Check trend alignment
        if direction == "LONG":
            if trend == "BULLISH":
                alignment_score += 1
            elif trend == "BEARISH":
                misalignments.append(f"Trend={trend}")

            if macd_trend == "BULLISH":
                alignment_score += 1
            elif macd_trend == "BEARISH":
                misalignments.append(f"MACD={macd_trend}")

            # RSI should not be overbought for longs
            if rsi < 70:
                alignment_score += 1
            else:
                misalignments.append(f"RSI={rsi:.0f} (overbought)")

        elif direction == "SHORT":
            if trend == "BEARISH":
                alignment_score += 1
            elif trend == "BULLISH":
                misalignments.append(f"Trend={trend}")

            if macd_trend == "BEARISH":
                alignment_score += 1
            elif macd_trend == "BULLISH":
                misalignments.append(f"MACD={macd_trend}")

            # RSI should not be oversold for shorts
            if rsi > 30:
                alignment_score += 1
            else:
                misalignments.append(f"RSI={rsi:.0f} (oversold)")

        if alignment_score < self.min_alignment_score:
            return FilterResult(
                passed=False,
                reason=f"Direction conflict: {', '.join(misalignments)}",
                details={
                    "direction": direction,
                    "alignment_score": alignment_score,
                    "required_score": self.min_alignment_score,
                    "misalignments": misalignments
                }
            )

        return FilterResult(passed=True)
