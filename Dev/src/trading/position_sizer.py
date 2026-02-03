"""
Position Sizer - Calculates trade size based on confidence-based risk tiers.

Risk Tiers (HARD-CODED):
- Confidence 90-100%: Max 3% risk
- Confidence 70-89%:  Max 2% risk
- Confidence 50-69%:  Max 1% risk
- Confidence < 50%:   NO TRADE

Usage:
    from src.trading.position_sizer import calculate_position_size

    result = calculate_position_size(
        equity=10000,
        confidence=75,
        entry_price=1.0843,
        stop_loss=1.0800,
        instrument="EUR_USD"
    )
"""

from dataclasses import dataclass
from typing import Optional

from src.utils.config import config
from src.utils.logger import logger


@dataclass
class PositionSizeResult:
    """Result of position size calculation."""
    can_trade: bool
    units: int
    risk_percent: float
    risk_amount: float
    risk_tier: str
    pip_distance: float
    pip_value: float
    reason: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "can_trade": self.can_trade,
            "units": self.units,
            "risk_percent": self.risk_percent,
            "risk_amount": self.risk_amount,
            "risk_tier": self.risk_tier,
            "pip_distance": self.pip_distance,
            "pip_value": self.pip_value,
            "reason": self.reason
        }


def get_pip_value(instrument: str) -> float:
    """
    Get pip value for instrument.

    Args:
        instrument: Currency pair or crypto (e.g., "EUR_USD", "BTC_USD")

    Returns:
        Pip value (0.0001 for most, 0.01 for JPY pairs, 1.0 for crypto)
    """
    # Crypto pairs use whole dollar as pip
    if "BTC" in instrument or "ETH" in instrument:
        return 1.0
    # JPY pairs have 2 decimal places
    if "JPY" in instrument:
        return 0.01
    # Standard forex pairs
    return 0.0001


def get_risk_tier(confidence: int) -> tuple[float, str]:
    """
    Get risk tier based on confidence score.

    Args:
        confidence: Score 0-100

    Returns:
        (risk_percent, tier_name)
    """
    if confidence >= 90:
        return config.MAX_RISK_PERCENT_TIER_3, "TIER 3 (High Confidence: 3%)"
    elif confidence >= 70:
        return config.MAX_RISK_PERCENT_TIER_2, "TIER 2 (Good Confidence: 2%)"
    elif confidence >= 50:
        return config.MAX_RISK_PERCENT_TIER_1, "TIER 1 (Moderate Confidence: 1%)"
    else:
        return 0.0, "NO TRADE (Low Confidence)"


def calculate_position_size(
    equity: float,
    confidence: int,
    entry_price: float,
    stop_loss: float,
    instrument: str
) -> PositionSizeResult:
    """
    Calculate position size based on confidence-driven risk tiers.

    This is the CORE risk management function. It ensures:
    1. Risk is limited based on confidence score
    2. Position size is calculated to risk exact amount
    3. No trade if confidence < 50%

    Args:
        equity: Account equity/balance
        confidence: Confidence score (0-100)
        entry_price: Planned entry price
        stop_loss: Planned stop loss price
        instrument: Currency pair (e.g., "EUR_USD")

    Returns:
        PositionSizeResult with all calculation details

    Example:
        >>> result = calculate_position_size(10000, 75, 1.0843, 1.0800, "EUR_USD")
        >>> print(result.units)  # ~4651
        >>> print(result.risk_percent)  # 0.02 (2%)
        >>> print(result.risk_amount)  # 200.0
    """
    # Validate inputs
    if equity <= 0:
        return PositionSizeResult(
            can_trade=False, units=0, risk_percent=0, risk_amount=0,
            risk_tier="ERROR", pip_distance=0, pip_value=0,
            reason="Invalid equity (must be positive)"
        )

    if confidence < 0 or confidence > 100:
        return PositionSizeResult(
            can_trade=False, units=0, risk_percent=0, risk_amount=0,
            risk_tier="ERROR", pip_distance=0, pip_value=0,
            reason="Invalid confidence score (must be 0-100)"
        )

    if entry_price <= 0 or stop_loss <= 0:
        return PositionSizeResult(
            can_trade=False, units=0, risk_percent=0, risk_amount=0,
            risk_tier="ERROR", pip_distance=0, pip_value=0,
            reason="Invalid price (must be positive)"
        )

    # Get risk tier
    risk_percent, risk_tier = get_risk_tier(confidence)

    # Check if confidence is too low
    if confidence < config.MIN_CONFIDENCE_TO_TRADE:
        logger.warning(f"Confidence {confidence}% below minimum {config.MIN_CONFIDENCE_TO_TRADE}%")
        return PositionSizeResult(
            can_trade=False, units=0, risk_percent=0, risk_amount=0,
            risk_tier=risk_tier, pip_distance=0, pip_value=0,
            reason=f"Confidence {confidence}% is below minimum {config.MIN_CONFIDENCE_TO_TRADE}%"
        )

    # Calculate pip value and distance
    pip_val = get_pip_value(instrument)
    price_distance = abs(entry_price - stop_loss)
    pip_distance = price_distance / pip_val

    if pip_distance == 0:
        return PositionSizeResult(
            can_trade=False, units=0, risk_percent=risk_percent, risk_amount=0,
            risk_tier=risk_tier, pip_distance=0, pip_value=pip_val,
            reason="Stop loss is same as entry price"
        )

    # Calculate risk amount and position size
    risk_amount = equity * risk_percent

    # Position size formula:
    # units = risk_amount / (pip_distance * pip_value_per_unit)
    # For most pairs, pip_value_per_unit ≈ pip_val (simplified)
    units = int(risk_amount / (pip_distance * pip_val))

    # MARGIN PROTECTION: Cap position size to prevent "No money" errors
    # Max ~1 standard lot (100,000 units) per trade for manageable risk
    MAX_UNITS_PER_TRADE = 100000
    if units > MAX_UNITS_PER_TRADE:
        logger.warning(f"Position size {units} exceeds max {MAX_UNITS_PER_TRADE}, capping")
        units = MAX_UNITS_PER_TRADE
        # Recalculate actual risk with capped units
        risk_amount = units * pip_distance * pip_val
        risk_percent = risk_amount / equity if equity > 0 else 0

    if units <= 0:
        return PositionSizeResult(
            can_trade=False, units=0, risk_percent=risk_percent, risk_amount=risk_amount,
            risk_tier=risk_tier, pip_distance=pip_distance, pip_value=pip_val,
            reason="Position size too small (SL distance too large for risk amount)"
        )

    logger.info(
        f"Position size calculated: {units} units, "
        f"Risk: {risk_percent*100:.1f}% (${risk_amount:.2f}), "
        f"SL: {pip_distance:.1f} pips"
    )

    return PositionSizeResult(
        can_trade=True,
        units=units,
        risk_percent=risk_percent,
        risk_amount=risk_amount,
        risk_tier=risk_tier,
        pip_distance=pip_distance,
        pip_value=pip_val,
        reason="OK"
    )


def calculate_risk_reward(
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    instrument: str
) -> dict:
    """
    Calculate risk/reward ratio.

    Args:
        entry_price: Entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
        instrument: Currency pair

    Returns:
        Dict with risk, reward, and ratio
    """
    pip_val = get_pip_value(instrument)

    risk_pips = abs(entry_price - stop_loss) / pip_val
    reward_pips = abs(take_profit - entry_price) / pip_val

    if risk_pips == 0:
        ratio = 0
    else:
        ratio = reward_pips / risk_pips

    return {
        "risk_pips": round(risk_pips, 1),
        "reward_pips": round(reward_pips, 1),
        "ratio": round(ratio, 2),
        "ratio_display": f"1:{ratio:.1f}"
    }
