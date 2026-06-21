from __future__ import annotations
"""CorrectionIntentService — apply arbiter regime shifts to TradePlan parameters."""

from typing import Any

from app.core.event_bus import CorrectionIntentEvent, get_event_bus
from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.sequence_chain import CorrectionIntent, new_intent_id

logger = get_logger(__name__)

_VERDICT_PATCHES: dict[str, dict[str, Any]] = {
    "bearish": {
        "risk_per_trade_pct": 0.5,
        "max_position_pct": 8.0,
        "change_type": "regime_shift",
    },
    "bullish": {
        "risk_per_trade_pct": 1.5,
        "max_position_pct": 20.0,
        "change_type": "regime_shift",
    },
    "neutral": {
        "risk_per_trade_pct": 1.0,
        "max_position_pct": 12.0,
        "change_type": "stance_flip",
    },
}


class CorrectionIntentService:
    """Translate arbiter consensus into trade-plan parameter patches."""

    def __init__(self, *, trade_plan_service: Any | None = None) -> None:
        self._trade_plan = trade_plan_service
        self._last_verdict: dict[str, str] = {}
        self._pending: dict[str, CorrectionIntent] = {}

    def maybe_emit_correction(
        self,
        *,
        provenance_id: str,
        symbol: str,
        market: str,
        verdict: str,
        confidence: float,
        prior_verdict: str | None = None,
    ) -> CorrectionIntent | None:
        """Emit CorrectionIntent when verdict shifts with sufficient confidence."""
        key = f"{market.upper()}:{symbol.strip().lower()}"
        prior = prior_verdict or self._last_verdict.get(key, "")
        new_v = verdict.strip().lower()
        if not new_v or new_v == prior:
            self._last_verdict[key] = new_v
            return None
        if not prior:
            self._last_verdict[key] = new_v
            return None
        if confidence < 0.55:
            self._last_verdict[key] = new_v
            return None

        patch_cfg = _VERDICT_PATCHES.get(new_v, _VERDICT_PATCHES["neutral"])
        intent = CorrectionIntent(
            intent_id=new_intent_id(),
            provenance_id=provenance_id,
            symbol=symbol.strip().lower(),
            market=market.upper(),
            change_type=str(patch_cfg.get("change_type", "regime_shift")),
            prior_verdict=prior,
            new_verdict=new_v,
            confidence=confidence,
            parameter_patch={
                k: v
                for k, v in patch_cfg.items()
                if k in ("risk_per_trade_pct", "max_position_pct")
            },
            rationale=f"仲裁 verdict {prior or 'none'} → {new_v} (conf={confidence:.2f})",
        )
        self._last_verdict[key] = new_v
        self._pending[key] = intent
        get_event_bus().publish(
            CorrectionIntentEvent(
                source="CorrectionIntentService",
                intent_id=intent.intent_id,
                provenance_id=provenance_id,
                symbol=intent.symbol,
                market=intent.market,
                change_type=intent.change_type,
                parameter_patch=intent.parameter_patch,
                confidence=confidence,
                rationale=intent.rationale,
            )
        )
        logger.info(
            "CorrectionIntent emitted sym=%s %s→%s patch=%s",
            symbol,
            prior,
            new_v,
            intent.parameter_patch,
        )
        return intent

    def get_pending(self, symbol: str, market: str = "CN") -> CorrectionIntent | None:
        key = f"{market.upper()}:{symbol.strip().lower()}"
        return self._pending.get(key)

    def apply_to_plan(
        self,
        *,
        symbol: str,
        market: MarketCode = MarketCode.CN,
        account_equity: float = 100_000.0,
        provenance_id: str | None = None,
    ) -> dict[str, Any]:
        """Build trade plan with pending correction patch merged."""
        if self._trade_plan is None:
            return {"ok": False, "message": "trade_plan_service_unavailable"}
        key = f"{market.value}:{symbol.strip().lower()}"
        intent = self._pending.get(key)
        if intent is None and provenance_id:
            for item in self._pending.values():
                if item.provenance_id == provenance_id:
                    intent = item
                    break
        patch = intent.parameter_patch if intent else {}
        plan = self._trade_plan.build_plan(
            symbol=symbol,
            market=market,
            account_equity=account_equity,
            **patch,
        )
        if intent:
            intent.applied = True
            if isinstance(plan, dict):
                plan["correction_intent"] = intent.model_dump()
                plan["provenance_id"] = intent.provenance_id
        return plan if isinstance(plan, dict) else {"plan": plan}
