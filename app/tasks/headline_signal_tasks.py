from __future__ import annotations

"""Celery task: offline batch headline signal tagging + cache."""

from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.modules.strategy.services.analytics.headline_signal_enrichment_service import (
    HeadlineSignalEnrichmentService,
)

logger = get_logger(__name__)


def _serialize_headline(item: object) -> dict[str, Any]:
    return {
        "title": getattr(item, "title", "") or "",
        "source": getattr(item, "source", "") or "",
        "published_at": str(getattr(item, "published_at", "") or ""),
        "url": getattr(item, "url", "") or "",
        "summary": getattr(item, "summary", "") or "",
    }


def run_enrich_market_headlines(*, market: str = "CN", limit: int = 40) -> dict[str, Any]:
    from app.modules.system.services.helpers.news_provider_access import get_news_provider

    market_code = MarketCode(market.upper()) if market else MarketCode.CN
    resolved_limit = max(8, min(int(limit or 40), 100))
    provider = get_news_provider()
    items = provider.get_market_headlines(market_code, limit=resolved_limit)
    headlines = [_serialize_headline(it) for it in items]
    svc = HeadlineSignalEnrichmentService()
    patch = svc.batch_compute_and_cache(headlines, market=market_code.value)
    return {
        "ok": True,
        "market": market_code.value,
        "count": len(headlines),
        "cached": len(patch),
    }


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(name="app.tasks.headline_signal_tasks.enrich_market_headlines")
    def enrich_market_headlines(market: str = "CN", limit: int = 40) -> dict[str, Any]:
        try:
            return run_enrich_market_headlines(market=market, limit=limit)
        except Exception as exc:
            logger.exception("enrich_market_headlines failed")
            return {"ok": False, "error": str(exc)}

else:
    enrich_market_headlines = None  # type: ignore[misc, assignment]
