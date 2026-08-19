"""Poll TDX TCP quotes during CN session and write to Redis."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.core.runtime_config import get_runtime, get_runtime_int
from app.domain.shared.cn_trading_session import is_cn_tdx_quote_session
from app.domain.shared.pytdx_quote_mapper import pytdx_row_to_quote_payload
from app.infrastructure.realtime.tdx_redis_quote_store import TdxRedisQuoteStore

logger = logging.getLogger(__name__)


def _default_symbols() -> list[str]:
    raw = (get_runtime("TDX_REDIS_SYMBOLS", "") or get_runtime("WS_QUOTE_SYMBOLS", "") or "").strip()
    if raw:
        return [_norm(c) for c in raw.split(",") if c.strip()]
    return ["600519", "000001", "000858", "601318", "300750", "002594", "300308"]


def _norm(code: str) -> str:
    digits = "".join(ch for ch in str(code) if ch.isdigit())
    return digits[-6:].zfill(6) if digits else str(code).strip().upper()


def resolve_tdx_feed_symbols(extra: list[str] | None = None) -> list[str]:
    """Watchlist + env symbols, capped for TCP batch budget."""
    cap = max(20, min(get_runtime_int("TDX_REDIS_MAX_SYMBOLS", 400), 2000))
    seen: set[str] = set()
    out: list[str] = []
    for src in (_default_symbols(), extra or []):
        for c in src:
            nc = _norm(c)
            if len(nc) != 6 or not nc.isdigit() or nc in seen:
                continue
            seen.add(nc)
            out.append(nc)
            if len(out) >= cap:
                return out
    try:
        from app.config import get_settings
        from app.infrastructure.repositories.common.deps import create_watchlist_repository

        wl = create_watchlist_repository(get_settings())
        for sym in wl.list_symbols() or []:
            nc = _norm(str(sym))
            if len(nc) == 6 and nc.isdigit() and nc not in seen:
                seen.add(nc)
                out.append(nc)
            if len(out) >= cap:
                break
    except Exception as exc:  # noqa: BLE001
        logger.debug("watchlist symbols for tdx feed: %s", exc)
    return out[:cap]


class TdxRealtimeFeedService:
    """One poll cycle: TDX batch quotes → Redis."""

    def __init__(self, store: TdxRedisQuoteStore | None = None) -> None:
        self._store = store or TdxRedisQuoteStore()

    def poll_once(self, symbols: list[str] | None = None) -> dict[str, Any]:
        if not is_cn_tdx_quote_session():
            return {"ok": True, "skipped": True, "reason": "outside_session"}
        if not self._store.available:
            return {"ok": False, "error": "redis_unavailable"}
        syms = symbols or resolve_tdx_feed_symbols()
        if not syms:
            return {"ok": True, "rows": 0, "reason": "no_symbols"}

        rows = self._fetch_tdx(syms)
        if not rows:
            return {"ok": False, "error": "tdx_empty", "requested": len(syms)}
        payloads = [pytdx_row_to_quote_payload(r) for r in rows if isinstance(r, dict)]
        written = self._store.write_batch(payloads, source="tdx")
        return {
            "ok": True,
            "requested": len(syms),
            "fetched": len(payloads),
            "written": written,
            "interval_hint_sec": feed_interval_sec(),
        }

    def _fetch_tdx(self, symbols: list[str]) -> list[dict[str, Any]]:
        try:
            from app.infrastructure.adapters.pytdx_market_port_adapter import PytdxMarketPortAdapter
            from app.infrastructure.pytdx.runtime import pytdx_available

            if not pytdx_available():
                return []
            port = PytdxMarketPortAdapter()
            return port.get_security_quotes_for_symbols(symbols)
        except Exception as exc:  # noqa: BLE001
            logger.warning("tdx feed fetch failed: %s", exc, exc_info=True)
            return []


def feed_interval_sec() -> float:
    """Recommended poll interval.

    通达信客户端自选股 Level-1 约 3s 刷新；2s 更激进，5s 偏省资源。
    默认 3s：每批最多 80 只，400 只约 5 批 ≈ 1–1.5s 拉取 + 间隔。
    """
    return max(2.0, min(float(get_runtime_int("TDX_REDIS_QUOTE_INTERVAL_SEC", 3)), 10.0))


def run_feed_loop(*, stop_flag: Any | None = None) -> None:
    """Blocking loop for background thread."""
    svc = TdxRealtimeFeedService()
    idle_sleep = max(30, get_runtime_int("TDX_REDIS_IDLE_SLEEP_SEC", 60))
    while True:
        if stop_flag and stop_flag():
            break
        if is_cn_tdx_quote_session():
            try:
                result = svc.poll_once()
                if not result.get("ok") and not result.get("skipped"):
                    logger.info("tdx feed tick: %s", result)
            except Exception as exc:  # noqa: BLE001
                logger.warning("tdx feed loop: %s", exc, exc_info=True)
            time.sleep(feed_interval_sec())
        else:
            time.sleep(idle_sleep)


__all__ = [
    "TdxRealtimeFeedService",
    "feed_interval_sec",
    "resolve_tdx_feed_symbols",
    "run_feed_loop",
]
