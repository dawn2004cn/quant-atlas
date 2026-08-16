"""API v1: Basic knowledge base search (研报/财报/新闻/产业链)."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.core.registry import register_routes
from app.modules.data.services.basic_knowledge_service import (
    SOURCE_CHAIN,
    SOURCE_CORPUS,
    SOURCE_FINANCIAL,
    SOURCE_NEWS,
    SOURCE_YANBAO,
)
from app.presentation.api.common import ok_response
from app.presentation.api.decorators import service_fallback
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.v1_context import ApiV1Context


@register_routes(
    name="basic_knowledge",
    context="data",
    description="Unified basic knowledge search across yanbao/news/financials/industry chain",
)
def register_basic_knowledge_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/knowledge/search")
    @login_required
    @service_fallback("basic_knowledge_service")
    def knowledge_search():
        svc = getattr(ctx, "basic_knowledge_service", None)
        q = (request.args.get("q") or request.args.get("query") or "").strip()
        symbol = (request.args.get("symbol") or "").strip() or None
        market = (request.args.get("market") or "CN").strip().upper() or "CN"
        limit = parse_int_param(
            request.args.get("limit"), name="limit", default=30, min_value=1, max_value=80
        )
        raw_sources = (request.args.get("sources") or "").strip()
        sources = [s.strip() for s in raw_sources.split(",") if s.strip()] if raw_sources else None
        data = svc.search(q, symbol=symbol, sources=sources, market=market, limit=limit)
        return ok_response(data=data, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/knowledge/sources")
    @login_required
    def knowledge_sources():
        return ok_response(
            data={
                "items": [
                    {"id": SOURCE_YANBAO, "label": "研报"},
                    {"id": SOURCE_NEWS, "label": "新闻"},
                    {"id": SOURCE_FINANCIAL, "label": "财报"},
                    {"id": SOURCE_CHAIN, "label": "产业链"},
                    {"id": SOURCE_CORPUS, "label": "基础知识语料"},
                ],
                "note": "命中来自平台已接入源 + 内置产业逻辑语料，非任意站点全网爬取。",
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
