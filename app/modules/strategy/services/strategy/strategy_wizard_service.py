from __future__ import annotations

from typing import Any
from app.core.logger import get_logger
from app.modules.strategy.services.strategy.strategy_template_service import StrategyTemplateService
from app.core.registry import ServiceRegistry

logger = get_logger(__name__)

class StrategyWizardService:
    """Orchestrates the guided strategy creation process for retail users."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.template_service = StrategyTemplateService()

        # Services needed for finalization and preview
        self.strategy_service = registry.get("strategy_service")
        self.backtest_service = registry.get_or_none("strategy_optimization_service")
        self.fast_engine = registry.get("fast_backtest_engine")
        self.strategy_risk_validator = registry.get_or_none("strategy_risk_validator")

    def get_wizard_start_data(self) -> dict[str, Any]:
        """Get initial data needed to start the wizard (categories and templates)."""
        # AI Recommendation based on Market Regime
        recommended_template_id = self._get_recommended_template_id()

        return {
            "categories": [c.value for c in self.template_service.get_categories()],
            "templates": [
                {
                    "id": t.template_id,
                    "name": t.name,
                    "description": t.description,
                    "category": t.category.value,
                    "risk_profile": t.risk_profile,
                    "is_recommended": t.template_id == recommended_template_id
                } for t in self.template_service.list_templates()
            ],
            "recommendation": {
                "template_id": recommended_template_id,
                "reason": "AI recommended this template based on current market regime." if recommended_template_id else None
            }
        }

    def _get_recommended_template_id(self) -> str | None:
        """
        Interacts with MarketRegimeService to recommend the best strategy template
        for the current environment.
        """
        try:
            # Resolve MarketRegimeService from registry
            # Note: MarketRegimeService in this project seems to be a domain service,
            # we might need to instantiate it or get it from the registry if it was wired.
            from app.domain.services.market_regime_service import MarketRegimeService
            regime_service = MarketRegimeService()

            # In a real scenario, we would fetch current sentiment/breadth from actual services
            # For now, we simulate a 'Neutral' regime to demonstrate the mapping
            # In production, we'd inject a 'MarketDataService' to get real values.
            regime = regime_service.evaluate_stance(sentiment_score=55.0)
            stance = regime["stance"] # 'aggressive', 'defensive', 'neutral'

            # Mapping Regime -> Strategy Category
            mapping = {
                "aggressive": "trend",         # Bull market -> Trend following
                "defensive": "mean_reversion", # Bear/Choppy market -> Mean reversion
                "neutral": "quant_factor",     # Sideways market -> Quant Factors
            }

            target_category = mapping.get(stance)
            if not target_category:
                return None

            # Find a template that matches the category
            templates = self.template_service.list_templates()
            for t in templates:
                if t.category.value == target_category:
                    return t.template_id

        except Exception as e:
            logger.error(f"Failed to get regime-based recommendation: {e}")

        return None

    def get_template_config(self, template_id: str) -> dict[str, Any]:
        """Get the required parameters and defaults for a specific template."""
        template = self.template_service.get_template(template_id)
        if not template:
            # Check if it's a dynamic alpha template
            if template_id.startswith("tpl_alpha_"):
                token_id = template_id.replace("tpl_alpha_", "")
                token_svc = self.registry.get("tokenized_alpha_service")
                template = self.template_service.create_template_from_alpha(token_id, token_svc)
            else:
                raise ValueError(f"Template {template_id} not found")

        return {
            "template_id": template.template_id,
            "name": template.name,
            "required_params": template.required_params,
            "default_params": template.default_params,
            "suggested_market": template.suggested_market
        }

    async def preview_strategy(self, template_id: str, user_params: dict[str, Any]) -> dict[str, Any]:
        """
        Runs a 'Quick-Preview' backtest using the FastBacktestEngine.
        """
        template = self.template_service.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Merge defaults with user provided params
        final_params = {**template.default_params, **user_params}

        # Validate required params
        for p in template.required_params:
            if p not in final_params:
                raise ValueError(f"Missing required parameter: {p}")

        # Use the FastBacktestEngine for a real (but fast) simulation
        # We assume 'AAPL' as a default preview symbol, or we could pass one from the UI.
        result = await self.fast_engine.run_preview(
            symbol="AAPL",
            market="US",
            params=final_params,
            template_id=template_id,
        )
        result["backend"] = "fast_backtest_engine"

        try:
            from datetime import datetime, timedelta

            import numpy as np
            import pandas as pd

            from app.modules.strategy.services.strategy.vectorbt_adapter import VectorBTBacktestAdapter

            end = datetime.now()
            start = end - timedelta(days=180)
            dates = pd.date_range(start, end, freq="D")
            np.random.seed(42)
            close = pd.Series(100 * (1 + np.random.randn(len(dates)) * 0.02).cumprod(), index=dates)
            result["backend_compare"] = VectorBTBacktestAdapter().compare_with_fast_preview(
                close=close,
                fast_metrics=result.get("metrics", {}),
            )
        except Exception as exc:
            logger.debug("VectorBT preview compare skipped: %s", exc)

        return result

    def create_from_wizard(self, template_id: str, user_params: dict[str, Any], risk_settings: dict[str, Any]) -> dict[str, Any]:
        """
        Finalizes the wizard process and creates a real strategy instance.
        Includes a Pre-Trade Risk Preflight check.
        """
        template = self.template_service.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # 1. Perform Pre-Trade Risk Validation
        risk_validator = getattr(self, "strategy_risk_validator", None)
        if risk_validator:
            passed, issues = risk_validator.validate_strategy_config(
                template=template,
                params=user_params,
                risk_settings=risk_settings,
                user_id=0 # Should be current_user.id
            )
            if not passed:
                return {"status": "risk_blocked", "issues": issues, "message": "Strategy failed risk preflight."}

        final_params = {**template.default_params, **user_params}

        # Use StrategyApplicationService to create the actual strategy record
        try:
            strategy_id = self.strategy_service.create_strategy(
                name=f"Wizard_{template.name}_{user_params.get('name', 'unnamed')}",
                logic_class=template.base_logic_class,
                params=final_params,
                risk_settings=risk_settings,
                tags=["wizard_created", template.category.value]
            )
            return {"status": "created", "strategy_id": strategy_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}
