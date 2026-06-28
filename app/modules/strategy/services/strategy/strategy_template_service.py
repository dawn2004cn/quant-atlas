from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StrategyCategory(Enum):
    TREND = "trend"
    MEAN_REVERSION = "mean_reversion"
    QUANT_FACTOR = "quant_factor"
    ARBITRAGE = "arbitrage"
    AI_DRIVEN = "ai_driven"

@dataclass
class StrategyTemplate:
    template_id: str
    name: str
    description: str
    category: StrategyCategory
    base_logic_class: str  # The class path to the strategy implementation
    default_params: dict[str, Any] = field(default_factory=dict)
    required_params: list[str] = field(default_factory=list)
    suggested_market: str = "CN"
    risk_profile: str = "moderate"

class StrategyTemplateService:
    """Service for managing strategy templates for the retail Strategy Wizard."""

    def __init__(self) -> None:
        # In a real scenario, these could be loaded from a JSON file or Database
        self._templates: dict[str, StrategyTemplate] = self._initialize_golden_templates()

    def _initialize_golden_templates(self) -> dict[str, StrategyTemplate]:
        templates = [
            StrategyTemplate(
                template_id="trend_following_basic",
                name="基础趋势跟随",
                description="基于移动平均线交叉的经典趋势跟随策略，适合波动率较高的市场。",
                category=StrategyCategory.TREND,
                base_logic_class="app.modules.strategy.logic.trend.MovingAverageCrossStrategy",
                default_params={"fast_ma": 20, "slow_ma": 60, "signal_threshold": 0.02},
                required_params=["fast_ma", "slow_ma"],
                risk_profile="aggressive"
            ),
            StrategyTemplate(
                template_id="mean_reversion_rsi",
                name="RSI 超买超卖回归",
                description="利用 RSI 指标捕捉短期过度反应导致的价格反弹或回调。",
                category=StrategyCategory.MEAN_REVERSION,
                base_logic_class="app.modules.strategy.logic.reversion.RSIReversionStrategy",
                default_params={"rsi_period": 14, "overbought": 70, "oversold": 30},
                required_params=["rsi_period", "overbought", "oversold"],
                risk_profile="moderate"
            ),
            StrategyTemplate(
                template_id="factor_momentum_alpha",
                name="量价动量因子 Alpha",
                description="结合量能爆发与价格突破的量化动量模型。",
                category=StrategyCategory.QUANT_FACTOR,
                base_logic_class="app.modules.strategy.logic.factor.MomentumAlphaStrategy",
                default_params={"lookback_period": 5, "volume_multiplier": 2.0},
                required_params=["lookback_period", "volume_multiplier"],
                risk_profile="moderate"
            ),
            StrategyTemplate(
                template_id="ai_sentiment_adaptive",
                name="AI 情绪自适应策略",
                description="通过 AI 分析新闻情绪，动态调整持仓权重。",
                category=StrategyCategory.AI_DRIVEN,
                base_logic_class="app.modules.strategy.logic.ai.SentimentAdaptiveStrategy",
                default_params={"sentiment_threshold": 0.6, "decay_rate": 0.1},
                required_params=["sentiment_threshold"],
                risk_profile="conservative"
            ),
        ]
        return {t.template_id: t for t in templates}

    def list_templates(self, category: StrategyCategory | None = None) -> list[StrategyTemplate]:
        """List all available strategy templates, optionally filtered by category."""
        if category:
            return [t for t in self._templates.values() if t.category == category]
        return list(self._templates.values())

    def get_template(self, template_id: str) -> StrategyTemplate | None:
        """Get a specific template by its ID."""
        return self._templates.get(template_id)

    def create_template_from_alpha(self, token_id: str, token_service: Any) -> StrategyTemplate:
        """
        Dynamic Template Generation: Convert a Marketplace Alpha Token
        into a Strategy Template for the Wizard.
        """
        manifest = token_service.get_manifest(token_id)
        if not manifest:
            raise ValueError(f"Token {token_id} not found")

        # Map token factor to a category
        # In a real system, the token manifest would store its category.
        category = StrategyCategory.QUANT_FACTOR

        # Create a dynamic template
        return StrategyTemplate(
            template_id=f"tpl_alpha_{token_id}",
            name=f"Alpha-Driven: {manifest.token_name}",
            description=f"Generated from token {manifest.token_symbol}. {manifest.description}",
            category=category,
            base_logic_class="app.modules.strategy.logic.factor.MomentumAlphaStrategy", # Default to factor logic
            default_params={"alpha_token_id": token_id, "lookback_period": 5},
            required_params=["alpha_token_id"],
            risk_profile="moderate"
        )

    def get_categories(self) -> list[StrategyCategory]:
        """Get all supported strategy categories."""
        return list(StrategyCategory)
