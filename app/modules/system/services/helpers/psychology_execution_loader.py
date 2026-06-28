from __future__ import annotations

"""Load execution_feedback rows into psychology guardian event shape."""

import re
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

_USER_STRATEGY_RE = re.compile(
    r"^(?:retail_user_|user:|u:)(\d+)$",
    re.IGNORECASE,
)


def encode_retail_strategy_id(user_id: int) -> str:
    """Convention for binding QMT/execution rows to a retail user."""
    return f"retail_user_{int(user_id)}"


def parse_user_id_from_strategy_id(strategy_id: str | None) -> int | None:
    if not strategy_id:
        return None
    text = str(strategy_id).strip()
    match = _USER_STRATEGY_RE.match(text)
    if match:
        return int(match.group(1))
    if text.isdigit():
        return int(text)
    return None


def _map_side_to_action(side: str) -> str:
    s = str(side or "").strip().lower()
    if s in ("sell", "short"):
        return "sell"
    return "buy"


def execution_row_to_psychology_event(row: dict[str, Any], *, user_id: int) -> dict[str, Any]:
    side = str(row.get("side") or "buy")
    slippage_pct = float(row.get("slippage_pct") or 0.0)
    change_pct = slippage_pct if side.lower() in ("buy",) else -abs(slippage_pct)
    ts = row.get("fill_time") or row.get("order_time") or ""
    return {
        "action": _map_side_to_action(side),
        "symbol": str(row.get("symbol") or "").strip(),
        "change_pct": change_pct,
        "timestamp": str(ts),
        "metadata": {
            "source": "execution_feedback",
            "order_id": row.get("order_id"),
            "strategy_id": row.get("strategy_id"),
            "execution_quality": row.get("execution_quality"),
            "user_id": user_id,
        },
    }


def load_execution_feedback_events(user_id: int, *, limit: int = 20) -> list[dict[str, Any]]:
    """Best-effort sync read of execution_records for strategy_id bound to user."""
    uid = int(user_id)
    strategy_id = encode_retail_strategy_id(uid)
    try:
        from sqlalchemy import select

        from app.config.settings import AppSettings
        from app.infrastructure.database.models.execution_feedback import ExecutionRecord
        from app.infrastructure.database.orm import create_db_engine, create_session_factory

        settings = AppSettings()
        uri = (settings.database_uri or "").strip()
        if not uri or "sqlite" in uri and ":memory:" in uri:
            return []

        engine = create_db_engine(uri)
        Session = create_session_factory(engine)
        session = Session()
        try:
            stmt = (
                select(ExecutionRecord)
                .where(ExecutionRecord.strategy_id == strategy_id)
                .order_by(ExecutionRecord.order_time.desc())
                .limit(max(limit, 1))
            )
            rows = session.execute(stmt).scalars().all()
            if not rows:
                stmt2 = (
                    select(ExecutionRecord)
                    .order_by(ExecutionRecord.order_time.desc())
                    .limit(limit * 5)
                )
                rows = [
                    r
                    for r in session.execute(stmt2).scalars().all()
                    if parse_user_id_from_strategy_id(r.strategy_id) == uid
                ][:limit]
            out: list[dict[str, Any]] = []
            for rec in rows:
                out.append(
                    execution_row_to_psychology_event(
                        {
                            "order_id": rec.order_id,
                            "symbol": rec.symbol,
                            "side": rec.side,
                            "slippage_pct": rec.slippage_pct,
                            "order_time": rec.order_time.isoformat() if rec.order_time else None,
                            "fill_time": rec.fill_time.isoformat() if rec.fill_time else None,
                            "strategy_id": rec.strategy_id,
                            "execution_quality": rec.execution_quality,
                        },
                        user_id=uid,
                    )
                )
            return out
        finally:
            session.close()
            Session.remove()
    except Exception as exc:
        logger.debug("psychology execution_feedback load: %s", exc)
        return []
