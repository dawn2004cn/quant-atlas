from __future__ import annotations

"""Celery tick: refresh the delayed CN quote book into Redis."""

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


def run_cn_quote_book_refresh(*, force: bool = False) -> dict[str, Any]:
    from app.modules.market_data.services.cn_quote_book import refresh_book_reason
    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

    reason = refresh_book_reason(force=force)
    if reason is None:
        return {"ok": True, "skipped": True, "reason": "outside_session_with_book"}

    from app.infrastructure.providers.cn_industry_provider import CnIndustryProvider
    from app.infrastructure.repositories.deps import create_stock_cache
    from app.modules.market_data.services.market_service import MarketApplicationService

    try:
        from app.bootstrap_components.providers import create_cache_port

        cache_port = create_cache_port()
    except Exception:
        cache_port = None

    svc = MarketApplicationService(
        get_market_data_provider(),
        CnIndustryProvider(),
        stock_cache=create_stock_cache(),
        cache=cache_port,
    )
    rows = svc.refresh_cn_quote_book(allow_akshare=True)
    return {"ok": True, "count": len(rows), "skipped": False, "reason": reason}


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(name="app.tasks.cn_quote_book_tasks.refresh_cn_quote_book_tick")
    def refresh_cn_quote_book_tick(force: bool = False) -> dict[str, Any]:
        try:
            return run_cn_quote_book_refresh(force=force)
        except Exception as exc:
            logger.exception("refresh_cn_quote_book_tick failed")
            return {"ok": False, "error": str(exc)}

else:
    refresh_cn_quote_book_tick = None  # type: ignore[misc, assignment]
