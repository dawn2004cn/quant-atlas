from __future__ import annotations

"""Context-Aware Personalities - Market Regime-Based Agent Personalities.

This module implements Dynamic Agent Personalities from midify_plan11.md:
- MarketRegimeManager: Detects market regime (bull/bear/neutral/volatile)
- DynamicPersonality: Switches agent personality based on market environment
- Defense/Aggressive mode switching for different market conditions

Usage:
    regime_mgr = MarketRegimeManager()
    current_regime = await regime_mgr.detect_regime(symbols=["600519"])
    personality = DynamicPersonality(regime_mgr)
    prompt = personality.get_personality_prompt("TechnicalAgent")
"""


from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class MarketRegime(Enum):
    """Market regime types."""
    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class RegimeContext:
    """Context information for market regime."""
    regime: MarketRegime
    confidence: float
    indicators: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.now)


class MarketRegimeManager:
    """Detects current market regime based on indicators."""

    def __init__(self, lookback_days: int = 30):
        self._lookback_days = lookback_days
        self._regime_cache: dict[str, RegimeContext] = {}
        self._cache_ttl_minutes = 15

    async def detect_regime(
        self,
        symbols: list[str] | None = None,
        market_index: str = "000001.SH",
    ) -> RegimeContext:
        """Detect overall market regime."""
        cache_key = "global"
        if cache_key in self._regime_cache:
            cached = self._regime_cache[cache_key]
            if self._is_cache_valid(cached):
                return cached

        indicators = await self._collect_indicators(market_index)

        regime = self._classify_regime(indicators)

        context = RegimeContext(
            regime=regime,
            confidence=indicators.get("confidence", 0.5),
            indicators=indicators,
        )

        self._regime_cache[cache_key] = context
        return context

    async def detect_symbol_regime(self, symbol: str) -> RegimeContext:
        """Detect regime for specific symbol."""
        if symbol in self._regime_cache:
            cached = self._regime_cache[symbol]
            if self._is_cache_valid(cached):
                return cached

        indicators = await self._collect_symbol_indicators(symbol)

        regime = self._classify_regime(indicators)

        context = RegimeContext(
            regime=regime,
            confidence=indicators.get("confidence", 0.5),
            indicators=indicators,
        )

        self._regime_cache[symbol] = context
        return context

    async def _collect_indicators(self, market_index: str) -> dict[str, Any]:
        """Collect market-wide indicators."""
        indicators = {
            "trend": "neutral",
            "volatility": "normal",
            "momentum": "neutral",
            "confidence": 0.6,
        }

        try:
            from app.infrastructure.database.stock_cache_db import StockCache
            cache = StockCache.default()

            history = cache.get_stock_history(
                market_index,
                (datetime.now() - timedelta(days=self._lookback_days)).strftime("%Y-%m-%d"),
                datetime.now().strftime("%Y-%m-%d"),
            )

            if history and len(history) > 5:
                prices = [float(h.get("close", 0)) for h in history]
                if prices:
                    recent = prices[-5:]
                    overall = prices

                    if overall[-1] > overall[0] * 1.05:
                        indicators["trend"] = "bullish"
                    elif overall[-1] < overall[0] * 0.95:
                        indicators["trend"] = "bearish"

                    import statistics
                    if len(recent) > 1:
                        vol = statistics.stdev(recent) / statistics.mean(recent) if statistics.mean(recent) > 0 else 0
                        if vol > 0.03:
                            indicators["volatility"] = "high"
                        elif vol < 0.01:
                            indicators["volatility"] = "low"

        except Exception as e:
            logger.warning(f"Failed to collect market indicators: {e}")

        return indicators

    async def _collect_symbol_indicators(self, symbol: str) -> dict[str, Any]:
        """Collect symbol-specific indicators."""
        return await self._collect_indicators(symbol)

    def _classify_regime(self, indicators: dict[str, Any]) -> MarketRegime:
        """Classify regime from indicators."""
        trend = indicators.get("trend", "neutral")
        volatility = indicators.get("volatility", "normal")

        if volatility == "high":
            return MarketRegime.HIGH_VOLATILITY
        elif volatility == "low":
            return MarketRegime.LOW_VOLATILITY

        if trend == "bullish":
            return MarketRegime.BULL
        elif trend == "bearish":
            return MarketRegime.BEAR

        return MarketRegime.NEUTRAL

    def _is_cache_valid(self, context: RegimeContext) -> bool:
        """Check if cache entry is still valid."""
        age = (datetime.now() - context.detected_at).total_seconds()
        return age < self._cache_ttl_minutes * 60


class DynamicPersonality:
    """Dynamic personality that adapts to market regime."""

    def __init__(self, regime_manager: MarketRegimeManager):
        self._regime_manager = regime_manager

        self._personality_templates = {
            "bull": {
                "technical": {
                    "system_prompt": "You are a technical analysis expert in a BULL MARKET. Be optimistic about breakouts and trend continuation. Require weaker confirmation for bullish signals.",
                    "confidence_boost": 0.15,
                    "bull_threshold": 0.4,
                },
                "fundamental": {
                    "system_prompt": "You are a fundamental analysis expert in a BULL MARKET. Focus on growth catalysts and positive catalysts. Be receptive to higher valuations.",
                    "confidence_boost": 0.1,
                    "bull_threshold": 0.4,
                },
                "risk": {
                    "system_prompt": "You are a risk management expert in a BULL MARKET. While conditions are favorable, maintain vigilance for emerging risks.",
                    "confidence_boost": 0.0,
                },
            },
            "bear": {
                "technical": {
                    "system_prompt": "You are a technical analysis expert in a BEAR MARKET. Be skeptical of rallies and look for breakdown signals. Require strong confirmation for any bullish view.",
                    "confidence_boost": -0.1,
                    "bull_threshold": 0.7,
                },
                "fundamental": {
                    "system_prompt": "You are a fundamental analysis expert in a BEAR MARKET. Focus on downside risks, cash position, and defensive characteristics.",
                    "confidence_boost": -0.15,
                    "bull_threshold": 0.7,
                },
                "risk": {
                    "system_prompt": "You are a risk management expert in a BEAR MARKET. Prioritize capital preservation. Be strict about stop losses and position sizing.",
                    "confidence_boost": 0.0,
                },
            },
            "high_volatility": {
                "technical": {
                    "system_prompt": "You are a technical analysis expert in a HIGH VOLATILITY market. Be cautious of false breakouts. Wait for confirmed signals before acting.",
                    "confidence_boost": -0.2,
                    "bull_threshold": 0.6,
                },
                "fundamental": {
                    "system_prompt": "You are a fundamental analysis expert in a HIGH VOLATILITY market. Focus on risk assessment and stress testing positions.",
                    "confidence_boost": -0.15,
                    "bull_threshold": 0.6,
                },
                "risk": {
                    "system_prompt": "You are a risk management expert in a HIGH VOLATILITY market. Implement strict risk controls. Reduce position sizes and widen stops.",
                    "confidence_boost": 0.0,
                },
            },
            "neutral": {
                "technical": {
                    "system_prompt": "You are a technical analysis expert in a NEUTRAL market. Balance opportunities with risks. Wait for clear signals.",
                    "confidence_boost": 0.0,
                    "bull_threshold": 0.5,
                },
                "fundamental": {
                    "system_prompt": "You are a fundamental analysis expert in a NEUTRAL market. Focus on valuation relative to peers and fundamentals.",
                    "confidence_boost": 0.0,
                    "bull_threshold": 0.5,
                },
                "risk": {
                    "system_prompt": "You are a risk management expert in a NEUTRAL market. Maintain balanced risk exposure.",
                    "confidence_boost": 0.0,
                },
            },
        }

    async def get_personality_prompt(
        self,
        agent_type: str,
        custom_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get personality-prompt configuration for agent."""
        regime = await self._regime_manager.detect_regime()
        regime_key = regime.regime.value

        templates = self._personality_templates.get(regime_key, self._personality_templates["neutral"])
        agent_template = templates.get(agent_type.lower(), templates.get("technical", {}))

        result = {
            "regime": regime_key,
            "regime_confidence": regime.confidence,
            **agent_template,
        }

        if custom_context:
            result = self._apply_context_overrides(result, custom_context)

        return result

    def _apply_context_overrides(
        self,
        base_prompt: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply custom context overrides."""
        result = base_prompt.copy()

        if context.get("force_regime"):
            result["regime"] = context["force_regime"]

        if context.get("confidence_adjustment"):
            result["confidence_boost"] = result.get("confidence_boost", 0) + context["confidence_adjustment"]

        return result

    def get_confidence_adjustment(
        self,
        base_confidence: float,
        agent_type: str,
    ) -> float:
        """Get confidence adjustment based on current regime."""
        template = self._personality_templates.get("neutral", {}).get(agent_type.lower(), {})
        return template.get("confidence_boost", 0.0)


def create_regime_manager() -> MarketRegimeManager:
    """Factory to create market regime manager."""
    return MarketRegimeManager()


def create_dynamic_personality(
    regime_manager: MarketRegimeManager | None = None,
) -> DynamicPersonality:
    """Factory to create dynamic personality."""
    if regime_manager is None:
        regime_manager = create_regime_manager()
    return DynamicPersonality(regime_manager)
