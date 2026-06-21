from __future__ import annotations
"""个股新闻归档：批量强制刷新（Celery）

对给定代码列表逐只调用 ``ToolFacadeService.news_bundle(..., force_refresh=True)``，写``news_archive.db``
代码来源：任务参``codes`` > 环境变量 ``NEWS_BACKFILL_CODES``（逗号分隔 自选股> 默认示例代码

默认 **不上 Beat**；可``NEWS_ARCHIVE_BACKFILL_BEAT=1`` 在周日凌晨跑一次（``app.celery_app``）
"""


import time
from typing import Any

from ..application.services.data.basic_market_data_service import BasicMarketDataService
from ..application.services.tool_facade_service import ToolFacadeService
from ..celery_app import celery as _celery
from ..config import get_settings
from ..core.runtime_config import get_runtime, get_runtime_float, get_runtime_int
from ..domain.enums import MarketCode
from ..infrastructure.repositories.deps import create_news_archive_repository, create_watchlist_repository
from .task_wiring import create_stock_application_service, get_market_data_provider


def _resolve_news_backfill_codes(codes: list[str] | None) -> list[str]:
    if codes:
        raw = ",".join(str(c).strip() for c in codes if str(c).strip())
    else:
        raw = (get_runtime("NEWS_BACKFILL_CODES", "") or "").strip()
    if raw:
        return BasicMarketDataService._parse_code_list(raw, default_csv="600519")
    s = get_settings()
    try:
        wl = create_watchlist_repository(s)
        syms = wl.list_symbols()
    except RuntimeError as e:
        if "session_factory" in str(e):
            syms = []
        else:
            raise
    if syms:
        out: list[str] = []
        for x in syms:
            d = "".join(ch for ch in str(x) if ch.isdigit())
            if len(d) >= 6:
                out.append(d[-6:].zfill(6))
        if out:
            return sorted(set(out))
    return BasicMarketDataService._parse_code_list(None, default_csv="600519,000001,300750")


def _news_archive_backfill_max_codes() -> int:
    v = get_runtime_int("NEWS_BACKFILL_MAX_CODES", 200)
    return max(1, min(v, 2000))


def _news_backfill_sleep_sec() -> float:
    v = get_runtime_float("NEWS_BACKFILL_SLEEP_SEC", 0.45)
    return max(0.05, min(v, 30.0))


def _tool_facade_service() -> ToolFacadeService:
    s = get_settings()
    market_provider = get_market_data_provider()
    stock_service = create_stock_application_service()
    archive = create_news_archive_repository(s)
    return ToolFacadeService(market_provider, stock_service, archive=archive)


def run_news_archive_force_refresh_for_codes(
    codes: list[str] | None = None,
    *,
    market: str = MarketCode.CN.value,
    sleep_sec: float | None = None,
    max_codes: int | None = None,
) -> dict[str, Any]:
    """对代码列表强制拉取新闻快照并写入归档（供 Celery 与单测调用）"""
    from ..config import BASE_DIR

    resolved = _resolve_news_backfill_codes(codes)
    cap = max_codes if max_codes is not None else _news_archive_backfill_max_codes()
    resolved = resolved[:cap]
    delay = sleep_sec if sleep_sec is not None else _news_backfill_sleep_sec()
    facade = _tool_facade_service()
    mc = MarketCode(str(market or MarketCode.CN.value))
    details: list[dict[str, Any]] = []
    refreshed = 0
    errors: list[dict[str, str]] = []
    for sym in resolved:
        try:
            r = facade.news_bundle(sym, mc, force_refresh=True, cache_max_age_hours=0.25)
            if r.get("remote_refreshed"):
                refreshed += 1
            details.append(
                {
                    "symbol": sym,
                    "archive_total_rows": r.get("archive_total_rows"),
                    "remote_refreshed": r.get("remote_refreshed"),
                },
            )
        except Exception as exc:  # noqa: BLE001
            errors.append({"symbol": sym, "error": str(exc)[:500]})
        time.sleep(delay)
    return {
        "ok": True,
        "market": mc.value,
        "codes_total": len(resolved),
        "remote_refreshed_symbols": refreshed,
        "errors": errors,
        "details_tail": details[-8:],
        "base_dir": str(BASE_DIR),
    }


if _celery is not None:

    @_celery.task(name="app.tasks.news_backfill_tasks.backfill_news_archive_for_codes")
    def backfill_news_archive_for_codes(
        codes: list[str] | None = None,
        market: str = MarketCode.CN.value,
        sleep_sec: float | None = None,
        max_codes: int | None = None,
    ) -> dict[str, Any]:
        """新闻归档：批``force_refresh``；代码见模块文档"""
        return run_news_archive_force_refresh_for_codes(
            codes=codes,
            market=market,
            sleep_sec=sleep_sec,
            max_codes=max_codes,
        )

    @_celery.task(name="app.tasks.news_backfill_tasks.scheduled_news_daily")
    def scheduled_news_daily() -> dict[str, Any]:
        """每日新闻归档刷新：默认取自+ 行情缓存N（由 ``NEWS_BACKFILL_MAX_CODES`` 控制）"""
        return run_news_archive_force_refresh_for_codes(
            codes=None,
            market=MarketCode.CN.value,
            sleep_sec=None,
            max_codes=None,
        )

else:
    backfill_news_archive_for_codes = None  # type: ignore[misc, assignment]
    scheduled_news_daily = None  # type: ignore[misc, assignment]

