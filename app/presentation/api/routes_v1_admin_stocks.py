from __future__ import annotations
"""API v1：管理员查看本地行情缓存（stock_cache.db）。"""


from flask import Blueprint, request
from flask_login import current_user, login_required

from app.application.errors import AuthorizationError
from app.modules.system.services.admin.admin_stock_service import get_admin_stock_service
from app.core.registry import register_routes
from .common import ok_response
from .request_parsers import parse_int_param


@register_routes(name="admin_stock_cache", context="misc", description="管理员查看本地行情缓存")
def register_admin_stock_cache_routes(blueprint: Blueprint, ctx: Any = None, *, enable_legacy_response_fields: bool = False) -> None:
    @blueprint.get("/admin/stock-cache")
    @login_required
    def admin_stock_cache():
        if not current_user.can_manage_users():
            raise AuthorizationError("admin_stock_cache_forbidden")
        limit = parse_int_param(request.args.get("limit"), name="limit", default=8000, min_value=1)
        limit = min(limit, 20_000)
        service = get_admin_stock_service()

        stats = {}
        try:
            stats = service.get_stats()
        except Exception:
            stats = {"error": "method not available"}

        items = []
        try:
            items = service.get_all_stocks()[:limit]
        except Exception:
            items = []
        
        return ok_response(
            data={"stats": stats, "items": items, "returned": len(items)},
            legacy_alias_key=None,
            enable_legacy_alias=enable_legacy_response_fields,
        )
