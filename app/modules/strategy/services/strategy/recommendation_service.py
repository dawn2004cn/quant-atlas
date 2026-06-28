"""Daily recommendation service — Phase C facade.

Delegates data-fetching to RecommendationDataService and scoring/enrichment
to RecommendationScoringService.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.dto.service_result import GenericResponseDTO
from app.domain.enums import MarketCode
from app.modules.strategy.services.strategy.recommendation_data_service import (
    _safe_float,
    RecommendationDataService,
)
from app.modules.strategy.services.strategy.recommendation_scoring_service import (
    RecommendationScoringService,
)

logger = get_logger(__name__)


class RecommendationService:
    """Compose daily Top-N recommendations from existing strategy evidence.

    Thin facade that delegates data access to RecommendationDataService and
    scoring/enrichment logic to RecommendationScoringService.
    """

    def __init__(
        self,
        *,
        selection_source_service: object,
        signal_flag_service: Any | None,
        trade_plan_service: object,
        ai_evidence_service: object,
        signal_observation_service: Any | None = None,
    ) -> None:
        self._trade_plan = trade_plan_service
        self._data = RecommendationDataService(
            signal_flag_service=signal_flag_service,
            selection_source_service=selection_source_service,
            ai_evidence_service=ai_evidence_service,
            signal_observation_service=signal_observation_service,
        )
        self._scoring = RecommendationScoringService()

    def daily_top(
        self,
        *,
        market: MarketCode = MarketCode.CN,
        top_n: int = 3,
        account_equity: float = 100000.0,
        user_id: int | None = None,
    ) -> GenericResponseDTO:
        """Return daily Top-N actionable recommendations."""
        top_n = max(1, min(int(top_n or 3), 5))
        candidates = self._data.candidate_rows(market, limit=max(top_n * 4, 12))

        staged: list[tuple[float, dict[str, Any]]] = []
        for row in candidates:
            code = str(row.get("code") or row.get("symbol") or "").strip()
            if not code:
                continue
            try:
                trade_plan = self._trade_plan.build_plan(
                    symbol=code,
                    market=market,
                    account_equity=account_equity,
                    cash_available=account_equity,
                    risk_per_trade_pct=1.0,
                    max_position_pct=15.0,
                    entry_price=_safe_float(row.get("price")) or None,
                )
            except Exception as exc:
                logger.warning("recommendation trade plan failed for %s: %s", code, exc)
                continue

            evidence = self._data.safe_evidence(code, market)
            agent_cal = self._data.agent_calibration(code)
            composite_score = self._scoring.score(row, evidence, agent_cal)

            plan_dict = trade_plan.model_dump() if hasattr(trade_plan, "model_dump") else {}
            plan = plan_dict.get("plan") or {}
            core_logic = self._scoring.core_logic(row, evidence)
            industry_position = self._scoring.industry_position(row)

            item = {
                "code": code,
                "name": row.get("name") or plan_dict.get("name") or code,
                "market": market.value,
                "industry": row.get("industry") or industry_position.get("industry") or "",
                "source": row.get("source") or "recommendation",
                "score": composite_score,
                "agent_calibration": agent_cal,
                "one_line_verdict": self._scoring.one_line_verdict(row, core_logic, evidence),
                "core_logic": core_logic,
                "industry_position": industry_position,
                "buy_zone": {
                    "low": round(_safe_float(plan.get("entry_price")) * 0.985, 2),
                    "high": round(_safe_float(plan.get("entry_price")) * 1.015, 2),
                },
                "stop_loss": plan.get("stop_loss"),
                "take_profit_1": plan.get("take_profit_1"),
                "target_price": plan.get("target_price"),
                "risk_reward_ratio": plan.get("risk_reward_ratio"),
                "recommended_shares": plan.get("recommended_shares"),
                "position_weight_pct": plan.get("position_weight_pct"),
                "estimated_win_rate": self._data.estimated_win_rate(
                    code, agent_cal, user_id=user_id
                ),
                "evidence": {
                    "trust": evidence.get("trust", {}),
                    "calibration": evidence.get("calibration", {}),
                    "signals": row.get("signal_strategies") or row.get("buy_signals") or [],
                },
                "links": {
                    "detail": f"/stock/{code}?m={market.value}",
                    "decision_brief": f"/stock/{code}?m={market.value}#decision-brief-strip",
                    "trade_plan": f"/stock/{code}?m={market.value}#section-trade-plan",
                    "diagnosis": f"/ai-analysis?symbol={code}&market={market.value}",
                    "industry_chain": f"/stock/{code}?m={market.value}#section-industry-chain",
                },
            }
            staged.append((composite_score, item))

        staged.sort(key=lambda pair: pair[0], reverse=True)
        items = []
        for rank, (_score_val, item) in enumerate(staged[:top_n], start=1):
            item["rank"] = rank
            items.append(item)

        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market": market.value,
            "top_n": top_n,
            "items": items,
            "disclaimer": "For research purposes only. Not investment advice.",
        }
