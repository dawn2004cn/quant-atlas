from __future__ import annotations
"""Record real fills into psychology_operation_store for guardian analysis."""

from typing import Any

from app.modules.system.services.helpers.psychology_execution_loader import (
    encode_retail_strategy_id,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


def record_execution_fill(
    *,
    user_id: int,
    symbol: str,
    side: str,
    change_pct: float = 0.0,
    psychology_store: Any | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Persist a buy/sell fill as psychology history (change_pct from quote if omitted)."""
    sym = str(symbol or "").strip()
    if not sym or not int(user_id):
        return None
    store = psychology_store
    if store is None:
        from app.modules.user.services.user.psychology_operation_store import (
            get_psychology_operation_store,
        )

        store = get_psychology_operation_store()
    action = "buy" if str(side or "").lower() in ("buy", "long", "cover") else "sell"
    meta = dict(metadata or {})
    meta.setdefault("source", "execution_feedback")
    meta.setdefault("strategy_id", encode_retail_strategy_id(int(user_id)))
    try:
        return store.record(
            user_id=int(user_id),
            action=action,
            symbol=sym,
            change_pct=float(change_pct or 0.0),
            metadata=meta,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("psychology_trade_hooks.record_execution_fill: %s", exc)
        return None
