from __future__ import annotations

from typing import Any
from app.core.registry import ServiceRegistry
from app.modules.strategy.services.strategy.strategy_template_service import StrategyTemplate
from app.core.logger import get_logger

logger = get_logger(__name__)

class StrategyRiskValidator:
    """
    Validates if a proposed strategy configuration is safe to deploy.
    Integrates PreTradePreflightService to verify the strategy's
    'Default Trade' against risk limits.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.preflight_svc = registry.get("pre_trade_preflight_service")
        self.market_svc = registry.get("market_service")

    def validate_strategy_config(
        self,
        template: StrategyTemplate,
        params: dict[str, Any],
        risk_settings: dict[str, Any],
        user_id: int
    ) -> tuple[bool, list[dict[str, Any]]]:
        """
        Simulates a 'first trade' for the strategy and checks if it passes preflight.
        """
        # 1. Extract a 'Representative Asset' for the strategy
        # For a general strategy, we pick a high-liquidity benchmark (e.g., 600519)
        benchmark_symbol = "600519.SH"

        # 2. Determine a representative trade size based on user risk settings
        # We assume the user provides 'budget' or 'account_equity' in risk_settings
        equity = float(risk_settings.get("account_equity", 100000.0))
        risk_pct = float(risk_settings.get("risk_per_trade", 0.02))

        # 3. Get current price
        price = 100.0 # Default
        if self.market_svc:
            try:
                quote = self.market_svc.list_quotes("CN", [benchmark_symbol])[0]
                price = float(quote.get("last", 100.0))
            except Exception:
                logger.warning("Suppressed exception", exc_info=True)
                pass

        # 4. Run Preflight
        # We simulate a a 'standard' trade quantity (e.g. 100 shares) to check for blocking issues
        try:
            preflight_result = self.preflight_svc.preflight(
                symbol=benchmark_symbol,
                direction="BUY",
                price=price,
                quantity=100,
                strategy_id=template.template_id,
                account_equity=equity,
                risk_per_trade=risk_pct
            )

            if not preflight_result.passed:
                issues = [
                    {"code": i.code, "message": i.message, "severity": i.severity}
                    for i in preflight_result.issues
                ]
                return False, issues

            return True, []
        except Exception as e:
            logger.error(f"Strategy risk validation failed: {e}")
            return False, [{"code": "system_error", "message": str(e), "severity": "blocking"}]
