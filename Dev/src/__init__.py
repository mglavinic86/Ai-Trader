# AI Trader - Source Package
#
# Quick imports for common components:
#   from src import OrderManager, RiskManager, MT5Client
#   from src import calculate_position_size, calculate_confidence

# Trading
from src.trading import (
    MT5Client,
    MT5Error,
    OrderManager,
    OrderResult,
    RiskManager,
    ValidationResult,
    calculate_position_size,
    calculate_risk_reward,
    PositionSizeResult,
    pre_trade_checklist
)

# Analysis
from src.analysis import (
    SentimentAnalyzer,
    SentimentResult,
    analyze_sentiment,
    AdversarialEngine,
    AdversarialResult,
    generate_adversarial_analysis,
    ConfidenceCalculator,
    ConfidenceResult,
    calculate_confidence,
    ErrorAnalyzer,
    analyze_trade_error
)

# Market
from src.market import (
    TechnicalAnalyzer,
    TechnicalAnalysis,
    analyze_candles
)

# Utils
from src.utils import (
    config,
    logger,
    db,
    format_price,
    generate_trade_id
)

__all__ = [
    # Trading
    "MT5Client",
    "MT5Error",
    "OrderManager",
    "OrderResult",
    "RiskManager",
    "ValidationResult",
    "calculate_position_size",
    "calculate_risk_reward",
    "PositionSizeResult",
    "pre_trade_checklist",
    # Analysis
    "SentimentAnalyzer",
    "SentimentResult",
    "analyze_sentiment",
    "AdversarialEngine",
    "AdversarialResult",
    "generate_adversarial_analysis",
    "ConfidenceCalculator",
    "ConfidenceResult",
    "calculate_confidence",
    "ErrorAnalyzer",
    "analyze_trade_error",
    # Market
    "TechnicalAnalyzer",
    "TechnicalAnalysis",
    "analyze_candles",
    # Utils
    "config",
    "logger",
    "db",
    "format_price",
    "generate_trade_id"
]
