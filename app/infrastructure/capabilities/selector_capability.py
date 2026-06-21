from __future__ import annotations
"""Stock selection / screening capability."""


from typing import Any

from app.domain.capabilities.base import BaseCapability
from app.domain.enums import MarketCode
from app.infrastructure.capabilities.registry import capability


def _safe_top_n(raw: object, default: int = 10, cap: int = 200) -> int:
    try:
        n = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default
    return max(1, min(cap, n))


@capability("run_selector")
class SelectorCapability(BaseCapability):
    """Run stock selection model or custom screening criteria."""

    capability_name = "run_selector"

    def __init__(self, **services: Any) -> None:
        self._strategy_service = services.get("strategy_service")

    def execute(
        self,
        *,
        model_name: str,
        market: MarketCode,
        criteria: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], str]:
        if not self._strategy_service:
            return (
                {"ok": False, "error": "Strategy service not initialized"},
                "strategy service not initialized",
            )

        c = criteria or {}
        top_n = _safe_top_n(c.get("top_n", 10))

        if model_name.strip() == "custom_criteria":
            screening_criteria = c.get("screening_criteria")
            if not screening_criteria:
                return (
                    {"ok": False, "error": "missing_screening_criteria"},
                    "custom_criteria mode requires screening_criteria",
                )
            note = f"选股引擎: 自定义筛选规则; market={market.value}."
            try:
                from app.domain.dto.strategy_dto import ScreeningCriteria as DtoScreeningCriteria

                dto_criteria = DtoScreeningCriteria(**screening_criteria)
                raw = self._strategy_service.custom_criteria_select_stocks(
                    dto_criteria, market
                )
            except Exception as exc:
                return {"ok": False, "error": str(exc)}, f"{note} 执行失败: {exc!s}."
            return {**raw, "ok": True}, (
                f"{note} 返回 {len(raw.get('candidates') or [])} 条候选。"
            )

        note = (
            f"选股引擎: StrategyApplicationService.select_stocks; "
            f"模型/策略={model_name}; market={market.value}; top_n={top_n}."
        )
        try:
            raw = self._strategy_service.select_stocks(model_name, market, top_n)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}, f"{note} 执行失败: {exc!s}."
        return {**raw, "ok": True}, (
            f"{note} 返回 {len(raw.get('candidates') or [])} 条候选。"
        )
