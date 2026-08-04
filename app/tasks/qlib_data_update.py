from __future__ import annotations

"""Qlib 数据定时更新：增量 CSV + 增量/自动 qlib.bin。

Celery 任务 ``app.tasks.qlib_data_update.qlib_incremental_pipeline`` 封装 ``update_all_data``（ingest 经
``MultiSourceMarketProvider``，含通达信链路）。Beat 需 ``QLIB_CELERY_BEAT=1``；API ``POST /api/v1/qlib/update_all``。
"""


from pathlib import Path
from typing import Any

from ..application.services.qlib.qlib_pipeline_service import QlibPipelineService
from ..core.logger import get_logger
from ..core.runtime_config import get_runtime
from ..domain.enums import MarketCode
from ..infrastructure.repositories.deps import create_default_qlib_pipeline_service

logger = get_logger(__name__)


def update_all_data(
    symbols: list[str] | None = None,
    *,
    market: MarketCode = MarketCode.CN,
    period: str = "2y",
    max_workers: int = 8,
    pipeline: QlibPipelineService | None = None,
    dump_incremental: bool | None = None,
) -> dict[str, Any]:
    """一键增量：合并写入 ``qlib_export`` CSV，再更新 ``qlib_bin``。

    Celery 已注册任务 ``qlib_incremental_pipeline``（见模块末尾）；Beat 见 ``QLIB_CELERY_BEAT``。

    :param symbols: 显式标的；省略时从 ``config/qlib_pipeline_meta.json`` 的最近一次 ``instruments`` 读取。
    :param dump_incremental: 传给 ``dump_to_qlib_bin``；``None`` 表示自动（已有 bin 则增量）。
    :param pipeline: 自定义服务实例（测试注入）；默认与 Web 相同 ``MultiSourceMarketProvider``。
    :returns: 结构化结果，含 ``ok``、``ingest``、``qlib_bin``；任一步失败 ``ok`` 为 False。
    """
    svc = pipeline or create_default_qlib_pipeline_service()
    resolved = list(symbols or [])
    if not resolved:
        meta_raw = svc.status().get("last_meta") or {}
        resolved = [str(x).strip() for x in (meta_raw.get("instruments") or []) if str(x).strip()]

    if not resolved:
        msg = "update_all_data: 无标的（传入 symbols 或先执行 ingest 写入 meta）"
        logger.error(msg)
        return {"ok": False, "error": "no_symbols", "message": msg}

    logger.info(
        "update_all_data: 开始 ingest merge_existing=True, 标的数=%d, market=%s",
        len(resolved),
        market.value,
    )
    try:
        meta = svc.ingest_symbols(resolved, market, period=period, merge_existing=True)
    except Exception as exc:
        logger.exception("update_all_data: ingest_symbols 失败")
        return {
            "ok": False,
            "error": "ingest_failed",
            "message": str(exc),
            "ingest": None,
            "qlib_bin": None,
        }

    logger.info("update_all_data: ingest 完成，开始 dump_to_qlib_bin incremental=%r", dump_incremental)
    try:
        bin_result = svc.dump_to_qlib_bin(
            max_workers=max_workers,
            overwrite=False,
            incremental=dump_incremental,
        )
    except Exception as exc:
        logger.exception("update_all_data: dump_to_qlib_bin 异常")
        return {
            "ok": False,
            "error": "dump_exception",
            "message": str(exc),
            "ingest": meta.to_dict(),
            "qlib_bin": None,
        }

    bin_ok = bool(bin_result.get("ok"))
    if not bin_ok:
        logger.error(
            "update_all_data: dump_to_qlib_bin 失败 error=%s msg=%s",
            bin_result.get("error"),
            bin_result.get("message"),
        )

    overall = bin_ok
    return {
        "ok": overall,
        "ingest_ok": True,
        "bin_ok": bin_ok,
        "ingest": meta.to_dict(),
        "qlib_bin": bin_result,
    }


def full_qlib_kline_cache_and_bin_if_empty(
    *,
    symbols: list[str] | None = None,
    period: str = "5y",
    max_workers: int = 8,
    pipeline: QlibPipelineService | None = None,
) -> dict[str, Any]:
    """一次性：仅当 ``instance/qlib_export`` 下尚无任何 CSV 时，拉 K 线写 CSV、同步缓存、并 dump qlib_bin（全量）。"""
    from ..domain.shared.symbol_normalizer import SymbolNormalizer

    svc = pipeline or create_default_qlib_pipeline_service()
    export = Path(svc.export_dir)
    csv_files = list(export.glob("*.csv"))
    if csv_files:
        return {"skipped": True, "reason": "qlib_export_has_csv", "csv_count": len(csv_files)}

    raw = (get_runtime("QLIB_FULL_BACKFILL_SYMBOLS", "") or "").strip()
    default_csv = "600519,000001,300750,601318,000858"
    parts = [x.strip() for x in (raw or default_csv).split(",") if x.strip()]
    resolved = list(symbols or [SymbolNormalizer.normalize_code(x) for x in parts])
    if not resolved:
        return {"ok": False, "error": "no_symbols", "skipped": False}

    logger.info("full_qlib_kline_if_empty: ingest %d symbols period=%s", len(resolved), period)
    try:
        meta = svc.ingest_symbols(resolved, MarketCode.CN, period=period, merge_existing=False)
    except Exception as exc:
        logger.exception("full_qlib_kline_if_empty ingest failed")
        return {"ok": False, "error": "ingest_failed", "message": str(exc), "skipped": False}

    try:
        bin_result = svc.dump_to_qlib_bin(
            max_workers=max_workers,
            overwrite=False,
            incremental=False,
        )
    except Exception as exc:
        logger.exception("full_qlib_kline_if_empty dump failed")
        return {
            "ok": False,
            "error": "dump_exception",
            "message": str(exc),
            "ingest": meta.to_dict(),
            "skipped": False,
        }

    return {
        "ok": bool(bin_result.get("ok")),
        "skipped": False,
        "ingest": meta.to_dict(),
        "qlib_bin": bin_result,
    }


from ..celery_app import celery as _celery

if _celery is not None:

    @_celery.task(name="app.tasks.qlib_data_update.csv_to_qlib_incremental_sync")
    def csv_to_qlib_incremental_sync(
        max_workers: int = 8,
        dump_incremental: bool | None = True,
    ) -> dict[str, Any]:
        """``qlib_export`` CSV → ``qlib_bin``（历史入库推荐路径）。"""
        svc = create_default_qlib_pipeline_service()
        logger.info("Starting csv_to_qlib_incremental_sync...")
        return svc.dump_to_qlib_bin(
            max_workers=max_workers,
            incremental=dump_incremental,
        )

    @_celery.task(name="app.tasks.qlib_data_update.mysql_to_qlib_full_sync")
    def mysql_to_qlib_full_sync() -> dict[str, Any]:
        """Deprecated shim：原 MySQL→bin 已下线，改为 CSV→bin。"""
        logger.warning("mysql_to_qlib_full_sync retired → csv_to_qlib_incremental_sync")
        return csv_to_qlib_incremental_sync(dump_incremental=False)

    @_celery.task(name="app.tasks.qlib_data_update.mysql_to_qlib_incremental_sync")
    def mysql_to_qlib_incremental_sync(
        limit_stocks: int | None = None,
        days_lookback: int | None = None,
    ) -> dict[str, Any]:
        """Deprecated shim：原 MySQL→bin 已下线，改为 CSV→bin。"""
        _ = (limit_stocks, days_lookback)
        logger.warning("mysql_to_qlib_incremental_sync retired → csv_to_qlib_incremental_sync")
        return csv_to_qlib_incremental_sync(dump_incremental=True)

    @_celery.task(name="app.tasks.qlib_data_update.qlib_incremental_pipeline")
    def qlib_incremental_pipeline(
        period: str = "2y",
        max_workers: int = 8,
        dump_incremental: bool | None = None,
    ) -> dict[str, Any]:
        """通达信等多源 ingest → ``qlib_export`` CSV → ``qlib_bin``（与 Web 管线一致）。"""
        return update_all_data(
            period=period,
            max_workers=max_workers,
            dump_incremental=dump_incremental,
        )

    @_celery.task(name="app.tasks.qlib_data_update.qlib_full_backfill_if_empty")
    def qlib_full_backfill_if_empty(
        period: str = "5y",
        max_workers: int = 8,
    ) -> dict[str, Any]:
        """无 CSV 存量时全量种子 K 线 + qlib_bin；已有 CSV 则跳过。"""
        return full_qlib_kline_cache_and_bin_if_empty(period=period, max_workers=max_workers)

else:
    csv_to_qlib_incremental_sync = None  # type: ignore[misc, assignment]
    mysql_to_qlib_full_sync = None  # type: ignore[misc, assignment]
    mysql_to_qlib_incremental_sync = None  # type: ignore[misc, assignment]
    qlib_incremental_pipeline = None  # type: ignore[misc, assignment]
    qlib_full_backfill_if_empty = None  # type: ignore[misc, assignment]
