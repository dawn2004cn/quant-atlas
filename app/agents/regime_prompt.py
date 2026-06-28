from __future__ import annotations
"""Regime-Aware Prompting - Market Sentiment Anchoring.

This module implements from midify_plan12.md:
- RegimePromptInjector: Inject market regime into all agent prompts
- Market sentiment anchoring for different regimes
- Automatic prompt modification based on market state

Usage:
    injector = RegimePromptInjector(regime_manager)
    enhanced_prompt = injector.inject_into_prompt(
        base_prompt="Analyze stock fundamentals",
        agent_type="fundamental"
    )
"""


from dataclasses import dataclass
from typing import Any

from .dynamic_personality import MarketRegime, MarketRegimeManager

from app.core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class RegimePromptTemplate:
    """Prompt template for a specific regime."""
    regime: MarketRegime
    system_prompt_addition: str
    confidence_modifier: float
    additional_instructions: list[str]


class RegimePromptInjector:
    """Inject market regime context into all agent prompts.

    In bear markets, automatically adds:
    - "Current market is in extreme fear, be skeptical of positive news"
    - "Check cash flow resilience"

    In bull markets:
    - "Market is optimistic, but maintain risk awareness"
    """

    def __init__(self, regime_manager: MarketRegimeManager):
        self._regime_manager = regime_manager

        self._regime_templates = {
            MarketRegime.BULL: RegimePromptTemplate(
                regime=MarketRegime.BULL,
                system_prompt_addition="""
[MARKET CONTEXT - BULL MARKET]
Current market conditions are BULLISH/OPTIMISTIC.
- Be aware of momentum and growth catalysts
- But maintain vigilance for emerging risks
- Do not blindly follow bullish sentiment without fundamental support
- Take profits strategy should be active
""".strip(),
                confidence_modifier=0.1,
                additional_instructions=[
                    "Consider momentum factors in analysis",
                    "Be alert to early signs of reversal",
                ],
            ),
            MarketRegime.BEAR: RegimePromptTemplate(
                regime=MarketRegime.BEAR,
                system_prompt_addition="""
[MARKET CONTEXT - BEAR MARKET]
Current market is in EXTREME FEAR/DISTRESS.
- Be highly skeptical of positive news - apply 50% discount to bullish signals
- PRIORITIZE: cash position, balance sheet strength, business continuity
- Analyze defensive characteristics (dividends, low debt, stable cash flow)
- Risk management takes precedence over upside potential
- Stop loss discipline is critical
""".strip(),
                confidence_modifier=-0.15,
                additional_instructions=[
                    "Check cash flow before any bullish recommendation",
                    "Verify business model resilience under stress",
                    "Apply higher bar for positive conclusions",
                ],
            ),
            MarketRegime.HIGH_VOLATILITY: RegimePromptTemplate(
                regime=MarketRegime.HIGH_VOLATILITY,
                system_prompt_addition="""
[MARKET CONTEXT - HIGH VOLATILITY]
Market is experiencing HIGH VOLATILITY/UNCERTAINTY.
- Be cautious of false breakouts - wait for confirmed signals
- Widen stop-loss margins
- Reduce position sizing recommendations
- Consider options/hedging strategies
- Do not rely on single-indicator signals
""".strip(),
                confidence_modifier=-0.2,
                additional_instructions=[
                    "Wait for confirmed signals before acting",
                    "Use multiple confirmation indicators",
                    "Stress test positions for volatility spikes",
                ],
            ),
            MarketRegime.LOW_VOLATILITY: RegimePromptTemplate(
                regime=MarketRegime.LOW_VOLATILITY,
                system_prompt_addition="""
[MARKET CONTEXT - LOW VOLATILITY]
Market is in LOW VOLATILITY/CONSOLIDATION phase.
- Range-bound trading is likely
- Look for breakout opportunities at support/resistance
- Be patient - opportunities will come
- Focus on fundamentals rather than technicals
""".strip(),
                confidence_modifier=0.0,
                additional_instructions=[
                    "Focus on support/resistance levels",
                    "Be patient for clear signals",
                ],
            ),
            MarketRegime.NEUTRAL: RegimePromptTemplate(
                regime=MarketRegime.NEUTRAL,
                system_prompt_addition="""
[MARKET CONTEXT - NEUTRAL]
Market conditions are NEUTRAL/UNCLEAR.
- Balance opportunities with risks
- Wait for clear signals before strong convictions
- Consider both bullish and bearish scenarios equally
- Maintain balanced position sizing
""".strip(),
                confidence_modifier=0.0,
                additional_instructions=[
                    "Present balanced view with both scenarios",
                    "Wait for clearer signals",
                ],
            ),
        }

    async def inject_into_prompt(
        self,
        base_prompt: str,
        agent_type: str,
        custom_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Inject regime context into base prompt."""
        regime_context = await self._regime_manager.detect_regime()
        template = self._regime_templates.get(
            regime_context.regime,
            self._regime_templates[MarketRegime.NEUTRAL],
        )

        enhanced_prompt = f"{base_prompt}\n\n{template.system_prompt_addition}"

        if template.additional_instructions:
            enhanced_prompt += "\n\n" + "Additional instructions:\n"
            for instruction in template.additional_instructions:
                enhanced_prompt += f"- {instruction}\n"

        return {
            "enhanced_prompt": enhanced_prompt,
            "regime": regime_context.regime.value,
            "regime_confidence": regime_context.confidence,
            "confidence_modifier": template.confidence_modifier,
            "injected": True,
        }

    def get_regime_context(self) -> dict[str, Any]:
        """Get current regime context without prompt modification."""
        return {
            "regime": "unknown",
            "confidence": 0.0,
        }

    def set_force_regime(self, regime: MarketRegime | None) -> None:
        """Force a specific regime (for testing/simulation)."""
        if regime:
            logger.info(f"Forcing regime: {regime.value}")

    def get_regime_instructions_for_agent(
        self,
        agent_type: str,
    ) -> dict[str, Any]:
        """Get regime-specific instructions for specific agent type."""
        agent_instructions = {
            "technical": {
                MarketRegime.BULL: "Focus on breakout confirmation but watch for false breakouts",
                MarketRegime.BEAR: "Be skeptical of rallies, look for breakdown signals",
                MarketRegime.HIGH_VOLATILITY: "Wait for multiple confirmation before entry",
            },
            "fundamental": {
                MarketRegime.BULL: "Be receptive to growth valuations but check sustainability",
                MarketRegime.BEAR: "Prioritize cash flow and balance sheet strength",
                MarketRegime.HIGH_VOLATILITY: "Stress test assumptions, check liquidity",
            },
            "risk": {
                MarketRegime.BULL: "Monitor for emerging risks despite positive environment",
                MarketRegime.BEAR: "Emphasize capital preservation, strict stop losses",
                MarketRegime.HIGH_VOLATILITY: "Recommend reduced position sizes, wider stops",
            },
        }

        instructions = agent_instructions.get(agent_type.lower(), {})

        return {
            "default": "Follow base risk management principles",
            "specific": instructions,
        }


class GlobalPromptEnhancer:
    """Global prompt enhancer that applies regime to all agent prompts."""

    def __init__(self, injector: RegimePromptInjector):
        self._injector = injector

    async def enhance(
        self,
        agent_type: str,
        base_prompt: str,
    ) -> str:
        """Enhance prompt with regime context."""
        result = await self._injector.inject_into_prompt(
            base_prompt,
            agent_type,
        )
        return result["enhanced_prompt"]


def create_regime_injector(
    regime_manager: MarketRegimeManager | None = None,
) -> RegimePromptInjector:
    """Factory to create regime prompt injector."""
    if regime_manager is None:
        from .dynamic_personality import create_regime_manager
        regime_manager = create_regime_manager()
    return RegimePromptInjector(regime_manager)
