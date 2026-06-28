from __future__ import annotations
"""Pipeline Tools - 研究pipeline和智能流程相关工具."""


from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from langchain_core.tools import tool

from ..core.logger import get_logger

logger = get_logger(__name__)


class ResearchPipelineStatusToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    error: str | None = None
    status: dict[str, Any] = Field(default_factory=dict)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class IntelligentPipelineToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    task_id: str
    ok: bool = True
    error: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class WebSearchToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query: str
    ok: bool = True
    error: str | None = None
    results: list[dict[str, Any]] = Field(default_factory=list)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class YanbaoDigestToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: str
    ok: bool = True
    error: str | None = None
    articles: list[dict[str, Any]] = Field(default_factory=list)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


@tool
def get_research_pipeline_status() -> ResearchPipelineStatusToolResult:
    """获取研究Pipeline状态."""
    from ..modules.ai_agent.services.ai_research_service import get_ai_research_service

    try:
        service = get_ai_research_service()
        status = service.get_pipeline_status()

        return ResearchPipelineStatusToolResult(
            status=status,
            evidence=f"Pipeline status: {status.get('state', 'unknown')}",
            confidence=0.8,
        )
    except Exception as e:
        logger.error(f"get_research_pipeline_status failed: {e}")
        return ResearchPipelineStatusToolResult(
            ok=False,
            error=str(e),
            confidence=0.3,
        )


@tool
def run_intelligent_pipeline(
    target: str,
    task_type: str = "fundamental",
    params: dict[str, Any] | None = None,
) -> IntelligentPipelineToolResult:
    """运行智能研究Pipeline."""
    import uuid
    from ..modules.ai_agent.services.ai_research_service import get_ai_research_service

    try:
        service = get_ai_research_service()
        task_id = str(uuid.uuid4())

        result = service.run_pipeline(
            target=target,
            task_type=task_type,
            params=params or {},
            task_id=task_id,
        )

        return IntelligentPipelineToolResult(
            task_id=task_id,
            result=result,
            evidence=f"Pipeline task {task_id} initiated for {target}",
            confidence=0.7,
        )
    except Exception as e:
        logger.error(f"run_intelligent_pipeline failed: {e}")
        return IntelligentPipelineToolResult(
            task_id="",
            ok=False,
            error=str(e),
            confidence=0.3,
        )


@tool
def search_web_intelligence(query: str) -> WebSearchToolResult:
    """搜索Web智能信息."""

    try:
        from ..infrastructure.providers.web_search import get_web_search_provider

        provider = get_web_search_provider()
        results = provider.search(query, max_results=10)

        return WebSearchToolResult(
            query=query,
            results=results,
            evidence=f"Web search returned {len(results)} results for '{query}'",
            confidence=0.7 if results else 0.4,
        )
    except Exception as e:
        logger.error(f"search_web_intelligence failed: {e}")
        return WebSearchToolResult(
            query=query,
            ok=False,
            error=str(e),
            confidence=0.3,
        )


@tool
def get_yanbao_market_digest(category: str = "个股研报", limit: int = 12) -> YanbaoDigestToolResult:
    """获取研报市场摘要."""
    from ..application.services.tool_facade_service import get_tool_facade_service

    try:
        service = get_tool_facade_service()
        articles = service.get_yanbao_digest(category=category, limit=limit)

        return YanbaoDigestToolResult(
            category=category,
            articles=articles,
            evidence=f"Retrieved {len(articles)} articles for category '{category}'",
            confidence=0.7 if articles else 0.4,
        )
    except Exception as e:
        logger.error(f"get_yanbao_market_digest failed: {e}")
        return YanbaoDigestToolResult(
            category=category,
            ok=False,
            error=str(e),
            confidence=0.3,
        )
