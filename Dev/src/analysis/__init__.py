# Analysis Module
from src.analysis.sentiment import (
    SentimentAnalyzer,
    SentimentResult,
    analyze_sentiment
)
from src.analysis.adversarial import (
    AdversarialEngine,
    AdversarialResult,
    generate_adversarial_analysis
)
from src.analysis.confidence import (
    ConfidenceCalculator,
    ConfidenceResult,
    calculate_confidence
)
from src.analysis.error_analyzer import (
    ErrorAnalyzer,
    ErrorAnalysis,
    ErrorCategory,
    analyze_trade_error
)
from src.analysis.post_trade_analyzer import (
    PostTradeAnalyzer,
    PostTradeAnalysis,
    analyze_closed_trade
)
from src.analysis.news_filter import (
    NewsFilter,
    news_filter,
    auto_refresh_news
)
from src.analysis.news_providers import (
    NewsProviderManager,
    refresh_news_calendar,
    set_finnhub_api_key,
    get_news_manager
)

__all__ = [
    # Sentiment
    "SentimentAnalyzer",
    "SentimentResult",
    "analyze_sentiment",
    # Adversarial
    "AdversarialEngine",
    "AdversarialResult",
    "generate_adversarial_analysis",
    # Confidence
    "ConfidenceCalculator",
    "ConfidenceResult",
    "calculate_confidence",
    # Error Analysis
    "ErrorAnalyzer",
    "ErrorAnalysis",
    "ErrorCategory",
    "analyze_trade_error",
    # Post-Trade Analysis
    "PostTradeAnalyzer",
    "PostTradeAnalysis",
    "analyze_closed_trade",
    # News Filter
    "NewsFilter",
    "news_filter",
    "auto_refresh_news",
    # News Providers
    "NewsProviderManager",
    "refresh_news_calendar",
    "set_finnhub_api_key",
    "get_news_manager"
]
