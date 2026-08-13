from __future__ import annotations

"""行情扫描 Celery 任务：支持分布式切片执行。"""


from typing import Any

from ..application.services.strategy.scanner_service import ScannerApplicationService
from ..celery_app import celery as _celery
from ..infrastructure.repositories.deps import create_stock_cache
from .task_wiring import get_market_data_provider


def _scanner_service() -> ScannerApplicationService:
    return ScannerApplicationService(get_market_data_provider(), create_stock_cache())


def scanner_core_tick() -> dict[str, Any]:
    return _scanner_service().run_core_scan_once().model_dump()


def process_quote_batch_task(symbols: list[str]) -> bool:
    """分布式 Worker：处理一小批标的的行情更新。"""
    _scanner_service().process_quote_batch(symbols)
    return True


def scanner_distributed_rotation(batch_size: int = 100) -> dict[str, Any]:
    """分布式编排：获取全量代码并分发给多个 Worker。"""
    from celery import group

    svc = _scanner_service()
    symbols = svc.get_rotation_symbols()

    if not symbols:
        svc.refresh_market_sentiment()
        return {"ok": True, "count": 0, "message": "empty_rotation"}

    chunks = [symbols[i : i + batch_size] for i in range(0, len(symbols), batch_size)]
    if _celery is None:
        for chunk in chunks:
            process_quote_batch_task(chunk)
        return {
            "ok": True,
            "total_symbols": len(symbols),
            "batches": len(chunks),
            "message": f"同步执行 {len(chunks)} 个行情扫描批次 (batch_size={batch_size})。",
        }

    job = group(process_quote_batch_task.s(chunk) for chunk in chunks)
    job.apply_async()

    return {
        "ok": True,
        "total_symbols": len(symbols),
        "batches": len(chunks),
        "message": f"已分发 {len(chunks)} 个行情扫描子任务 (batch_size={batch_size})。",
    }


def scanner_rotation_tick() -> dict[str, Any]:
    """兼容旧入口，默认执行分布式旋转。"""
    return scanner_distributed_rotation()


if _celery is not None:
    scanner_core_tick = _celery.task(name="app.tasks.scanner_tasks.scanner_core_tick")(scanner_core_tick)
    process_quote_batch_task = _celery.task(
        name="app.tasks.scanner_tasks.process_quote_batch_task",
        rate_limit="30/m",
        time_limit=120,
    )(process_quote_batch_task)
    scanner_distributed_rotation = _celery.task(
        name="app.tasks.scanner_tasks.scanner_distributed_rotation"
    )(scanner_distributed_rotation)
    scanner_rotation_tick = _celery.task(name="app.tasks.scanner_tasks.scanner_rotation_tick")(
        scanner_rotation_tick
    )
