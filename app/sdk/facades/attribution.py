from __future__ import annotations

"""Attribution facade over ``UnifiedAttributionService``."""

from typing import Any

from app.domain.dto.analytics_dto import AttributionReportDTO
from app.modules.strategy.services.analytics.unified_attribution_service import UnifiedAttributionService


class AttributionFacade:
    """Thin SDK wrapper for unified attribution reports."""

    def __init__(self, service: UnifiedAttributionService | None = None) -> None:
        self._service = service or UnifiedAttributionService()

    def report(
        self,
        *,
        strategy_name: str,
        period: str,
        positions: list[dict[str, Any]],
        benchmark_return: float = 0.0,
        symbol: str | None = None,
        strategy_id: str | None = None,
        portfolio_return: float | None = None,
        factor_exposures: dict[str, float] | None = None,
        factor_returns: dict[str, float] | None = None,
        alpha: float = 0.0,
        include_slippage: bool = True,
    ) -> AttributionReportDTO:
        return self._service.build_report(
            strategy_name=strategy_name,
            period=period,
            positions=positions,
            benchmark_return=benchmark_return,
            symbol=symbol,
            strategy_id=strategy_id,
            portfolio_return=portfolio_return,
            factor_exposures=factor_exposures,
            factor_returns=factor_returns,
            alpha=alpha,
            include_slippage=include_slippage,
        )

    def report_dict(self, **kwargs: Any) -> dict[str, Any]:
        return self.report(**kwargs).model_dump(mode="json")
