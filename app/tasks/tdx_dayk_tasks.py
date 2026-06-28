from __future__ import annotations

"""TDX 日 K Celery 任务（兼容别名）。

推荐任务名（Beat / 运维）：
- 增量日更：``app.tasks.data_backfill_tasks.sync_incremental_tdx``
- 全量：``app.tasks.data_backfill_tasks.backfill_all_history_tdx``
- 收盘链路：``app.tasks.data_backfill_tasks.scheduled_cn_history_daily``
"""


from typing import Any

from ..celery_app import celery as _celery
from ..core.logger import get_logger
from ..infrastructure.repositories.deps import create_tdx_dayk_sync_service

logger = get_logger(__name__)

@_celery.task(
    name="app.tasks.tdx_dayk_tasks.tdx_dayk_full_sync",
    bind=True,
    acks_late=True,
    time_limit=3600,
    soft_time_limit=3300,
)
def tdx_dayk_full_sync(
    self,
    limit: int | None = None,
    dump_qlib_bin: bool = True,
    dump_max_workers: int = 8,
) -> dict[str, Any]:
    """[别名] 全量 TDX 日 K；推荐 ``data_backfill_tasks.backfill_all_history_tdx``。

    从通达信目录扫描所有股票，导入 MySQL、CSV 和 Qlib。

    - `limit`: 限制处理的股票数量（用于测试）
    - `dump_qlib_bin`: 是否同步到Qlib二进制文件
    - `dump_max_workers`: Qlib同步的最大并发数
    """
    logger.info("TDX dayk full sync started (limit=%s, dump_qlib_bin=%s)", limit, dump_qlib_bin)
    try:
        service = create_tdx_dayk_sync_service()
        result = service.full_sync_from_tdx_dayk(
            limit=limit,
            dump_qlib_bin=dump_qlib_bin,
            dump_max_workers=dump_max_workers,
        )
        logger.info("TDX dayk full sync completed: %s", result.get("stats", {}))
        return result
    except Exception as e:
        logger.exception("TDX dayk full sync failed")
        return {"ok": False, "error": str(e)}


@_celery.task(
    name="app.tasks.tdx_dayk_tasks.tdx_dayk_daily_sync",
    bind=True,
    acks_late=True,
    time_limit=1800,
)
def tdx_dayk_daily_sync(
    self,
    trade_date: str | None = None,
    limit: int | None = None,
    dump_qlib_bin: bool = True,
    dump_max_workers: int = 8,
) -> dict[str, Any]:
    """TDX 日K线当日同步（已改用增量同步）：从MySQL最新日期开始同步通达信新增数据。

    注意：此任务已改为使用增量同步实现，确保数据完整性，不会漏数据。
    原每日同步仅同步单日期数据，可能因文件读取问题漏数据。

    - `trade_date`: 保留参数（向后兼容），实际使用时会忽略
    - `limit`: 限制处理的股票数量（用于测试）
    - `dump_qlib_bin`: 是否同步到Qlib二进制文件
    - `dump_max_workers`: Qlib同步的最大并发数
    """
    logger.info("TDX dayk daily sync started (now using incremental sync, trade_date=%s)", trade_date)
    try:
        service = create_tdx_dayk_sync_service()
        # 使用增量同步替代每日同步，确保数据完整性
        result = service.incremental_sync_from_tdx_dayk(
            start_date=None,  # 从MySQL最新日期开始
            dump_qlib_bin=dump_qlib_bin,
            dump_max_workers=dump_max_workers,
        )
        logger.info("TDX dayk daily sync (incremental) completed: %s", result.get("stats", {}))
        return result
    except Exception as e:
        logger.exception("TDX dayk daily sync failed")
        return {"ok": False, "error": str(e)}


@_celery.task(
    name="app.tasks.tdx_dayk_tasks.tdx_dayk_incremental_sync",
    bind=True,
    acks_late=True,
    time_limit=1800,
)
def tdx_dayk_incremental_sync(
    self,
    start_date: str | None = None,
    dump_qlib_bin: bool = True,
    dump_max_workers: int = 8,
) -> dict[str, Any]:
    """[别名] 增量 TDX 日 K；推荐 ``data_backfill_tasks.sync_incremental_tdx``。

    从 MySQL 最新日期（或指定起始日期）同步通达信新增数据。

    - `start_date`: 指定起始日期（如 "2026-04-24"），None则从MySQL最新日期开始
    - `dump_qlib_bin`: 是否同步到Qlib二进制文件
    - `dump_max_workers`: Qlib同步的最大并发数
    """
    logger.info("TDX dayk incremental sync started (start_date=%s)", start_date)
    try:
        service = create_tdx_dayk_sync_service()
        result = service.incremental_sync_from_tdx_dayk(
            start_date=start_date,
            dump_qlib_bin=dump_qlib_bin,
            dump_max_workers=dump_max_workers,
        )
        logger.info("TDX dayk incremental sync completed: %s", result.get("stats", {}))
        return result
    except Exception as e:
        logger.exception("TDX dayk incremental sync failed")
        return {"ok": False, "error": str(e)}
