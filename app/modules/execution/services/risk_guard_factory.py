"""Shared RiskGuardService factory (Borderless + QMT share Redis state)."""

from __future__ import annotations

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime, get_runtime_bool
from app.modules.execution.services.risk_guard_service import (
    InMemoryRiskGuardStore,
    LoggingRiskGuardActions,
    RiskGuardService,
    RiskGuardStorePort,
)

logger = get_logger(__name__)

_guard: RiskGuardService | None = None


def _resolve_redis_url() -> str:
    return (
        get_runtime("RISK_GUARD_REDIS_URL", "")
        or get_runtime("TASK_MESSAGE_REDIS_URL", "")
        or get_runtime("REDIS_URL", "")
        or ""
    ).strip()


def build_risk_guard_store() -> RiskGuardStorePort:
    """Prefer Redis when URL is configured; otherwise in-memory."""
    url = _resolve_redis_url()
    if not url:
        return InMemoryRiskGuardStore()
    try:
        from app.infrastructure.trading.risk_guard_redis_store import RedisRiskGuardStore

        return RedisRiskGuardStore(redis_url=url)
    except Exception:
        logger.warning("risk_guard redis store unavailable; using in-memory", exc_info=True)
        return InMemoryRiskGuardStore()


def build_risk_guard_service() -> RiskGuardService:
    from app.infrastructure.notifications.telegram_alerter import make_risk_guard_telegram_callback

    max_dd = float(get_runtime("RISK_GUARD_MAX_DAILY_DRAWDOWN_PCT", "0.05") or "0.05")
    max_stops = int(get_runtime("RISK_GUARD_MAX_CONSECUTIVE_STOP_OUTS", "3") or "3")
    return RiskGuardService(
        store=build_risk_guard_store(),
        actions=LoggingRiskGuardActions(alerter=make_risk_guard_telegram_callback()),
        max_daily_drawdown_pct=max_dd,
        max_consecutive_stop_outs=max_stops,
    )


def get_risk_guard_service(*, force_new: bool = False) -> RiskGuardService:
    """Process-wide singleton so QMT and Borderless share day risk state."""
    global _guard
    if force_new or _guard is None:
        _guard = build_risk_guard_service()
    return _guard


def risk_guard_enabled() -> bool:
    return get_runtime_bool("RISK_GUARD_ENABLED", True)


__all__ = [
    "build_risk_guard_service",
    "build_risk_guard_store",
    "get_risk_guard_service",
    "risk_guard_enabled",
]
