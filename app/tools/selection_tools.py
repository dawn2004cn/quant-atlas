from __future__ import annotations
"""Selection Tools - 选股和自选股相关工具."""


from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from langchain_core.tools import tool
from ..core.logger import get_logger

logger = get_logger(__name__)


class StockSelectorToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model_name: str
    ok: bool = True
    error: str | None = None
    stocks: list[dict[str, Any]] = Field(default_factory=list)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class WatchlistToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: int
    ok: bool = True
    error: str | None = None
    watchlist: list[dict[str, Any]] = Field(default_factory=list)
    groups: list[dict[str, Any]] = Field(default_factory=list)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


def _ensure_dict(v: Any) -> dict[str, Any] | None:
    if v is None:
        return None
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        import json as _json
        try:
            return _json.loads(v)
        except _json.JSONDecodeError as e:
            logger.warning("selection_tools.py._ensure_dict: %s", e)
    return None


@tool
def stock_selector(
    model_name: str,
    criteria: Optional[dict[str, Any]] = None,
    screening_criteria: Optional[dict[str, Any]] = None,
) -> StockSelectorToolResult:
    """执行选股扫描."""
    from ..application.services.tool_facade_service import get_tool_facade_service

    try:
        service = get_tool_facade_service()
        result = service.stock_selection(
            model_name=model_name,
            criteria=_ensure_dict(criteria),
            screening_criteria=_ensure_dict(screening_criteria),
        )

        return StockSelectorToolResult(
            model_name=model_name,
            stocks=result.get("stocks", []),
            evidence=f"Selected {len(result.get('stocks', []))} stocks using {model_name}",
            confidence=0.8 if result.get("stocks") else 0.4,
        )
    except Exception as e:
        logger.error(f"stock_selector failed: {e}")
        return StockSelectorToolResult(
            model_name=model_name,
            ok=False,
            error=str(e),
            confidence=0.3,
        )


@tool
def get_user_watchlist(user_id: int) -> WatchlistToolResult:
    """获取用户自选股列表."""
    from app.config import get_settings
    from app.infrastructure.repositories.common.deps import (
        create_watchlist_repository,
        create_stock_group_repository,
    )
    from app.modules.market_data.services.watchlist_service import WatchlistApplicationService

    try:
        settings = get_settings()
        # MySQL requires a SQLAlchemy session_factory for the repository
        session_factory = None
        if settings.use_mysql and getattr(settings, "mysql", None):
            try:
                from app.infrastructure.database.db_manager import get_db_manager
                session_factory = get_db_manager().get_session_factory(settings.mysql)
            except Exception:
                logger.warning("Suppressed exception", exc_info=True)
                pass

        watchlist_repo = create_watchlist_repository(settings, session_factory)
        stock_group_repo = create_stock_group_repository(settings, session_factory)
        service = WatchlistApplicationService(
            repository=watchlist_repo,
            stock_group_repository=stock_group_repo,
        )
        symbols = service.list_symbols(user_id)
        groups = service.get_all_watchlists(user_id)
        watchlist_items = [{"code": s} for s in symbols] if symbols else []
        group_items = [{"name": k, "symbols": v} for k, v in (groups or {}).items()]

        return WatchlistToolResult(
            user_id=user_id,
            watchlist=watchlist_items,
            groups=group_items,
            evidence=f"Retrieved {len(watchlist_items)} stocks for user {user_id}",
            confidence=0.9,
        )
    except Exception as e:
        logger.error(f"get_user_watchlist failed: {e}")
        return WatchlistToolResult(
            user_id=user_id,
            ok=False,
            error=str(e),
            confidence=0.3,
        )