"""AI tools for local classified knowledge base."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from app.core.logger import get_logger

logger = get_logger(__name__)


class LocalKnowledgeSearchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    error: str | None = None
    query: str = ""
    symbol: str | None = None
    items: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    evidence: str = ""
    confidence: float = Field(default=0.55, ge=0.0, le=1.0)


class LocalKnowledgePackResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    error: str | None = None
    symbol: str | None = None
    prompt_block: str = ""
    by_category: dict[str, Any] = Field(default_factory=dict)
    count: int = 0
    evidence: str = ""
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)


def _store():
    from app.infrastructure.storage.knowledge_local_store import KnowledgeLocalStore

    return KnowledgeLocalStore()


@tool
def search_local_knowledge(
    query: str = "",
    symbol: str = "",
    categories: str = "",
    limit: int = 20,
) -> LocalKnowledgeSearchResult:
    """搜索本地基础知识库（研报/新闻/财报/产业链/语料），优先返回已爬取并分类落库的内容。"""
    try:
        cats = [c.strip() for c in (categories or "").split(",") if c.strip()] or None
        items = _store().search(
            query or "",
            categories=cats,
            symbol=(symbol or "").strip() or None,
            limit=max(1, min(int(limit or 20), 50)),
        )
        conf = 0.45 + min(0.4, 0.05 * len(items))
        return LocalKnowledgeSearchResult(
            query=query or "",
            symbol=(symbol or "").strip() or None,
            items=items,
            count=len(items),
            evidence=f"local knowledge hits={len(items)} categories={categories or 'all'}",
            confidence=conf,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("search_local_knowledge failed: %s", exc, exc_info=True)
        return LocalKnowledgeSearchResult(ok=False, error=str(exc), query=query or "", confidence=0.1)


@tool
def get_local_knowledge_pack(symbol: str = "", query: str = "", limit: int = 24) -> LocalKnowledgePackResult:
    """获取按类别整理的本地知识包（prompt_block），便于直接注入 AI 上下文。"""
    try:
        pack = _store().build_ai_pack(
            symbol=(symbol or "").strip() or None,
            query=query or "",
            limit=max(1, min(int(limit or 24), 40)),
        )
        conf = 0.5 if pack.get("count") else 0.25
        return LocalKnowledgePackResult(
            symbol=pack.get("symbol"),
            prompt_block=str(pack.get("prompt_block") or ""),
            by_category=dict(pack.get("by_category") or {}),
            count=int(pack.get("count") or 0),
            evidence="local classified knowledge pack",
            confidence=conf,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("get_local_knowledge_pack failed: %s", exc, exc_info=True)
        return LocalKnowledgePackResult(ok=False, error=str(exc), confidence=0.1)
