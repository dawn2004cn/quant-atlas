from __future__ import annotations
"""Batch processing service for handling multiple stocks."""


import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, TypeVar

from app.core.logger import get_logger
from app.infrastructure.memory_cache import get_cache

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class BatchResult:
    """Result of batch processing."""
    total: int
    success: int
    failed: int
    results: list[Any]
    errors: list[dict]
    elapsed_seconds: float


class BatchProcessor:
    """Batch processor for parallel stock operations."""

    def __init__(self, max_workers: int = 10):
        self._max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cache = get_cache()
        logger.info(f"BatchProcessor initialized with {max_workers} workers")

    async def process_stocks_async(
        self,
        stocks: list[dict[str, Any]],
        process_fn: Callable[[dict], Any],
        use_cache: bool = True,
    ) -> BatchResult:
        """Process stocks asynchronously."""
        start_time = datetime.now()
        results = []
        errors = []
        success = 0
        failed = 0

        for stock in stocks:
            code = stock.get("code", "")

            try:
                if use_cache:
                    cache_key = f"batch:{process_fn.__name__}:{code}"
                    cached_result = self._cache.get(cache_key)
                    if cached_result is not None:
                        results.append(cached_result)
                        success += 1
                        continue

                result = await asyncio.to_thread(process_fn, stock)
                results.append(result)

                if use_cache:
                    self._cache.set(cache_key, result, ttl=60)

                success += 1

            except Exception as e:
                logger.error(f"Error processing {code}: {e}")
                errors.append({"code": code, "error": str(e)})
                failed += 1

        elapsed = (datetime.now() - start_time).total_seconds()

        return BatchResult(
            total=len(stocks),
            success=success,
            failed=failed,
            results=results,
            errors=errors,
            elapsed_seconds=elapsed,
        )

    async def process_in_chunks(
        self,
        items: list[Any],
        process_fn: Callable[[Any], Any],
        chunk_size: int = 50,
    ) -> list[Any]:
        """Process items in chunks."""
        results = []

        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            chunk_results = await self.process_stocks_async(
                chunk,
                process_fn,
                use_cache=False,
            )
            results.extend(chunk_results.results)

        return results

    def process_parallel(
        self,
        items: list[Any],
        process_fn: Callable[[Any], Any],
    ) -> list[Any]:
        """Process items in parallel using thread pool."""
        futures = [self._executor.submit(process_fn, item) for item in items]
        results = []
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                logger.error(f"Error in parallel processing: {e}")
                results.append({"error": str(e)})
        return results

    def shutdown(self):
        """Shutdown the executor."""
        self._executor.shutdown(wait=True)


_batch_processor: BatchProcessor | None = None


def get_batch_processor() -> BatchProcessor:
    """Get global batch processor."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    return _batch_processor


class BatchOperation:
    """Helper class for batch operations."""

    @staticmethod
    async def fetch_quotes(codes: list[str], provider: Any) -> BatchResult:
        """Batch fetch quotes."""
        processor = get_batch_processor()

        def fetch_one(code: str) -> dict:
            return provider.get_realtime_quote(code) or {}

        stocks = [{"code": c} for c in codes]
        return await processor.process_stocks_async(stocks, lambda s: fetch_one(s["code"]))

    @staticmethod
    async def analyze_stocks(codes: list[str], analysis_service: Any) -> BatchResult:
        """Batch analyze stocks."""
        processor = get_batch_processor()

        stocks = [{"code": c} for c in codes]
        return await processor.process_stocks_async(
            stocks,
            lambda s: analysis_service.analyze_stock(s["code"]),
            use_cache=True,
        )

    @staticmethod
    async def scan_stocks(codes: list[str], scanner_service: Any, scan_type: str = "breakout") -> BatchResult:
        """Batch scan stocks."""
        processor = get_batch_processor()

        stocks = [{"code": c} for c in codes]
        return await processor.process_stocks_async(
            stocks,
            lambda s: scanner_service.scan_stock(s["code"], scan_type),
            use_cache=True,
        )


__all__ = [
    "BatchResult",
    "BatchProcessor",
    "get_batch_processor",
    "BatchOperation",
]