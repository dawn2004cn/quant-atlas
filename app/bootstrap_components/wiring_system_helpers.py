"""System helper service wiring — news, tasks, notifications, tools, AI."""

from __future__ import annotations

import logging
from typing import Any

from app.core.registry import register_factory

logger = logging.getLogger(__name__)


def _make_news_provider(_reg: Any) -> Any:
    from app.modules.system.services.helpers.news_provider_wiring import get_news_provider
    return get_news_provider()


register_factory("news_provider", _make_news_provider)


def _make_task_message_store(_reg: Any) -> Any:
    from app.modules.system.services.helpers.task_message_wiring import get_task_message_store
    return get_task_message_store()


register_factory("task_message_store", _make_task_message_store)


def _resolve_news_provider(reg: Any) -> Any:
    provider = reg.get_or_none("news_provider")
    if provider is not None:
        return provider
    try:
        from app.modules.system.services.helpers.news_provider_wiring import get_news_provider
        return get_news_provider()
    except Exception as exc:
        logger.warning("news_provider fallback failed: %s", exc)
        return None


def _resolve_task_message_store(reg: Any) -> Any:
    store = reg.get_or_none("task_message_store")
    if store is not None:
        return store
    try:
        from app.modules.system.services.helpers.task_message_wiring import get_task_message_store
        return get_task_message_store()
    except Exception as exc:
        logger.warning("task_message_store fallback failed: %s", exc)
        return None


def _make_notification_service(reg: Any) -> Any:
    from app.modules.system.services.notification_service import NotificationService
    return NotificationService(registry=reg)


register_factory("notification_service", _make_notification_service)


def _make_tool_facade_service(_reg: Any) -> Any:
    from app.modules.system.services.tools.tool_facade_service import ToolFacadeService
    return ToolFacadeService()


register_factory("tool_facade_service", _make_tool_facade_service)


def _make_ai_research_service(_reg: Any) -> Any:
    from app.modules.ai_agent.services.ai_research_service import AiResearchService
    return AiResearchService()


register_factory("ai_research_service", _make_ai_research_service)


def _make_decision_review_queue(reg: Any) -> Any:
    from app.modules.system.services.ui.decision_review_queue import DecisionReviewQueue
    return DecisionReviewQueue(
        store_path=None,
        max_pending=100,
    )

register_factory("decision_review_queue", _make_decision_review_queue)


def _make_rdagent_job_store(reg: Any) -> Any:
    import tempfile

    from app.modules.system.services.helpers.rdagent_access import create_rdagent_job_store
    return create_rdagent_job_store(tempfile.gettempdir())

register_factory("rdagent_job_store", _make_rdagent_job_store)


def _make_qlib_task_service(reg: Any) -> Any:
    from app.modules.system.services.helpers.qlib_access import create_qlib_task_service
    return create_qlib_task_service()


register_factory("qlib_task_service", _make_qlib_task_service)
