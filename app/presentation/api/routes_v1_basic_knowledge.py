"""API v1: Basic knowledge base search (研报/财报/新闻/产业链) + crawl/localize."""

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
                "note": "命中来自本地分类库 + 平台已接入源，非任意站点全网爬取。",
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/knowledge/local/stats")
    @login_required
    @service_fallback("knowledge_crawl_service")
    def knowledge_local_stats():
        crawl = getattr(ctx, "knowledge_crawl_service", None)
        return ok_response(
            data=crawl.store.stats(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/knowledge/local/search")
    @login_required
    @service_fallback("knowledge_crawl_service")
    def knowledge_local_search():
        crawl = getattr(ctx, "knowledge_crawl_service", None)
        q = (request.args.get("q") or request.args.get("query") or "").strip()
        symbol = (request.args.get("symbol") or "").strip() or None
        limit = parse_int_param(
            request.args.get("limit"), name="limit", default=30, min_value=1, max_value=80
        )
        raw_sources = (request.args.get("sources") or request.args.get("categories") or "").strip()
        cats = [s.strip() for s in raw_sources.split(",") if s.strip()] if raw_sources else None
        items = crawl.store.search(q, categories=cats, symbol=symbol, limit=limit)
        return ok_response(
            data={"query": q, "symbol": symbol, "items": items, "count": len(items)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/knowledge/pack")
    @login_required
    @service_fallback("knowledge_crawl_service")
    def knowledge_ai_pack():
        crawl = getattr(ctx, "knowledge_crawl_service", None)
        q = (request.args.get("q") or request.args.get("query") or "").strip()
        symbol = (request.args.get("symbol") or "").strip() or None
        limit = parse_int_param(
            request.args.get("limit"), name="limit", default=24, min_value=1, max_value=40
        )
        pack = crawl.store.build_ai_pack(symbol=symbol, query=q, limit=limit)
        return ok_response(data=pack, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/knowledge/crawl")
    @login_required
    @service_fallback("knowledge_crawl_service")
    def knowledge_crawl():
        crawl = getattr(ctx, "knowledge_crawl_service", None)
        body = request.get_json(silent=True) or {}
        codes = body.get("codes")
        if isinstance(codes, str):
            codes = [c.strip() for c in codes.split(",") if c.strip()]
        sources = body.get("sources")
        if isinstance(sources, str):
            sources = [s.strip() for s in sources.split(",") if s.strip()]
        run_remote = body.get("run_remote", True)
        if isinstance(run_remote, str):
            run_remote = run_remote.strip().lower() not in ("0", "false", "no")
        async_mode = bool(body.get("async") or body.get("enqueue"))
        if async_mode and getattr(ctx, "enable_celery", False):
            try:
                from app.tasks.knowledge_crawl_tasks import crawl_knowledge_bundle

                if crawl_knowledge_bundle is not None:
                    async_result = crawl_knowledge_bundle.delay(
                        codes=codes,
                        sources=sources,
                        run_remote=bool(run_remote),
                    )
                    return ok_response(
                        data={"queued": True, "task_id": async_result.id},
                        legacy_alias_key=None,
                        enable_legacy_alias=legacy,
                    )
            except Exception:  # noqa: BLE001
                pass
        data = crawl.crawl_and_localize(
            codes=codes,
            sources=sources,
            run_remote=bool(run_remote),
        )
        return ok_response(data=data, legacy_alias_key=None, enable_legacy_alias=legacy)
