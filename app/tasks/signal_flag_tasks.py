from __future__ import annotations
"""信号旗股票池扫描：支持分布式并发执行"""


from datetime import datetime
from typing import Any

from celery import chord

from ..application.services.strategy.signal_flag_service import SignalFlagScannerService
from ..celery_app import celery as _celery
from ..config import get_settings
from ..core.logger import get_logger
from ..domain.enums import MarketCode
from ..infrastructure.repositories.deps import create_signal_flag_pool_repository, create_stock_cache
from .task_wiring import (
    create_stock_application_service,
    get_task_message_store,
)


logger = get_logger(__name__)


def _scanner_service() -> SignalFlagScannerService:
    settings = get_settings()
    repo = create_signal_flag_pool_repository(settings)
    return SignalFlagScannerService(
        stock_service=create_stock_application_service(),
        stock_cache=create_stock_cache(),
        repository=repo,
        enable_qlib=settings.enable_qlib,
    )


def _push_done(task_id: str, summary_dict: dict[str, Any]) -> None:
    try:
        get_task_message_store().push(
            event="task_succeeded",
            task_id=task_id,
            task_name="app.tasks.signal_flag_tasks.signal_flag_pool_scan",
            detail=(summary_dict.get("message") or "信号旗扫描完成")[:2000],
            meta={
                "pool_date": summary_dict.get("pool_date"),
                "scanned": summary_dict.get("scanned"),
                "hits": summary_dict.get("hits"),
                "persisted": summary_dict.get("persisted"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("signal_flag task message push skipped: %s", exc)


if _celery is not None:

    @_celery.task(name="app.tasks.signal_flag_tasks.scan_batch_worker_task")
    def scan_batch_worker_task(
        universe_chunk: list[dict[str, Any]],
        market_val: str,
        pool_date: str,
        lookback_days: int
    ) -> list[dict[str, Any]]:
        """分布Worker：对切片标的执行多策略扫描"""
        svc = _scanner_service()
        return svc.scan_batch(universe_chunk, MarketCode(market_val), pool_date, lookback_days)

    @_celery.task(name="app.tasks.signal_flag_tasks.finalize_scan_callback")
    def finalize_scan_callback(
        results_of_groups: list[list[dict[str, Any]]],
        pool_date: str,
        scanned_count: int,
        task_id: str
    ) -> dict[str, Any]:
        """聚合所有分布式子任务结果并写入数据库"""
        all_hits = [item for sublist in results_of_groups for item in sublist]
        svc = _scanner_service()
        n = svc.finalize_pool(pool_date, all_hits)

        summary = {
            "pool_date": pool_date,
            "scanned": scanned_count,
            "hits": len(all_hits),
            "persisted": n,
            "message": f"分布式扫描完成：共扫 {scanned_count} 只，命中 {len(all_hits)} 条",
            "_suppress_default_task_message": True
        }
        _push_done(task_id, summary)
        return summary

    @_celery.task(bind=True, name="app.tasks.signal_flag_tasks.signal_flag_pool_backfill")
    def signal_flag_pool_backfill(
        self,
        start_date: str = "2020-01-01",
        end_date: str | None = None,
        max_stocks: int = 800,
        lookback_days: int = 160,
        limit_days: int = 0,
    ) -> dict[str, Any]:
        """历史回填：逐日扫描并入库，走 Celery Worker 异步执行。"""
        from datetime import timedelta

        from celery import current_task
        req = getattr(current_task, "request", None)
        task_id = str(getattr(req, "id", "") or "backfill")
        svc = _scanner_service()

        d0 = (end_date or datetime.now().strftime("%Y-%m-%d"))[:10]
        end_dt = datetime.strptime(d0, "%Y-%m-%d")
        start_dt = datetime.strptime(start_date[:10], "%Y-%m-%d")
        total_days = (end_dt - start_dt).days
        if limit_days > 0:
            start_dt = end_dt - timedelta(days=min(limit_days, total_days))
            total_days = (end_dt - start_dt).days

        scanned_total = 0
        hit_total = 0
        current = start_dt
        day_count = 0
        errors: list[str] = []

        while current <= end_dt:
            ds = current.strftime("%Y-%m-%d")
            try:
                universe = svc.get_scan_universe(MarketCode.CN, max_stocks)
                hits = svc.scan_batch(universe, MarketCode.CN, ds, lookback_days)
                svc.finalize_pool(ds, hits)
                scanned_total += len(universe)
                hit_total += len(hits)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{ds}: {exc}")
            day_count += 1
            if day_count % 20 == 0:
                self.update_state(state="PROGRESS", meta={"progress": min(99, int(day_count / max(1, total_days) * 100)), "day": ds})
            current += timedelta(days=1)

        result = {
            "ok": True,
            "start_date": start_date,
            "end_date": d0,
            "days_scanned": day_count,
            "total_scanned": scanned_total,
            "total_hits": hit_total,
            "errors": errors[:20],
            "_suppress_default_task_message": True,
        }
        _push_done(task_id, result)
        return result

    @_celery.task(name="app.tasks.signal_flag_tasks.signal_flag_pool_scan")
    def signal_flag_pool_scan(
        pool_date: str | None = None,
        max_stocks: int = 800,
        lookback_days: int = 160,
        batch_size: int = 80
    ) -> dict[str, Any]:
        """分布式编排：获取 Universe -> 分片 -> 分发Worker -> 回调聚合"""
        from celery import current_task
        req = getattr(current_task, "request", None)
        task_id = str(getattr(req, "id", "") or "signal-flag-scan")

        svc = _scanner_service()
        d0 = (pool_date or datetime.now().strftime("%Y-%m-%d"))[:10]
        universe = svc.get_scan_universe(MarketCode.CN, max_stocks)

        if not universe:
            return {"ok": True, "scanned": 0, "message": "No stocks in universe to scan."}

        # 创建分布式任务链 (Chord)
        chunks = [universe[i : i + batch_size] for i in range(0, len(universe), batch_size)]

        header = [
            scan_batch_worker_task.s(chunk, MarketCode.CN.value, d0, int(lookback_days))
            for chunk in chunks
        ]
        callback = finalize_scan_callback.s(d0, len(universe), task_id)

        chord(header)(callback)

        return {
            "mode": "distributed",
            "task_id": task_id,
            "batches": len(chunks),
            "total_universe": len(universe),
            "message": f"已分发 {len(chunks)} 个分布式扫描任务",
        }


def run_signal_flag_scan_sync(
    pool_date: str | None = None,
    max_stocks: int = 800,
    lookback_days: int = 160
) -> dict[str, Any]:
    """同步版本的信号旗扫描，不依赖 Celery 队列，供其他任务串行调用"""
    svc = _scanner_service()
    d0 = (pool_date or datetime.now().strftime("%Y-%m-%d"))[:10]
    universe = svc.get_scan_universe(MarketCode.CN, max_stocks)

    if not universe:
        return {"pool_date": d0, "scanned": 0, "hits": 0, "message": "No stocks to scan."}

    # 执行扫描
    hits = svc.scan_batch(universe, MarketCode.CN, d0, int(lookback_days))

    # 写入池并收尾
    n = svc.finalize_pool(d0, hits)

    return {
        "pool_date": d0,
        "scanned": len(universe),
        "hits": len(hits),
        "persisted": n,
        "message": f"同步扫描完成：共扫描 {len(universe)} 只，命中 {len(hits)} 条",
    }

    # ... (Keep backfill for now, or also distributed-ize it)
