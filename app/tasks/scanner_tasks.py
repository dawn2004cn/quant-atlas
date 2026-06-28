from __future__ import annotations
"""行情扫描 Celery 任务：支持分布式切片执行。"""


from typing import Any
from celery import group

from ..application.services.strategy.scanner_service import ScannerApplicationService
from ..celery_app import celery as _celery
from ..infrastructure.repositories.deps import create_stock_cache
from .task_wiring import get_market_data_provider


def _scanner_service() -> ScannerApplicationService:
    return ScannerApplicationService(get_market_data_provider(), create_stock_cache())


if _celery is not None:

    @_celery.task(name="app.tasks.scanner_tasks.scanner_core_tick")
    def scanner_core_tick() -> dict[str, Any]:
        return _scanner_service().run_core_scan_once().model_dump()

    @_celery.task(
        name="app.tasks.scanner_tasks.process_quote_batch_task",
        bind=True,
        rate_limit="30/m",  # 限制每分钟执行次数，防止触发上游 API 频控
        time_limit=120,     # 单个批次必须在 120 秒内完成
    )
    def process_quote_batch_task(self, symbols: list[str]) -> bool:
        """分布式 Worker：处理一小批标的的行情更新。"""
        _scanner_service().process_quote_batch(symbols)
        return True

    @_celery.task(name="app.tasks.scanner_tasks.scanner_distributed_rotation")
    def scanner_distributed_rotation(batch_size: int = 100) -> dict[str, Any]:
        """分布式编排：获取全量代码并分发给多个 Worker。"""
        svc = _scanner_service()
        symbols = svc.get_rotation_symbols()

        if not symbols:
            svc.refresh_market_sentiment()
            return {"ok": True, "count": 0, "message": "empty_rotation"}

        # 分片并创建任务组
        chunks = [symbols[i : i + batch_size] for i in range(0, len(symbols), batch_size)]
        job = group(process_quote_batch_task.s(chunk) for chunk in chunks)
        job.apply_async()

        return {
            "ok": True,
            "total_symbols": len(symbols),
            "batches": len(chunks),
            "message": f"已分发 {len(chunks)} 个行情扫描子任务 (batch_size={batch_size})。"
        }

    @_celery.task(name="app.tasks.scanner_tasks.scanner_rotation_tick")
    def scanner_rotation_tick() -> dict[str, Any]:
        """兼容旧入口，默认执行分布式旋转。"""
        return scanner_distributed_rotation()

else:
    scanner_core_tick = None  # type: ignore
    process_quote_batch_task = None  # type: ignore
    scanner_distributed_rotation = None  # type: ignore
    scanner_rotation_tick = None  # type: ignore
