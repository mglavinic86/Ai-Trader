# Trading Module
from src.trading.oanda_client import OandaClient, OandaError
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
    # OANDA Client
    "OandaClient",
    "OandaError",
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
