# Trading Module
from src.trading.mt5_client import MT5Client, MT5Error
from src.trading.orders import OrderManager, OrderResult
from src.trading.position_sizer import (
    calculate_position_size,
    calculate_risk_reward,
    PositionSizeResult
)
from src.trading.risk_manager import (
    RiskManager,
    ValidationResult,
    pre_trade_checklist
)

# Lazy import for trade_lifecycle to avoid circular imports
# Use: from src.trading.trade_lifecycle import trade_closed_handler

__all__ = [
    # MT5 Client
    "MT5Client",
    "MT5Error",
    # Orders
    "OrderManager",
    "OrderResult",
    # Position Sizing
    "calculate_position_size",
    "calculate_risk_reward",
    "PositionSizeResult",
    # Risk Management
    "RiskManager",
    "ValidationResult",
    "pre_trade_checklist"
]
