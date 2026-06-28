from __future__ import annotations
"""一次性存量回填与财报日更（Celery）

- 龙虎/ 财报快照：仅当库内无对应存量时执行全量回填（``backfill_*_if_empty``）
- **独立强制全量**：``backfill_longhu_full``（无视已有龙虎榜）、``backfill_yanbao_full``（加深单分类行数），
  默认 **不上 Beat**，请按需 ``delay()`` 或运维触发，避免与「仅空库」任务重复打源站
- 财报日更：从 qlib meta instruments 解析代码（或 ``FINANCIAL_DAILY_CODES``），覆盖刷新 ``cn_financial_stash``
"""


from typing import Any


from ..core.logger import get_logger
from ..application.services.data.basic_market_data_service import BasicMarketDataService
from ..infrastructure.repositories.deps import (
    create_default_qlib_pipeline_service,
    create_tdx_dayk_sync_service,
)
from ..celery_app import celery as _celery
from ..core.runtime_config import get_runtime, get_runtime_int
from ..domain.enums import MarketCode
from ..domain.shared.qlib_symbol_map import qlib_instrument_to_symbol
from .qlib_data_update import full_qlib_kline_cache_and_bin_if_empty
from .task_wiring import create_basic_market_data_service

logger = get_logger(__name__)

def _basic_service() -> BasicMarketDataService:
    return create_basic_market_data_service()


def _yanbao_full_max_rows() -> int:
    v = get_runtime_int("YANBAO_FULL_MAX_ROWS", 500)
    return max(1, min(v, 800))


def _financial_daily_codes() -> list[str]:
    svc = create_default_qlib_pipeline_service()
    inst = (svc.status().get("last_meta") or {}).get("instruments") or []
    codes: list[str] = []
    for x in inst:
        xs = str(x).strip()
        if not xs:
            continue
        try:
            codes.append(qlib_instrument_to_symbol(xs, MarketCode.CN))
        except Exception:  # noqa: BLE001
            continue
    cap = get_runtime_int("FINANCIAL_DAILY_MAX_CODES", 120)
    if codes:
        return codes[: max(1, cap)]
    return BasicMarketDataService._parse_code_list(
        get_runtime("FINANCIAL_DAILY_CODES", "") or None,
        default_csv="600519,000001,300750",
    )


if _celery is not None:

    @_celery.task(name="app.tasks.data_backfill_tasks.backfill_longhu_if_empty")
    def backfill_longhu_if_empty(
        years: int = 3,
        chunk_days: int = 55,
        sleep_sec: float = 0.35,
    ) -> dict[str, Any]:
        """龙虎榜：``longhu_em`` 无行时按年分段回填"""
        return _basic_service().run_longhu_full_historical_if_no_stock(
            years=years,
            chunk_days=chunk_days,
            sleep_sec=sleep_sec,
        )

    @_celery.task(name="app.tasks.data_backfill_tasks.backfill_longhu_full")
    def backfill_longhu_full(
        years: int = 3,
        chunk_days: int = 55,
        sleep_sec: float = 0.35,
    ) -> dict[str, Any]:
        """Longhu: force full upsert by year windows."""
        return _basic_service().run_longhu_full_historical_force(
            years=years,
            chunk_days=chunk_days,
            sleep_sec=sleep_sec,
        )

    @_celery.task(name="app.tasks.data_backfill_tasks.backfill_yanbao_full")
    def backfill_yanbao_full(
        max_rows_per_category: int | None = None,
    ) -> dict[str, Any]:
        """Yanbao: full Eastmoney HTML scrape."""
        if max_rows_per_category is not None:
            try:
                cap = int(max_rows_per_category)
            except (TypeError, ValueError):
                cap = _yanbao_full_max_rows()
        else:
            cap = _yanbao_full_max_rows()
        cap = max(1, min(cap, 800))
        return _basic_service().ingest_yanbao_eastmoney_html(max_rows_per_category=cap)

    @_celery.task(name="app.tasks.data_backfill_tasks.backfill_all_history_tdx")
    def backfill_all_history_tdx(limit: int | None = None) -> dict[str, Any]:
        """[TDX专用] 历史全量：TDX 日K目录 MySQL + qlib_export(CSV) + qlib_bin"""
        logger.info("Starting backfill_all_history_tdx (TDX dayk -> mysql/csv/qlib)...")
        return create_tdx_dayk_sync_service().full_sync_from_tdx_dayk(limit=limit)

    @_celery.task(name="app.tasks.data_backfill_tasks.sync_today_history_tdx")
    def sync_today_history_tdx(trade_date: str | None = None, limit: int | None = None) -> dict[str, Any]:
        """[TDX专用] 日更：与增量同步一致，从 MySQL 最新日期补全至 TDX（trade_date 仅兼容保留）。"""
        logger.info("Starting sync_today_history_tdx (TDX dayk incremental, trade_date=%s)...", trade_date)
        return create_tdx_dayk_sync_service().incremental_sync_from_tdx_dayk(
            trade_date=trade_date,
            limit=limit,
        )

    @_celery.task(name="app.tasks.data_backfill_tasks.sync_incremental_tdx")
    def sync_incremental_tdx(
        limit: int | None = None,
        dump_qlib_bin: bool = True,
        dump_max_workers: int = 8,
    ) -> dict[str, Any]:
        """[TDX 推荐] 增量同步：MySQL 最新日期 → TDX lday → MySQL + CSV（可选同步 qlib_bin）。"""
        logger.info(
            "Starting sync_incremental_tdx (dump_qlib_bin=%s, limit=%s)...",
            dump_qlib_bin,
            limit,
        )
        return create_tdx_dayk_sync_service().incremental_sync_from_tdx_dayk(
            limit=limit,
            dump_qlib_bin=dump_qlib_bin,
            dump_max_workers=dump_max_workers,
        )

    @_celery.task(name="app.tasks.data_backfill_tasks.scheduled_cn_history_daily")
    def scheduled_cn_history_daily(
        limit: int | None = None,
        dump_max_workers: int = 8,
    ) -> dict[str, Any]:
        """收盘后日更链路：TDX 增量（不写 bin）→ MySQL → qlib_bin。"""
        logger.info("scheduled_cn_history_daily: TDX incremental (no inline bin dump)...")
        tdx_result = create_tdx_dayk_sync_service().incremental_sync_from_tdx_dayk(
            limit=limit,
            dump_qlib_bin=False,
            dump_max_workers=dump_max_workers,
        )
        if not tdx_result.get("ok", False):
            return {
                "ok": False,
                "stage": "tdx_incremental",
                "tdx": tdx_result,
                "qlib_bin": None,
            }

        from .qlib_data_update import mysql_to_qlib_incremental_sync

        logger.info("scheduled_cn_history_daily: mysql_to_qlib_incremental_sync...")
        bin_result = mysql_to_qlib_incremental_sync()
        overall_ok = bool(bin_result.get("ok"))
        return {
            "ok": overall_ok,
            "stage": "done" if overall_ok else "qlib_bin",
            "tdx": tdx_result,
            "qlib_bin": bin_result,
        }

    @_celery.task(name="app.tasks.data_backfill_tasks.backfill_financial_stash_if_empty")
    def backfill_financial_stash_if_empty() -> dict[str, Any]:
        """财报快照：仅 ``cn_financial_stash`` 为空时全量写入（代码``FINANCIAL_FULL_BACKFILL_CODES``）"""
        return _basic_service().run_financial_full_stash_if_empty()

    @_celery.task(name="app.tasks.data_backfill_tasks.backfill_qlib_kline_if_empty")
    def backfill_qlib_kline_if_empty(
        period: str = "5y",
        max_workers: int = 8,
    ) -> dict[str, Any]:
        """通达K 线：``qlib_export`` CSV 时种子全+ dump qlib_bin"""
        return full_qlib_kline_cache_and_bin_if_empty(period=period, max_workers=max_workers)

    @_celery.task(name="app.tasks.data_backfill_tasks.scheduled_financial_stash_refresh")
    def scheduled_financial_stash_refresh() -> dict[str, Any]:
        """每日：按 meta / 环境变量刷新财报快照行"""
        codes = _financial_daily_codes()
        if not codes:
            return {"ok": False, "error": "no_codes", "rows": 0}
        return _basic_service().refresh_financial_stash_for_codes(codes)

else:
    backfill_longhu_if_empty = None  # type: ignore[misc, assignment]
    backfill_longhu_full = None  # type: ignore[misc, assignment]
    backfill_yanbao_full = None  # type: ignore[misc, assignment]
    backfill_financial_stash_if_empty = None  # type: ignore[misc, assignment]
    backfill_qlib_kline_if_empty = None  # type: ignore[misc, assignment]
    scheduled_financial_stash_refresh = None  # type: ignore[misc, assignment]
    backfill_all_history_tdx = None  # type: ignore[misc, assignment]
    sync_today_history_tdx = None  # type: ignore[misc, assignment]
    sync_incremental_tdx = None  # type: ignore[misc, assignment]
    scheduled_cn_history_daily = None  # type: ignore[misc, assignment]
