"""
Bayesian Confidence Calibration using Platt Scaling.

Problem: Raw confidence scores (82-92%) don't match actual win rate (5.1%).
Solution: Platt Scaling maps raw scores to calibrated probabilities.

Formula: P(win) = 1 / (1 + exp(-(A * raw_score + B)))

Where A, B are fitted from historical trade outcomes via logistic regression.
Brier score < 0.25 indicates good calibration.
"""

import math
from datetime import datetime
from typing import Optional

from src.utils.logger import logger


class ConfidenceCalibrator:
    """Platt Scaling calibration of confidence scores."""

    def __init__(self, db):
        self.db = db
        self.param_a = -1.0  # Default (no scaling)
        self.param_b = 0.0
        self.is_fitted = False
        self.min_trades_to_fit = 30
        self.refit_interval = 50  # Refit every 50 new trades
        self._last_trade_count = 0
        self._load_params()

    def calibrate(self, raw_confidence: int) -> int:
        """
        Apply Platt Scaling to raw confidence.

        Args:
            raw_confidence: Raw confidence score 0-100

        Returns:
            Calibrated confidence score 0-100
        """
        if not self.is_fitted:
            return raw_confidence

        # Normalize to 0-1 range
        x = raw_confidence / 100.0

        # Platt Scaling: P(win) = 1 / (1 + exp(-(A*x + B)))
        z = self.param_a * x + self.param_b
        # Clamp to avoid overflow
        z = max(-20.0, min(20.0, z))
        calibrated = 1.0 / (1.0 + math.exp(-z))

        # Convert back to 0-100 int
        return max(0, min(100, int(round(calibrated * 100))))

    def fit(self) -> dict:
        """
        Fit A, B parameters on historical closed auto trades.

        Uses gradient descent to minimize log-loss (cross-entropy).

        Returns:
            Dict with fit metrics (training_trades, brier_score, etc.)
        """
        # Get closed auto trades with confidence scores
        trades = self._get_training_data()

        if len(trades) < self.min_trades_to_fit:
            logger.info(
                f"Calibrator: Need {self.min_trades_to_fit} trades, "
                f"have {len(trades)}. Skipping fit."
            )
            return {
                "fitted": False,
                "reason": f"Need {self.min_trades_to_fit} trades, have {len(trades)}",
                "training_trades": len(trades),
            }

        # Extract (raw_confidence, outcome) pairs
        X = []  # normalized confidence (0-1)
        Y = []  # outcome (1=win, 0=loss)
        for t in trades:
            conf = t.get("confidence_score", 50)
            pnl = t.get("pnl", 0) or 0
            X.append(conf / 100.0)
            Y.append(1 if pnl > 0 else 0)

        # Try scipy first, fall back to manual gradient descent
        try:
            a, b = self._fit_scipy(X, Y)
        except Exception:
            a, b = self._fit_gradient_descent(X, Y)

        # Calculate Brier score for quality assessment
        brier = self._brier_score(X, Y, a, b)
        win_rate = sum(Y) / len(Y)

        # Save params
        self.param_a = a
        self.param_b = b
        self.is_fitted = True
        self._last_trade_count = len(trades)
        self._save_params(a, b, len(trades), win_rate, brier)

        logger.info(
            f"Calibrator fitted: A={a:.4f}, B={b:.4f}, "
            f"Brier={brier:.4f}, trades={len(trades)}, WR={win_rate:.1%}"
        )

        return {
            "fitted": True,
            "param_a": a,
            "param_b": b,
            "training_trades": len(trades),
            "training_win_rate": round(win_rate * 100, 1),
            "brier_score": round(brier, 4),
        }

    def should_refit(self) -> bool:
        """Check if we need to refit (every refit_interval new trades)."""
        current_count = self._count_closed_trades()
        return current_count - self._last_trade_count >= self.refit_interval

    def get_stats(self) -> dict:
        """Return calibration statistics."""
        return {
            "is_fitted": self.is_fitted,
            "param_a": round(self.param_a, 4),
            "param_b": round(self.param_b, 4),
            "last_trade_count": self._last_trade_count,
            "min_trades_to_fit": self.min_trades_to_fit,
            "refit_interval": self.refit_interval,
        }

    # === Private methods ===

    def _fit_scipy(self, X, Y):
        """Fit using scipy.optimize.minimize (L-BFGS-B)."""
        from scipy.optimize import minimize

        def neg_log_likelihood(params):
            a, b = params
            loss = 0.0
            for x, y in zip(X, Y):
                z = a * x + b
                z = max(-20.0, min(20.0, z))
                p = 1.0 / (1.0 + math.exp(-z))
                p = max(1e-7, min(1 - 1e-7, p))
                loss -= y * math.log(p) + (1 - y) * math.log(1 - p)
            return loss / len(X)

        result = minimize(
            neg_log_likelihood,
            x0=[0.0, 0.0],
            method="L-BFGS-B",
            bounds=[(-20, 20), (-20, 20)],
        )
        return result.x[0], result.x[1]

    def _fit_gradient_descent(self, X, Y, lr=0.1, epochs=1000):
        """Manual gradient descent fallback when scipy unavailable."""
        a, b = 0.0, 0.0

        for _ in range(epochs):
            grad_a, grad_b = 0.0, 0.0
            for x, y in zip(X, Y):
                z = a * x + b
                z = max(-20.0, min(20.0, z))
                p = 1.0 / (1.0 + math.exp(-z))
                err = p - y
                grad_a += err * x
                grad_b += err

            grad_a /= len(X)
            grad_b /= len(X)

            a -= lr * grad_a
            b -= lr * grad_b

        return a, b

    def _brier_score(self, X, Y, a, b) -> float:
        """Calculate Brier score (lower is better, <0.25 is good)."""
        total = 0.0
        for x, y in zip(X, Y):
            z = a * x + b
            z = max(-20.0, min(20.0, z))
            p = 1.0 / (1.0 + math.exp(-z))
            total += (p - y) ** 2
        return total / len(X)

    def _get_training_data(self) -> list:
        """Get closed auto trades with confidence scores."""
        with self.db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT confidence_score, pnl
                FROM trades
                WHERE status = 'CLOSED'
                AND confidence_score IS NOT NULL
                AND pnl IS NOT NULL
                ORDER BY closed_at ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def _count_closed_trades(self) -> int:
        """Count total closed trades with confidence scores."""
        with self.db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM trades
                WHERE status = 'CLOSED'
                AND confidence_score IS NOT NULL
                AND pnl IS NOT NULL
            """)
            return cursor.fetchone()[0]

    def _save_params(self, a, b, trades, win_rate, brier):
        """Save fitted parameters to DB."""
        with self.db._connection() as conn:
            cursor = conn.cursor()
            # Deactivate old params
            cursor.execute(
                "UPDATE calibration_params SET active = 0 WHERE active = 1"
            )
            # Insert new
            cursor.execute("""
                INSERT INTO calibration_params (
                    timestamp, param_a, param_b,
                    training_trades, training_win_rate, brier_score, active
                ) VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (
                datetime.now().isoformat(),
                a, b, trades, win_rate, brier
            ))

    def _load_params(self):
        """Load active parameters from DB."""
        try:
            with self.db._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT param_a, param_b, training_trades
                    FROM calibration_params
                    WHERE active = 1
                    ORDER BY id DESC LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    self.param_a = row["param_a"]
                    self.param_b = row["param_b"]
                    self._last_trade_count = row["training_trades"]
                    self.is_fitted = True
                    logger.info(
                        f"Calibrator loaded: A={self.param_a:.4f}, B={self.param_b:.4f}"
                    )
        except Exception:
            # Table might not exist yet
            pass
