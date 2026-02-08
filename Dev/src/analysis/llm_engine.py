"""
LLM Engine - Claude integration for market analysis.

This module uses the system prompt + skills + knowledge base
to produce a natural-language analysis. It is advisory only
and must never execute trades directly.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
import time
from typing import Optional

from src.core.settings_manager import settings_manager
from src.utils.logger import logger

# Lazy import to avoid circular dependency
def _get_learning_engine():
    try:
        from src.analysis.learning_engine import learning_engine
        return learning_engine
    except Exception:
        return None

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except Exception:
    ANTHROPIC_AVAILABLE = False


@dataclass
class LLMAnalysis:
    summary: str
    bias: str
    risk_notes: list[str]
    strategy_notes: list[str]
    recommendation: str
    direction: str
    confidence_adjustment: int = 0
    model: str = ""
    latency_ms: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    skill_used: Optional[str] = None
    knowledge_included: bool = False
    raw: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "bias": self.bias,
            "risk_notes": self.risk_notes,
            "strategy_notes": self.strategy_notes,
            "recommendation": self.recommendation,
            "direction": self.direction,
            "confidence_adjustment": self.confidence_adjustment,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "skill_used": self.skill_used,
            "knowledge_included": self.knowledge_included,
            "raw": self.raw,
        }


class LLMEngine:
    """Claude LLM wrapper for advisory analysis."""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._enabled = settings_manager.get_config("ai.use_llm", True)
        self._model = settings_manager.get_config("ai.model", "claude-opus-4-5-20251101")
        self._temperature = settings_manager.get_config("ai.temperature", 0.3)
        self._max_tokens = settings_manager.get_config("ai.max_tokens", 1024)

        if not ANTHROPIC_AVAILABLE:
            logger.warning("Anthropic SDK not available - LLM disabled")
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY missing - LLM disabled")

    def is_available(self) -> bool:
        return ANTHROPIC_AVAILABLE and bool(self.api_key) and bool(self._enabled)

    def status(self) -> tuple[bool, str]:
        """Return (available, reason)."""
        if not self._enabled:
            return False, "LLM disabled in config"
        if not ANTHROPIC_AVAILABLE:
            return False, "Anthropic SDK not installed"
        if not self.api_key:
            return False, "ANTHROPIC_API_KEY missing"
        return True, "LLM enabled"

    def simple_analyze(self, prompt: str, max_tokens: int = 500, system_prompt: str = None) -> Optional[str]:
        """
        Simple text analysis with Claude.

        Args:
            prompt: The text prompt to analyze
            max_tokens: Maximum tokens in response (default 500)
            system_prompt: Optional system prompt override

        Returns:
            Response text or None if failed
        """
        if not self.is_available():
            return None

        if system_prompt is None:
            system_prompt = "You are a financial analyst. Provide concise, structured analysis."

        try:
            client = Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model=self._model,
                max_tokens=min(max_tokens, self._max_tokens),
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            content = message.content[0].text if message and message.content else ""
            return content.strip() if content else None
        except Exception as e:
            logger.error(f"LLM simple_analyze failed: {e}")
            return None

    def _build_prompt(
        self,
        instrument: str,
        price: dict,
        technical: object,
        sentiment: object,
        adversarial: object,
        rag_errors: list[dict],
        recent_lessons: Optional[str] = None,
        learning_insights: Optional[str] = None
    ) -> str:
        """Build LLM prompt with structured context."""
        rag_summary = []
        for err in rag_errors:
            rag_summary.append({
                "category": err.get("error_category"),
                "root_cause": err.get("root_cause"),
                "lessons": err.get("lessons"),
                "timestamp": err.get("timestamp"),
            })

        context = {
            "instrument": instrument,
            "price": price,
            "technical": technical.to_dict() if hasattr(technical, "to_dict") else {},
            "sentiment": sentiment.to_dict() if hasattr(sentiment, "to_dict") else {},
            "adversarial": adversarial.to_dict() if hasattr(adversarial, "to_dict") else {},
            "rag_errors": rag_summary,
            "recent_lessons": recent_lessons or ""
        }

        # Add learning insights section if available
        learning_section = ""
        if learning_insights:
            learning_section = f"""

=== HISTORICAL LEARNING DATA ===
The following warnings and insights are based on actual past trade performance.
IMPORTANT: Take these seriously - they are derived from real trading history!

{learning_insights}

================================
"""

        return f"""
You are an AI trading assistant. Provide advisory analysis only. Do NOT execute trades.
Use the provided skills and knowledge base.
{learning_section}
CRITICAL RULES:
1. If there are warnings from historical data, you MUST mention them in your analysis
2. If win rate for this setup is below 40%, recommend SKIP unless there's exceptional confluence
3. Adjust your confidence based on the historical adjustment recommendation
4. If "should_trade" is False in insights, your recommendation MUST be SKIP

Return JSON with keys:
summary (string), bias (BULLISH/BEARISH/NEUTRAL), risk_notes (list), strategy_notes (list),
recommendation (TRADE/SKIP), direction (LONG/SHORT/NEUTRAL),
confidence_adjustment (int, -25 to +15).

Context (JSON):
{json.dumps(context, ensure_ascii=True, indent=2)}
""".strip()

    def analyze(
        self,
        instrument: str,
        price: dict,
        technical: object,
        sentiment: object,
        adversarial: object,
        rag_errors: list[dict],
        skill_name: Optional[str] = None,
        skill_content: Optional[str] = None,
        trade_context: Optional[dict] = None
    ) -> Optional[LLMAnalysis]:
        """Run LLM analysis and return structured result."""
        if not self.is_available():
            return None

        system_prompt = settings_manager.get_full_system_prompt()
        recent_lessons = settings_manager.get_knowledge("lessons")
        if recent_lessons and len(recent_lessons) > 2000:
            recent_lessons = recent_lessons[:2000] + "\n... (truncated)"
        knowledge_included = bool(recent_lessons)

        if skill_name and skill_content:
            system_prompt = system_prompt + f"\n\n---\n\n## Skill Focus: {skill_name}\n\n{skill_content}"

        # Get learning insights from historical data
        learning_insights = None
        learning_engine = _get_learning_engine()
        if learning_engine and trade_context:
            try:
                # Determine direction from technical analysis
                direction = "LONG" if hasattr(technical, 'trend') and technical.trend == "BULLISH" else "SHORT"
                if hasattr(technical, 'trend') and technical.trend == "RANGING":
                    direction = "NEUTRAL"

                insights = learning_engine.get_insights_for_trade(
                    instrument=instrument,
                    direction=direction,
                    context=trade_context
                )
                learning_insights = insights.format_for_prompt()
                logger.info(f"Learning insights loaded for {instrument}: adjustment={insights.confidence_adjustment}")
            except Exception as e:
                logger.warning(f"Could not load learning insights: {e}")

        user_prompt = self._build_prompt(
            instrument,
            price,
            technical,
            sentiment,
            adversarial,
            rag_errors,
            recent_lessons=recent_lessons,
            learning_insights=learning_insights
        )

        try:
            start = time.perf_counter()
            client = Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
            usage = getattr(message, "usage", None)
            input_tokens = getattr(usage, "input_tokens", None) if usage else None
            output_tokens = getattr(usage, "output_tokens", None) if usage else None

            content = message.content[0].text if message and message.content else ""
            parsed = None
            try:
                parsed = json.loads(content)
            except Exception:
                parsed = None

            if parsed:
                return LLMAnalysis(
                    summary=str(parsed.get("summary", "")).strip(),
                    bias=str(parsed.get("bias", "NEUTRAL")).strip(),
                    risk_notes=parsed.get("risk_notes", []) or [],
                    strategy_notes=parsed.get("strategy_notes", []) or [],
                    recommendation=str(parsed.get("recommendation", "SKIP")).strip(),
                    direction=str(parsed.get("direction", "NEUTRAL")).strip(),
                    confidence_adjustment=int(parsed.get("confidence_adjustment", 0) or 0),
                    model=self._model,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    skill_used=skill_name,
                    knowledge_included=knowledge_included,
                    raw=content
                )

            return LLMAnalysis(
                summary=content.strip(),
                bias="NEUTRAL",
                risk_notes=[],
                strategy_notes=[],
                recommendation="SKIP",
                direction="NEUTRAL",
                confidence_adjustment=0,
                model=self._model,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                skill_used=skill_name,
                knowledge_included=knowledge_included,
                raw=content
            )

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return None

    def generate_lesson(self, prompt: str) -> Optional[str]:
        """Generate a lesson text from a prompt."""
        if not self.is_available():
            return None

        system_prompt = "You are a trading mentor. Provide concise, actionable lessons in Croatian."

        try:
            client = Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model=self._model,
                max_tokens=min(self._max_tokens, 800),
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            content = message.content[0].text if message and message.content else ""
            return content.strip() if content else None
        except Exception as e:
            logger.error(f"LLM lesson generation failed: {e}")
            return None

    def validate_signal(self, signal_data: dict) -> Optional["SignalValidation"]:
        """
        Validate a trading signal using Claude AI.

        This is the core AI validation layer - Claude decides whether
        to approve or reject each trade signal.

        Args:
            signal_data: Dict containing signal details:
                - instrument: str
                - direction: str (LONG/SHORT)
                - confidence: int
                - entry_price: float
                - stop_loss: float
                - take_profit: float
                - risk_reward: float
                - technical: dict (trend, rsi, macd, atr)
                - sentiment: float
                - bull_case: str
                - bear_case: str

        Returns:
            SignalValidation with decision and reasoning
        """
        if not self.is_available():
            logger.warning("LLM not available for signal validation")
            return None

        # Build concise validation prompt (SMC-based)
        smc_data = signal_data.get('smc', {})
        prompt = f"""You are an AI trading validator using Smart Money Concepts (SMC). Analyze this signal and decide: APPROVE or REJECT.

SIGNAL:
- Instrument: {signal_data.get('instrument')}
- Direction: {signal_data.get('direction')}
- Confidence Score: {signal_data.get('confidence')}%
- Entry: {signal_data.get('entry_price')}
- Stop Loss: {signal_data.get('stop_loss')}
- Take Profit: {signal_data.get('take_profit')}
- Risk:Reward: {signal_data.get('risk_reward', 0):.2f}

SMC ANALYSIS:
- HTF Bias: {smc_data.get('htf_bias', 'N/A')}
- HTF Structure: {smc_data.get('htf_structure', 'N/A')}
- Setup Grade: {smc_data.get('setup_grade', 'N/A')}
- Sweep: {smc_data.get('sweep_detected', 'None')}
- CHoCH: {smc_data.get('ltf_choch', 'None')}
- BOS: {smc_data.get('ltf_bos', 'None')}
- Displacement: {smc_data.get('ltf_displacement', 'None')}
- FVGs: {smc_data.get('fvg_count', 0)}
- Order Blocks: {smc_data.get('ob_count', 0)}
- Premium/Discount: {smc_data.get('premium_discount', 'N/A')}

SENTIMENT: {signal_data.get('sentiment', 0):.2f}

SEQUENCE ANALYSIS (ISI):
- Current Phase: {signal_data.get('sequence_phase_name', 'N/A')} ({signal_data.get('sequence_phase', 'N/A')}/5)
- Raw Confidence: {signal_data.get('raw_confidence', 'N/A')}%
- Calibrated Confidence: {signal_data.get('confidence', 'N/A')}%
- Divergence Modifier: {signal_data.get('divergence_modifier', 0)}

BULL CASE: {signal_data.get('bull_case', 'N/A')[:200]}
BEAR CASE: {signal_data.get('bear_case', 'N/A')[:200]}

VALIDATION RULES (SMC+ISI MODE - institutional sequence intelligence):
1. REJECT if no liquidity sweep detected
2. REJECT if no CHoCH or BOS on LTF
3. REJECT if price is in equilibrium zone (not premium/discount)
4. REJECT if HTF bias is NEUTRAL or opposes LTF direction
5. REJECT if R:R < 3.0
6. REJECT if setup grade is B or lower
7. PREFER Phase 4 (Retracement) entries - OPTIMAL ENTRY POINT
8. REJECT Phase 1 (Accumulation) - no setup yet
9. When in doubt, REJECT - we only want A+ and A setups

Respond with ONLY valid JSON:
{{"decision": "APPROVE" or "REJECT", "reasoning": "1-2 sentence explanation", "confidence_adjustment": -10 to +10}}
"""

        try:
            start = time.perf_counter()
            client = Anthropic(api_key=self.api_key)

            # Use faster model for validation (Haiku) if available, else default
            validation_model = settings_manager.get_config("ai.validation_model", "claude-sonnet-4-20250514")

            message = client.messages.create(
                model=validation_model,
                max_tokens=200,  # Short response needed
                temperature=0.1,  # More deterministic
                messages=[{"role": "user", "content": prompt}],
            )
            latency_ms = int((time.perf_counter() - start) * 1000)

            content = message.content[0].text if message and message.content else ""
            logger.info(f"AI Validation response ({latency_ms}ms): {content[:100]}")

            # Parse JSON response
            try:
                # Handle potential markdown code blocks
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                parsed = json.loads(content.strip())
            except json.JSONDecodeError:
                # Try to extract decision from text
                content_upper = content.upper()
                if "APPROVE" in content_upper:
                    parsed = {"decision": "APPROVE", "reasoning": content[:100], "confidence_adjustment": 0}
                else:
                    parsed = {"decision": "REJECT", "reasoning": content[:100], "confidence_adjustment": 0}

            usage = getattr(message, "usage", None)

            return SignalValidation(
                decision=parsed.get("decision", "REJECT").upper(),
                reasoning=parsed.get("reasoning", "No reasoning provided"),
                confidence_adjustment=int(parsed.get("confidence_adjustment", 0)),
                model=validation_model,
                latency_ms=latency_ms,
                input_tokens=getattr(usage, "input_tokens", None) if usage else None,
                output_tokens=getattr(usage, "output_tokens", None) if usage else None,
            )

        except Exception as e:
            logger.error(f"AI signal validation failed: {e}")
            return None


@dataclass
class SignalValidation:
    """Result of AI signal validation."""
    decision: str  # APPROVE or REJECT
    reasoning: str
    confidence_adjustment: int = 0
    model: str = ""
    latency_ms: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

    @property
    def approved(self) -> bool:
        return self.decision == "APPROVE"

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "reasoning": self.reasoning,
            "confidence_adjustment": self.confidence_adjustment,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }
