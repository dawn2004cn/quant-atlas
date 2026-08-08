from __future__ import annotations

"""Borderless execution driver registration (CN / US / HK / CRYPTO)."""

from typing import Any

from app.core.runtime_config import get_runtime, get_runtime_bool
from app.infrastructure.execution.borderless_router import BorderlessExecutionRouter
from app.infrastructure.execution.drivers.paper_driver import PaperExecutionDriver
from app.infrastructure.execution.drivers.redis_market_driver import RedisMarketExecutionDriver

_MARKETS = ("CN", "US", "HK", "CRYPTO")
_EXCHANGES: dict[str, str] = {
    "CN": "paper_cn",
    "US": "alpaca_sim",
    "HK": "futu_sim",
    "CRYPTO": "binance",
}


def build_borderless_router(*, mode: str | None = None) -> BorderlessExecutionRouter:
    """Register paper + redis drivers for all supported markets."""
    resolved_mode = (mode or get_runtime("EXECUTION_DEFAULT_MODE", "paper")).strip().lower()
    router = BorderlessExecutionRouter(default_mode=resolved_mode)

    if get_runtime_bool("RISK_GUARD_ENABLED", True):
        from app.modules.execution.services.risk_guard_factory import get_risk_guard_service

        router.set_risk_guard(get_risk_guard_service())

    for market in _MARKETS:
        exchange = _EXCHANGES[market]
        router.register_driver(
            f"paper_{market.lower()}",
            PaperExecutionDriver(market=market, exchange=exchange),
        )

    redis_url = (
        get_runtime("EXECUTION_REDIS_URL", "")
        or get_runtime("TASK_MESSAGE_REDIS_URL", "")
    ).strip()
    fallback = get_runtime_bool("EXECUTION_REDIS_FALLBACK_PAPER", True)
    timeout = float(get_runtime("EXECUTION_REDIS_TIMEOUT", "2.0") or "2.0")
    register_redis = get_runtime_bool("EXECUTION_REGISTER_REDIS_DRIVERS", True)

    if register_redis:
        for market in _MARKETS:
            router.register_driver(
                f"redis_{market.lower()}",
                RedisMarketExecutionDriver(
                    market=market,
                    exchange=_EXCHANGES[market],
                    redis_url=redis_url,
                    fallback_paper=fallback,
                    timeout=timeout,
                ),
            )

    return router


def resolve_bot_execution_gateway(config: dict[str, Any]) -> Any:
    """Pick market-appropriate ExecutionGateway for TradingBotService."""
    symbols = config.get("symbols") or []
    symbol = str(symbols[0] if symbols else config.get("symbol") or "600519")
    market = str(config.get("market") or "").strip().upper() or None
    mode = str(config.get("execution_mode") or config.get("mode") or "").strip().lower() or None
    router = build_borderless_router(mode=mode)
    return router.gateway_for_symbol(symbol, market_hint=market, mode=mode)


__all__ = ["build_borderless_router", "resolve_bot_execution_gateway"]
