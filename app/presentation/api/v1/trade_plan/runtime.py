"""Shared runtime for trade-plan HTTP routes."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from flask_login import current_user

from app.application.errors import ValidationError
from app.core.middleware.request_context import require_authenticated_user_id
from app.modules.execution.services.trade_plan_adoption_service import TradePlanAdoptionService
from app.presentation.api.v1_context import ApiV1Context

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TradePlanRuntime:
    ctx: ApiV1Context

    def user_id(self) -> int:
        return require_authenticated_user_id()

    def adoption_service(self) -> TradePlanAdoptionService:
        trade_plan = getattr(self.ctx, "trade_plan_service", None)
        if trade_plan is None:
            raise ValidationError("trade_plan_service_unavailable")
        if self.ctx.signal_observation_service is None:
            raise ValidationError("signal_observation_service_unavailable")
        return TradePlanAdoptionService(
            trade_plan_service=trade_plan,
            signal_observation_service=self.ctx.signal_observation_service,
        )

    def psychology_after_adopt(self, payload: dict) -> None:
        if not current_user.is_authenticated:
            return
        symbol = str(payload.get("symbol") or "").strip()
        if not symbol:
            return
        try:
            from app.modules.system.services.helpers.psychology_watchlist_hooks import (
                record_plan_adoption_event,
            )

            market_svc = None
            if getattr(self.ctx, "market", None) is not None:
                market_svc = getattr(self.ctx.market, "market_service", None)
            market_svc = market_svc or getattr(self.ctx, "market_service", None)
            record_plan_adoption_event(
                user_id=self.user_id(),
                symbol=symbol,
                market_service=market_svc,
                task_message_store=getattr(self.ctx, "task_message_store", None),
                lifecycle_service=getattr(self.ctx, "user_lifecycle_service", None),
                notify_message_center=False,
            )
        except (ImportError, AttributeError, TypeError, ValueError) as exc:
            logger.warning("psychology adopt hook: %s", exc)

    def log_decision_event(self, payload: dict) -> None:
        if not current_user.is_authenticated:
            return
        svc = getattr(self.ctx, "user_decision_context_service", None)
        if svc is None:
            return
        try:
            svc.record_event(
                user_id=self.user_id(),
                event_type="trade_plan_adopt",
                symbol=str(payload.get("symbol", "")),
                market=str(payload.get("market", "CN")),
                page="trade_plan",
                component="action_bar",
                action="adopt",
                detail={"source": payload.get("source"), "strategy_id": payload.get("strategy_id")},
            )
        except (AttributeError, TypeError, ValueError) as exc:
            logger.warning("decision event hook: %s", exc)

    def audit_after_adopt(self, payload: dict) -> None:
        audit = getattr(self.ctx, "user_audit_trail_service", None)
        if audit is None or not current_user.is_authenticated:
            return
        symbol = str(payload.get("symbol") or "").strip()
        if not symbol:
            return
        try:
            audit.record(
                user_id=self.user_id(),
                action="trade_plan_adopt",
                target_type="symbol",
                target_id=symbol,
                metadata={
                    "source": payload.get("source"),
                    "market": payload.get("market"),
                    "observation_id": payload.get("observation_id"),
                },
            )
        except (AttributeError, TypeError, ValueError) as exc:
            logger.warning("audit trade_plan_adopt: %s", exc)

    def after_adopt_hooks(self, payload: dict) -> None:
        self.psychology_after_adopt(payload)
        self.audit_after_adopt(payload)
        self.log_decision_event(payload)
