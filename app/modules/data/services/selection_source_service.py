from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""中长线 / 选股器：数据源 ``legacy`` | ``qlib_factors`` | ``model_score``。"""


from datetime import datetime
from typing import Any, Literal

from app.core.base_service import BaseApplicationService
from app.domain.enums import MarketCode
from app.application.errors import ValidationError
from app.modules.data.services.qlib_pipeline_service import QlibPipelineService
from app.modules.data.services.prediction_service import PredictionApplicationService
from app.modules.strategy.services.strategy.strategy_service import StrategyApplicationService

DataSource = Literal["legacy", "qlib_factors", "model_score"]


def _parse_data_source(raw: object) -> DataSource:
    s = str(raw or "legacy").strip().lower()
    if s in ("legacy", "qlib_factors", "model_score"):
        return s  # type: ignore[return-value]
    raise ValidationError("data_source 须为 legacy | qlib_factors | model_score")


class SelectionSourceService:
    def __init__(
        self,
        strategy_service: StrategyApplicationService,
        qlib_pipeline_service: QlibPipelineService,
        prediction_service: PredictionApplicationService,
        market_service: object,
    ) -> None:
        self._strategy = strategy_service
        self._qlib = qlib_pipeline_service
        self._prediction = prediction_service
        self._market = market_service

    def _enrich_quotes(self, candidates: list[dict[str, Any]], market: MarketCode) -> list[dict[str, Any]]:
        if not candidates:
            return candidates
        codes = [c.get("code", "") for c in candidates if c.get("code")]
        quotes = self._market.list_quotes(market, codes)
        
        qmap = {}
        for q in quotes:
            if hasattr(q, "model_dump"):
                q_dict = q.model_dump()
            elif hasattr(q, "dict"):
                q_dict = q.dict()
            else:
                q_dict = q
            
            if isinstance(q_dict, dict):
                qmap[q_dict.get("code")] = q_dict

        for c in candidates:
            code = c.get("code", "")
            q = qmap.get(code, {})
            if q:
                c["name"] = q.get("name") or c.get("name") or code
                c["price"] = float(q.get("price") or 0)
                c["change_pct"] = float(q.get("change_pct") or 0)
        return candidates

    def select_stocks(
        self,
        *,
        strategy: str,
        market: MarketCode,
        top_n: int,
        data_source: Any = "legacy",
        enable_qlib: bool,
        model_id: str | None = None,
        horizon_days: int = 20,
    ) -> GenericResponseDTO:
        ds = _parse_data_source(data_source)
        base_sent: dict[str, Any] = {"data_source": ds}

        if self._strategy is None:
            raise ValidationError("strategy_service not configured; cannot run selection")

        if ds == "legacy":
            out = self._strategy.select_stocks(
                strategy_name=strategy,
                market=market,
                top_n=top_n,
                selector_type=ds,
            )
            out.setdefault("sentiment_analysis", {})
            out["sentiment_analysis"] = {**out["sentiment_analysis"], **base_sent}
            return out

        if ds == "qlib_factors":
            if not enable_qlib:
                raise ValidationError("data_source=qlib_factors 需要 ENABLE_QLIB=1")
            block = self._qlib.cross_section_factor_rank(market, top_n=top_n)
            candidates = self._enrich_quotes(list(block.get("candidates") or []), market)
            return {
                "strategy": strategy,
                "effective_strategy_group": "qlib_factors",
                "market": market.value,
                "generated_at": datetime.now().isoformat(),
                "sentiment_analysis": {**base_sent, "evidence": block.get("evidence", "")},
                "candidates": candidates,
            }

        # model_score
        pre = self._strategy.select_stocks(
            strategy_name=strategy,
            market=market,
            top_n=min(max(top_n * 4, top_n), 48),
        )
        codes = [str(c.get("code", "")).strip() for c in pre.get("candidates", []) if c.get("code")]
        if not codes:
            return {
                "strategy": strategy,
                "effective_strategy_group": "model_score",
                "market": market.value,
                "generated_at": datetime.now().isoformat(),
                "sentiment_analysis": {**base_sent, "note": "legacy 预筛为空"},
                "candidates": [],
            }
        pr = self._prediction.scores_cross_section(
            codes,
            market,
            model_id=model_id,
            horizon_days=horizon_days,
        )
        ranking = [r for r in (pr.get("ranking") or []) if r.get("ok")]
        by_code = {str(c.get("code")): c for c in pre.get("candidates", [])}
        merged: list[dict[str, Any]] = []
        for r in ranking[:top_n]:
            sym = str(r.get("symbol", ""))
            base = dict(by_code.get(sym, {"code": sym, "name": sym}))
            base["score"] = float(r.get("score") or 0.0)
            base["reason"] = f"model_score:{pr.get('model', {}).get('id', '')} {pr.get('evidence', '')[:120]}"
            base["rating"] = "A" if base["score"] >= 3.0 else "B"
            base["buy_signals"] = ["模型截面分"]
            merged.append(base)
        merged = self._enrich_quotes(merged, market)
        return {
            "strategy": strategy,
            "effective_strategy_group": "model_score",
            "market": market.value,
            "generated_at": datetime.now().isoformat(),
            "sentiment_analysis": {**base_sent, "model": pr.get("model"), "evidence": pr.get("evidence")},
            "candidates": merged,
        }
