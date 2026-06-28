from __future__ import annotations
"""Celery tasks for factor lifecycle management.

Phase 41: 因子生命周期管理 - 定时任务

Tasks:
- factor_lifecycle_daily_check: Daily lifecycle check for all active factors
- factor_ic_calculation: Daily IC calculation for all factors
- factor_cleanup: Archive deprecated factors older than 30 days
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


def run_factor_lifecycle_daily_check() -> dict[str, Any]:
    """Sync runner for FactorLifecycleManager.run_daily_lifecycle_check."""
    try:
        from app.config import get_settings
        from app.domain.factor_lifecycle import FactorLifecycleManager
        from app.infrastructure.repositories.common.deps import create_factor_repository

        settings = get_settings()
        if not settings.use_mysql:
            return {"status": "skipped", "reason": "MySQL not enabled"}

        repo = create_factor_repository(settings)
        manager = FactorLifecycleManager(repo)
        result = asyncio.run(manager.run_daily_lifecycle_check())
        logger.info("Factor lifecycle daily check completed: %s", result)
        return {"status": "completed", "result": result}
    except Exception as exc:
        logger.error("Factor lifecycle daily check failed: %s", exc, exc_info=True)
        return {"status": "failed", "error": str(exc)}


def run_factor_ic_calculation(factor_id: str | None = None) -> dict[str, Any]:
    """Sync runner for daily IC calculation across active factors."""
    try:
        from app.config import get_settings
        from app.domain.factor_service import FactorService
        from app.infrastructure.repositories.common.deps import create_factor_repository

        settings = get_settings()
        if not settings.use_mysql:
            return {"status": "skipped", "reason": "MySQL not enabled"}

        repo = create_factor_repository(settings)
        service = FactorService(repo)

        async def _run() -> list[dict[str, Any]]:
            if factor_id:
                factor = await repo.get_factor(factor_id)
                factors = [factor] if factor else []
            else:
                factors = await repo.list_factors(status="active", limit=1000)

            results: list[dict[str, Any]] = []
            for factor in factors:
                if not factor:
                    continue
                fid = factor.get("factor_id")
                if not fid:
                    continue
                try:
                    ic_history = await repo.get_ic_history(fid, days=60)
                    if len(ic_history) >= 10:
                        ic_series = [row["ic_value"] for row in ic_history]
                        metrics = await service.update_factor_performance(fid, ic_series)
                        results.append({"factor_id": fid, "metrics": metrics})
                except Exception as inner_exc:
                    logger.error("IC calculation failed for %s: %s", fid, inner_exc)
            return results

        results = asyncio.run(_run())
        return {
            "status": "completed",
            "factors_processed": len(results),
            "results": results,
        }
    except Exception as exc:
        logger.error("Factor IC calculation failed: %s", exc, exc_info=True)
        return {"status": "failed", "error": str(exc)}


def run_factor_cleanup_archived(days_threshold: int = 30) -> dict[str, Any]:
    """Sync runner to archive deprecated factors older than threshold."""
    try:
        from app.config import get_settings
        from app.infrastructure.repositories.common.deps import create_factor_repository

        settings = get_settings()
        if not settings.use_mysql:
            return {"status": "skipped", "reason": "MySQL not enabled"}

        repo = create_factor_repository(settings)
        cutoff_date = (datetime.now() - timedelta(days=days_threshold)).strftime("%Y-%m-%d")

        async def _run() -> int:
            deprecated_factors = await repo.list_factors(status="deprecated", limit=1000)
            archived_count = 0
            for factor in deprecated_factors:
                updated_at = factor.get("updated_at")
                if updated_at and updated_at < cutoff_date:
                    fid = factor.get("factor_id")
                    if not fid:
                        continue
                    await repo.deactivate_factor(
                        fid,
                        reason=f"Auto-archived after {days_threshold} days",
                    )
                    archived_count += 1
            return archived_count

        archived_count = asyncio.run(_run())
        logger.info("Factor cleanup completed: archived %s factors", archived_count)
        return {"status": "completed", "archived_count": archived_count}
    except Exception as exc:
        logger.error("Factor cleanup failed: %s", exc, exc_info=True)
        return {"status": "failed", "error": str(exc)}


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(bind=True, name="factor.lifecycle_daily_check")
    def factor_lifecycle_daily_check(self) -> dict[str, Any]:
        return run_factor_lifecycle_daily_check()

    @_celery.task(bind=True, name="factor.ic_calculation")
    def factor_ic_calculation(self, factor_id: str | None = None) -> dict[str, Any]:
        return run_factor_ic_calculation(factor_id)

    @_celery.task(bind=True, name="factor.cleanup_archived")
    def factor_cleanup_archived(self, days_threshold: int = 30) -> dict[str, Any]:
        return run_factor_cleanup_archived(days_threshold)

else:
    factor_lifecycle_daily_check = None  # type: ignore[misc, assignment]
    factor_ic_calculation = None  # type: ignore[misc, assignment]
    factor_cleanup_archived = None  # type: ignore[misc, assignment]


__all__ = [
    "factor_lifecycle_daily_check",
    "factor_ic_calculation",
    "factor_cleanup_archived",
    "run_factor_lifecycle_daily_check",
    "run_factor_ic_calculation",
    "run_factor_cleanup_archived",
]
