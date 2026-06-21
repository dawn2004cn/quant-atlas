from __future__ import annotations

"""Adopt a generated trade plan into the user's signal observation loop."""

from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode

logger = get_logger(__name__)


def _to_dict(value: object) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {}


def _safe_float(value: object) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


class TradePlanAdoptionService:
    """Build a trade plan and persist it as an open observation (watchlist-style)."""

    def __init__(
        self,
        *,
        trade_plan_service: Any,
        signal_observation_service: Any,
    ) -> None:
        self._trade_plan = trade_plan_service
        self._observations = signal_observation_service

    def adopt(
        self,
        *,
        user_id: int,
        symbol: str,
        market: MarketCode = MarketCode.CN,
        source: str = "trade_plan_adopt",
        strategy_id: str | None = None,
        account_equity: float = 100000.0,
        cash_available: float | None = None,
        risk_per_trade_pct: float = 1.0,
        max_position_pct: float = 15.0,
        entry_price: float | None = None,
        reason: str = "",
        ai_summary: str = "",
    ) -> dict[str, Any]:
        clean_symbol = str(symbol or "").strip().upper()
        if not clean_symbol:
            raise ValueError("symbol_required")
        if self._observations is None:
            raise RuntimeError("signal_observation_service_unavailable")

        plan_raw = self._trade_plan.build_plan(
            symbol=clean_symbol,
            market=market,
            account_equity=account_equity,
            cash_available=cash_available if cash_available is not None else account_equity,
            risk_per_trade_pct=risk_per_trade_pct,
            max_position_pct=max_position_pct,
            entry_price=entry_price,
        )
        plan_dict = _to_dict(plan_raw)
        if plan_dict.get("status") == "price_unavailable":
            raise ValueError(plan_dict.get("error") or "price_unavailable")

        entry, stop, target = self._extract_prices(plan_dict)
        adopt_reason = reason.strip() or self._default_reason(source, strategy_id)
        summary = ai_summary.strip() or adopt_reason

        observation = self._observations.add_observation(
            symbol=clean_symbol,
            market=market,
            user_id=user_id,
            name=str(plan_dict.get("name") or "").strip() or None,
            entry_price=entry,
            stop_loss=stop,
            target_price=target,
            source=source,
            reason=adopt_reason,
            ai_summary=summary[:2000],
        )

        return {
            "status": "adopted",
            "symbol": clean_symbol,
            "market": market.value,
            "source": source,
            "strategy_id": strategy_id,
            "plan": plan_dict,
            "observation": _to_dict(observation),
            "links": {
                "observations": "/signal-observations",
                "stock_detail": f"/stock/{clean_symbol}?m={market.value}",
            },
        }

    @staticmethod
    def _extract_prices(plan_dict: dict[str, Any]) -> tuple[float | None, float | None, float | None]:
        inner = plan_dict.get("plan") if isinstance(plan_dict.get("plan"), dict) else {}
        entry = _safe_float(plan_dict.get("entry_price")) or _safe_float(inner.get("entry_price"))
        stop = _safe_float(inner.get("stop_loss")) or _safe_float(plan_dict.get("stop_loss"))
        target = (
            _safe_float(inner.get("take_profit_1"))
            or _safe_float(inner.get("take_profit"))
            or _safe_float(plan_dict.get("take_profit"))
            or _safe_float(inner.get("target_price"))
            or _safe_float(plan_dict.get("target_price"))
        )
        return entry, stop, target

    @staticmethod
    def _default_reason(source: str, strategy_id: str | None) -> str:
        if strategy_id:
            return f"Adopted trade plan from {source} ({strategy_id})"
        return f"Adopted trade plan from {source}"


__all__ = ["TradePlanAdoptionService"]
