"""
Error Analyzer - Analyzes trade losses and extracts lessons.

Categorizes losses and generates lessons for the RAG system.

Usage:
    from src.analysis.error_analyzer import ErrorAnalyzer

    analyzer = ErrorAnalyzer()
    analysis = analyzer.analyze_loss(trade_data, market_context)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from src.utils.logger import logger
from src.utils.database import db


class ErrorCategory(Enum):
    """Categories of trading errors."""
    OVERCONFIDENT = "OVERCONFIDENT"
    NEWS_IGNORED = "NEWS_IGNORED"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"
    SENTIMENT_MISMATCH = "SENTIMENT_MISMATCH"
    TIMING_WRONG = "TIMING_WRONG"
    SUPPORT_RESISTANCE_FAIL = "SUPPORT_RESISTANCE_FAIL"
    ADVERSARIAL_IGNORED = "ADVERSARIAL_IGNORED"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    UNKNOWN = "UNKNOWN"


@dataclass
class ErrorAnalysis:
    """Result of error analysis."""
    category: ErrorCategory
    root_cause: str
    lesson: str
    severity: str  # LOW, MEDIUM, HIGH
    tags: list[str] = field(default_factory=list)
    should_add_lesson: bool = False
    lesson_text: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "root_cause": self.root_cause,
            "lesson": self.lesson,
            "severity": self.severity,
            "tags": self.tags,
            "should_add_lesson": self.should_add_lesson
        }


# Lesson templates for each category
LESSON_TEMPLATES = {
    ErrorCategory.OVERCONFIDENT: """### [{date}] Overconfidence na {instrument}

**Trade:** {instrument} {direction} @ {entry_price}
**Gubitak:** {pnl_formatted}
**Kategorija:** OVERCONFIDENT

**Sto se dogodilo:**
Confidence score je bio {confidence}%, ali trade je izgubio.
Tehnicki score: {technical_score}%, Sentiment: {sentiment_score}.

**Lekcija:**
Visoki confidence score ne garantira uspjeh. Uvijek provjeri bear case.

**Pravilo:**
Kada confidence > 80%, dodatno provjeri adversarial analizu.
""",

    ErrorCategory.NEWS_IGNORED: """### [{date}] News Impact na {instrument}

**Trade:** {instrument} {direction} @ {entry_price}
**Gubitak:** {pnl_formatted}
**Kategorija:** NEWS_IGNORED

**Sto se dogodilo:**
Cijena je napravila spike veci od 2x ATR ({price_move} pips).
Vjerojatno news event koji nije uzet u obzir.

**Lekcija:**
Provjeri ekonomski kalendar prije svakog tradea.

**Pravilo:**
Ne tradaj 1h prije/nakon high-impact news eventova.
""",

    ErrorCategory.TECHNICAL_FAILURE: """### [{date}] Technical Setup Failure na {instrument}

**Trade:** {instrument} {direction} @ {entry_price}
**Gubitak:** {pnl_formatted}
**Kategorija:** TECHNICAL_FAILURE

**Sto se dogodilo:**
Tehnicki score je bio {technical_score}%, ali setup nije radio.

**Lekcija:**
Tehnicki indikatori sami po sebi nisu dovoljni.

**Pravilo:**
Kombiniraj tehnike s fundamentalnom analizom.
""",

    ErrorCategory.SENTIMENT_MISMATCH: """### [{date}] Sentiment Mismatch na {instrument}

**Trade:** {instrument} {direction} @ {entry_price}
**Gubitak:** {pnl_formatted}
**Kategorija:** SENTIMENT_MISMATCH

**Sto se dogodilo:**
Sentiment je bio {sentiment_direction}, ali cijena je otisla suprotno.

**Lekcija:**
Sentiment moze biti kasni indikator. Ne oslanjaj se samo na njega.

**Pravilo:**
Uvijek provjeri price action uz sentiment.
""",

    ErrorCategory.TIMING_WRONG: """### [{date}] Timing Greska na {instrument}

**Trade:** {instrument} {direction} @ {entry_price}
**Gubitak:** {pnl_formatted}
**Kategorija:** TIMING_WRONG

**Sto se dogodilo:**
Trade je trajao manje od 1 sat i izgubio.
Vjerojatno prerano ulazenje ili volatilnost.

**Lekcija:**
Strpljenje je kljuc. Cekaj potvrdu prije ulaska.

**Pravilo:**
Ne ulazi u poziciju bez jasne potvrde signala.
""",

    ErrorCategory.ADVERSARIAL_IGNORED: """### [{date}] Adversarial Warning Ignored na {instrument}

**Trade:** {instrument} {direction} @ {entry_price}
**Gubitak:** {pnl_formatted}
**Kategorija:** ADVERSARIAL_IGNORED

**Sto se dogodilo:**
Adversarial adjustment je bio {adv_adjustment}, ali trade je svejedno otvoren.
Bear case je bio {bear_strength}% jak.

**Lekcija:**
Adversarial analiza postoji s razlogom. Slusaj upozorenja!

**Pravilo:**
Ako adversarial adjustment < -15, ne tradaj.
""",

    ErrorCategory.VOLATILITY_SPIKE: """### [{date}] Volatility Spike na {instrument}

**Trade:** {instrument} {direction} @ {entry_price}
**Gubitak:** {pnl_formatted}
**Kategorija:** VOLATILITY_SPIKE

**Sto se dogodilo:**
SL je udaren zbog iznenadnog povecanja volatilnosti.

**Lekcija:**
Volatilnost moze naglo porasti. Postavi sire SL u volatilnim periodima.

**Pravilo:**
Provjeri ATR prije postavljanja SL. SL >= 1.5x ATR.
""",

    ErrorCategory.UNKNOWN: """### [{date}] Nepoznata Greska na {instrument}

**Trade:** {instrument} {direction} @ {entry_price}
**Gubitak:** {pnl_formatted}
**Kategorija:** UNKNOWN

**Sto se dogodilo:**
Razlog gubitka nije jasno identificiran.

**Lekcija:**
Zapisuj vise detalja o market conditions prije tradea.

**Pravilo:**
Uvijek dokumentiraj razlog za ulazak u trade.
"""
}


class ErrorAnalyzer:
    """
    Analyzes trade losses and categorizes errors.

    Uses trade data and market context to determine:
    - Error category
    - Root cause
    - Lesson for RAG
    - Whether to add to lessons.md
    """

    # Thresholds
    HIGH_CONFIDENCE_THRESHOLD = 80
    STRONG_TECHNICAL_THRESHOLD = 60
    NEWS_SPIKE_ATR_MULTIPLIER = 2.0
    SHORT_TRADE_HOURS = 1
    SIGNIFICANT_LOSS_PERCENT = 1.0
    REPEATED_ERROR_THRESHOLD = 2
    REPEATED_ERROR_DAYS = 7

    def __init__(self):
        """Initialize analyzer."""
        pass

    def analyze_loss(
        self,
        trade_data: dict,
        market_context: Optional[dict] = None
    ) -> ErrorAnalysis:
        """
        Analyze a losing trade and categorize the error.

        Args:
            trade_data: Trade details from database
                - trade_id, instrument, direction, entry_price, exit_price
                - pnl, pnl_percent, confidence_score
                - bull_case, bear_case, sentiment_score
                - timestamp, closed_at
            market_context: Optional market data at time of trade
                - atr: Average True Range
                - price_move_pips: How much price moved against us
                - technical_score: Original technical score
                - adversarial_adjustment: Adversarial adjustment

        Returns:
            ErrorAnalysis with category and lesson
        """
        if market_context is None:
            market_context = {}

        # Extract trade info
        instrument = trade_data.get("instrument", "UNKNOWN")
        direction = trade_data.get("direction", "UNKNOWN")
        confidence = trade_data.get("confidence_score", 0)
        pnl = trade_data.get("pnl", 0)
        pnl_percent = trade_data.get("pnl_percent", 0)
        sentiment_score = trade_data.get("sentiment_score", 0)

        # Market context
        technical_score = market_context.get("technical_score", 0)
        adv_adjustment = market_context.get("adversarial_adjustment", 0)
        price_move = market_context.get("price_move_pips", 0)
        atr = market_context.get("atr", 0)

        # Calculate trade duration
        trade_duration = self._calculate_duration(trade_data)

        # Determine category
        category = self._categorize_error(
            confidence=confidence,
            technical_score=technical_score,
            sentiment_score=sentiment_score,
            adv_adjustment=adv_adjustment,
            price_move=price_move,
            atr=atr,
            trade_duration=trade_duration,
            direction=direction
        )

        # Generate root cause
        root_cause = self._generate_root_cause(
            category, trade_data, market_context
        )

        # Generate short lesson
        lesson = self._generate_short_lesson(category)

        # Determine severity
        severity = self._determine_severity(pnl_percent)

        # Generate tags
        tags = self._generate_tags(category, trade_data, market_context)

        # Determine if lesson should be added to lessons.md
        should_add = self._should_add_lesson(
            pnl_percent=pnl_percent,
            confidence=confidence,
            category=category,
            instrument=instrument
        )

        # Generate full lesson text if needed
        lesson_text = None
        if should_add:
            lesson_text = self._generate_full_lesson(
                category, trade_data, market_context
            )

        logger.info(
            f"Error analyzed: {instrument} - {category.value} "
            f"(severity={severity}, add_lesson={should_add})"
        )

        return ErrorAnalysis(
            category=category,
            root_cause=root_cause,
            lesson=lesson,
            severity=severity,
            tags=tags,
            should_add_lesson=should_add,
            lesson_text=lesson_text
        )

    def _categorize_error(
        self,
        confidence: int,
        technical_score: int,
        sentiment_score: float,
        adv_adjustment: int,
        price_move: float,
        atr: float,
        trade_duration: float,
        direction: str
    ) -> ErrorCategory:
        """Determine the error category based on trade characteristics."""

        # Check for news spike (price move > 2x ATR)
        if atr > 0 and price_move > (atr * self.NEWS_SPIKE_ATR_MULTIPLIER):
            return ErrorCategory.NEWS_IGNORED

        # Check for overconfidence
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return ErrorCategory.OVERCONFIDENT

        # Check for adversarial ignored
        if adv_adjustment < -10:
            return ErrorCategory.ADVERSARIAL_IGNORED

        # Check for technical failure
        if technical_score >= self.STRONG_TECHNICAL_THRESHOLD:
            return ErrorCategory.TECHNICAL_FAILURE

        # Check for sentiment mismatch
        if sentiment_score != 0:
            sentiment_direction = "bullish" if sentiment_score > 0 else "bearish"
            trade_direction = "bullish" if direction == "LONG" else "bearish"
            if sentiment_direction != trade_direction:
                return ErrorCategory.SENTIMENT_MISMATCH

        # Check for timing issue
        if trade_duration < self.SHORT_TRADE_HOURS:
            return ErrorCategory.TIMING_WRONG

        # Check for volatility spike (SL hit)
        if atr > 0:
            return ErrorCategory.VOLATILITY_SPIKE

        return ErrorCategory.UNKNOWN

    def _calculate_duration(self, trade_data: dict) -> float:
        """Calculate trade duration in hours."""
        try:
            opened = trade_data.get("timestamp", "")
            closed = trade_data.get("closed_at", "")

            if not opened or not closed:
                return 0

            # Parse ISO format dates
            open_dt = datetime.fromisoformat(opened.replace("Z", "+00:00"))
            close_dt = datetime.fromisoformat(closed.replace("Z", "+00:00"))

            delta = close_dt - open_dt
            return delta.total_seconds() / 3600  # Convert to hours

        except (ValueError, TypeError):
            return 0

    def _generate_root_cause(
        self,
        category: ErrorCategory,
        trade_data: dict,
        market_context: dict
    ) -> str:
        """Generate root cause description."""
        causes = {
            ErrorCategory.OVERCONFIDENT:
                f"Confidence {trade_data.get('confidence_score', 0)}% prevysok, "
                f"ignoriran bear case",
            ErrorCategory.NEWS_IGNORED:
                f"Veliki price spike ({market_context.get('price_move_pips', 0):.0f} pips), "
                f"moguc news event",
            ErrorCategory.TECHNICAL_FAILURE:
                f"Tehnicki score {market_context.get('technical_score', 0)}% nije se realizirao",
            ErrorCategory.SENTIMENT_MISMATCH:
                f"Sentiment {trade_data.get('sentiment_score', 0):.2f} suprotan od price action",
            ErrorCategory.TIMING_WRONG:
                f"Trade trajao manje od 1h, prerano ulazenje",
            ErrorCategory.SUPPORT_RESISTANCE_FAIL:
                f"S/R razina probijena",
            ErrorCategory.ADVERSARIAL_IGNORED:
                f"Adversarial adjustment {market_context.get('adversarial_adjustment', 0)} ignoriran",
            ErrorCategory.VOLATILITY_SPIKE:
                f"Volatility spike udario SL",
            ErrorCategory.UNKNOWN:
                f"Razlog neodredjen, potrebna dodatna analiza"
        }
        return causes.get(category, "Nepoznat razlog")

    def _generate_short_lesson(self, category: ErrorCategory) -> str:
        """Generate short lesson for database."""
        lessons = {
            ErrorCategory.OVERCONFIDENT:
                "Visoki confidence ne garantira uspjeh. Uvijek provjeri bear case.",
            ErrorCategory.NEWS_IGNORED:
                "Provjeri ekonomski kalendar prije tradea.",
            ErrorCategory.TECHNICAL_FAILURE:
                "Tehnicki indikatori nisu dovoljni sami po sebi.",
            ErrorCategory.SENTIMENT_MISMATCH:
                "Sentiment moze biti kasni indikator.",
            ErrorCategory.TIMING_WRONG:
                "Cekaj potvrdu prije ulaska u poziciju.",
            ErrorCategory.SUPPORT_RESISTANCE_FAIL:
                "S/R razine mogu biti probijene. Postavi SL iza razine.",
            ErrorCategory.ADVERSARIAL_IGNORED:
                "Adversarial warnings postoje s razlogom!",
            ErrorCategory.VOLATILITY_SPIKE:
                "Postavi sire SL u volatilnim periodima.",
            ErrorCategory.UNKNOWN:
                "Dokumentiraj vise detalja za buducu analizu."
        }
        return lessons.get(category, "Neodredjena lekcija.")

    def _determine_severity(self, pnl_percent: float) -> str:
        """Determine error severity based on loss percentage."""
        pnl_abs = abs(pnl_percent) if pnl_percent else 0

        if pnl_abs >= 2.0:
            return "HIGH"
        elif pnl_abs >= 1.0:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_tags(
        self,
        category: ErrorCategory,
        trade_data: dict,
        market_context: dict
    ) -> list[str]:
        """Generate tags for the error."""
        tags = [category.value]

        # Add instrument tag
        instrument = trade_data.get("instrument", "")
        if instrument:
            tags.append(instrument)

        # Add direction tag
        direction = trade_data.get("direction", "")
        if direction:
            tags.append(direction)

        # Add severity based tags
        pnl_percent = trade_data.get("pnl_percent", 0)
        if pnl_percent and abs(pnl_percent) >= 2.0:
            tags.append("HIGH_LOSS")

        # Add confidence tag
        confidence = trade_data.get("confidence_score", 0)
        if confidence >= 80:
            tags.append("HIGH_CONFIDENCE")
        elif confidence < 50:
            tags.append("LOW_CONFIDENCE")

        return tags

    def _should_add_lesson(
        self,
        pnl_percent: float,
        confidence: int,
        category: ErrorCategory,
        instrument: str
    ) -> bool:
        """
        Determine if lesson should be added to lessons.md.

        Criteria:
        - Loss > 1% of account, OR
        - Same category error 2+ times in 7 days, OR
        - Confidence > 70% but still lost
        """
        # Significant loss
        if abs(pnl_percent or 0) >= self.SIGNIFICANT_LOSS_PERCENT:
            logger.debug(f"Adding lesson: significant loss {pnl_percent}%")
            return True

        # High confidence failure
        if confidence >= 70:
            logger.debug(f"Adding lesson: high confidence {confidence}% failed")
            return True

        # Check for repeated errors
        if self._is_repeated_error(category, instrument):
            logger.debug(f"Adding lesson: repeated {category.value} on {instrument}")
            return True

        return False

    def _is_repeated_error(self, category: ErrorCategory, instrument: str) -> bool:
        """Check if this error category has occurred recently."""
        try:
            # Query errors in last 7 days
            recent_errors = db.find_similar_errors(instrument, limit=10)

            # Filter to same category in last 7 days
            cutoff = datetime.now() - timedelta(days=self.REPEATED_ERROR_DAYS)
            count = 0

            for error in recent_errors:
                if error.get("error_category") == category.value:
                    try:
                        error_time = datetime.fromisoformat(
                            error.get("timestamp", "").replace("Z", "+00:00")
                        )
                        if error_time > cutoff:
                            count += 1
                    except (ValueError, TypeError):
                        pass

            return count >= self.REPEATED_ERROR_THRESHOLD

        except Exception as e:
            logger.warning(f"Error checking repeated errors: {e}")
            return False

    def _generate_full_lesson(
        self,
        category: ErrorCategory,
        trade_data: dict,
        market_context: dict
    ) -> str:
        """Generate full lesson text for lessons.md."""
        template = LESSON_TEMPLATES.get(category, LESSON_TEMPLATES[ErrorCategory.UNKNOWN])

        # Format PnL
        pnl = trade_data.get("pnl", 0)
        pnl_percent = trade_data.get("pnl_percent", 0)
        pnl_formatted = f"-${abs(pnl):.2f} ({pnl_percent:.1f}%)" if pnl else "N/A"

        # Format sentiment direction
        sentiment = trade_data.get("sentiment_score", 0)
        sentiment_direction = "bullish" if sentiment > 0 else "bearish" if sentiment < 0 else "neutral"

        # Get values with defaults
        values = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "instrument": trade_data.get("instrument", "UNKNOWN"),
            "direction": trade_data.get("direction", "UNKNOWN"),
            "entry_price": trade_data.get("entry_price", 0),
            "pnl_formatted": pnl_formatted,
            "confidence": trade_data.get("confidence_score", 0),
            "technical_score": market_context.get("technical_score", 0),
            "sentiment_score": sentiment,
            "sentiment_direction": sentiment_direction,
            "price_move": market_context.get("price_move_pips", 0),
            "adv_adjustment": market_context.get("adversarial_adjustment", 0),
            "bear_strength": market_context.get("bear_strength", 0)
        }

        try:
            return template.format(**values)
        except KeyError as e:
            logger.warning(f"Missing template key: {e}")
            return template


def build_lesson_prompt(trade_data: dict, market_context: dict, analysis: ErrorAnalysis) -> str:
    """Build a prompt for LLM to generate an improved lesson."""
    payload = {
        "trade_data": trade_data,
        "market_context": market_context,
        "analysis": analysis.to_dict()
    }
    return (
        "Generate a concise trading lesson in Croatian.\n"
        "Format as markdown with title, what happened, lesson, and rule.\n"
        "Keep it short and actionable.\n"
        f"Context JSON:\n{payload}"
    )


# Convenience function
def analyze_trade_error(trade_data: dict, market_context: dict = None) -> ErrorAnalysis:
    """
    Convenience function to analyze a trade error.

    Args:
        trade_data: Trade details
        market_context: Market context at time of trade

    Returns:
        ErrorAnalysis
    """
    analyzer = ErrorAnalyzer()
    return analyzer.analyze_loss(trade_data, market_context)
