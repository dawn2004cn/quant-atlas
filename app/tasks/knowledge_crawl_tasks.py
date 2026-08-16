"""Celery tasks: crawl + localize knowledge base (研报/新闻/财报/产业链)."""

from __future__ import annotations

from typing import Any

from ..celery_app import celery as _celery
from ..config import get_settings
from ..core.logger import get_logger
from ..core.runtime_config import get_runtime, get_runtime_int
from .task_wiring import create_basic_market_data_service

logger = get_logger(__name__)


def _resolve_codes(codes: list[str] | None) -> list[str]:
    from app.modules.data.services.basic_market_data_service import BasicMarketDataService

    if codes:
        raw = ",".join(str(c).strip() for c in codes if str(c).strip())
        return BasicMarketDataService._parse_code_list(raw, default_csv="600519")
    raw = (get_runtime("KNOWLEDGE_CRAWL_CODES", "") or "").strip()
    if raw:
        return BasicMarketDataService._parse_code_list(raw, default_csv="600519")
    return BasicMarketDataService._parse_code_list(None, default_csv="600519,000001,300750")


def _make_crawl_service():
    from app.infrastructure.repositories.common.deps import create_news_archive_repository
    from app.infrastructure.storage.knowledge_local_store import KnowledgeLocalStore
    from app.modules.data.services.knowledge_crawl_service import KnowledgeCrawlService
    from app.modules.system.services.tools.tool_facade_service import get_tool_facade_service

    settings = get_settings()
    news = None
    try:
        news = create_news_archive_repository(settings)
    except Exception as exc:  # noqa: BLE001
        logger.warning("news archive for crawl: %s", exc, exc_info=True)

    facade = None
    try:
        facade = get_tool_facade_service()
    except Exception as exc:  # noqa: BLE001
        logger.warning("tool facade for crawl: %s", exc, exc_info=True)

    chain = None
    try:
        from app.modules.market_data.services.industry_chain_map_service import (
            IndustryChainMapService,
        )

        chain = IndustryChainMapService()
    except Exception as exc:  # noqa: BLE001
        logger.debug("industry chain for crawl: %s", exc)

    return KnowledgeCrawlService(
        store=KnowledgeLocalStore(),
        basic_market_data_service=create_basic_market_data_service(),
        news_archive=news,
        tool_facade=facade,
        industry_chain_service=chain,
        fundamental_access=facade,
    )


def run_knowledge_crawl(
    codes: list[str] | None = None,
    *,
    sources: list[str] | None = None,
    run_remote: bool = True,
    yanbao_max_pages: int | None = None,
) -> dict[str, Any]:
    """Sync entry used by Celery and API."""
    resolved = _resolve_codes(codes)
    cap = max(1, min(get_runtime_int("KNOWLEDGE_CRAWL_MAX_CODES", 30), 200))
    resolved = resolved[:cap]
    pages = yanbao_max_pages
    if pages is None:
        pages = max(1, min(get_runtime_int("KNOWLEDGE_CRAWL_YANBAO_PAGES", 3), 20))
    svc = _make_crawl_service()
    return svc.crawl_and_localize(
        codes=resolved,
        sources=sources,
        run_remote=run_remote,
        yanbao_max_pages=pages,
    )


if _celery is not None:

    @_celery.task(name="app.tasks.knowledge_crawl_tasks.crawl_knowledge_bundle", bind=True)
    def crawl_knowledge_bundle(
        self,
        codes: list[str] | None = None,
        sources: list[str] | None = None,
        run_remote: bool = True,
        yanbao_max_pages: int | None = None,
    ) -> dict[str, Any]:
        task_id = getattr(getattr(self, "request", None), "id", None)
        if task_id:
            try:
                from app.tasks.task_wiring import init_task_progress, report_task_progress

                steps = ["远程爬取", "本地分类落库", "完成"]
                init_task_progress(task_id, task_name=self.name, steps=steps)
                report_task_progress(task_id, step_index=0, message=steps[0])
            except Exception as exc:  # noqa: BLE001
                logger.debug("knowledge crawl progress init: %s", exc)
        result = run_knowledge_crawl(
            codes,
            sources=sources,
            run_remote=run_remote,
            yanbao_max_pages=yanbao_max_pages,
        )
        if task_id:
            try:
                from app.tasks.task_wiring import report_task_progress

                report_task_progress(task_id, step_index=2, message="完成")
            except Exception as exc:  # noqa: BLE001
                logger.debug("knowledge crawl progress done: %s", exc)
        return result

    @_celery.task(name="app.tasks.knowledge_crawl_tasks.scheduled_knowledge_crawl")
    def scheduled_knowledge_crawl() -> dict[str, Any]:
        return run_knowledge_crawl(run_remote=True)

else:
    crawl_knowledge_bundle = None  # type: ignore[misc, assignment]
    scheduled_knowledge_crawl = None  # type: ignore[misc, assignment]


__all__ = [
    "run_knowledge_crawl",
    "crawl_knowledge_bundle",
    "scheduled_knowledge_crawl",
]
