from __future__ import annotations
"""Hook watchlist mutations into psychology guardian + message center."""

from typing import Any

from app.modules.user.services.user.psychology_guardian_service import PsychologyGuardianService
from app.core.logger import get_logger
from app.domain.enums import MarketCode

logger = get_logger(__name__)


def on_watchlist_mutation(
    *,
    user_id: int,
    symbol: str,
    action: str,
    market_service: Any | None = None,
    task_message_store: Any | None = None,
    psychology_store: Any | None = None,
    lifecycle_service: Any | None = None,
    notify_message_center: bool = True,
) -> dict[str, Any] | None:
    """Record add/remove and optionally push psychology alerts to task messages."""
    sym = (symbol or "").strip()
    if not sym or not user_id:
        return None
    change_pct = 0.0
    if market_service is not None:
        try:
            quotes = market_service.list_quotes(MarketCode.CN, [sym])
            if quotes:
                change_pct = float(quotes[0].get("change_pct", 0) or 0)
        except Exception as exc:  # noqa: BLE001
            logger.debug("psychology_watchlist_hooks quote: %s", exc)

    store = psychology_store
    if store is None:
        from app.modules.user.services.user.psychology_operation_store import (
            get_psychology_operation_store,
        )

        store = get_psychology_operation_store()

    store.record(
        user_id=user_id,
        action=action,
        symbol=sym,
        change_pct=change_pct,
    )
    history = store.list_recent(user_id)
    svc = PsychologyGuardianService(operation_store=store)
    result = svc.analyze_user_behavior(user_id=user_id, operation_history=history)
    if notify_message_center and task_message_store is not None and result.get("alerts"):
        pushed = svc.push_alerts_to_message_center(
            task_message_store,
            user_id=user_id,
            alerts=result.get("alerts") or [],
            lifecycle_service=lifecycle_service,
        )
        result["messages_pushed"] = pushed
    return result


def record_plan_adoption_event(
    *,
    user_id: int,
    symbol: str,
    market_service: Any | None = None,
    task_message_store: Any | None = None,
    psychology_store: Any | None = None,
    lifecycle_service: Any | None = None,
    notify_message_center: bool = False,
) -> dict[str, Any] | None:
    """Record trade-plan adopt as psychology signal (optional notify)."""
    return on_watchlist_mutation(
        user_id=user_id,
        symbol=symbol,
        action="adopt",
        market_service=market_service,
        task_message_store=task_message_store,
        psychology_store=psychology_store,
        lifecycle_service=lifecycle_service,
        notify_message_center=notify_message_center,
    )
