"""Retail assistant hub summary routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.common import ok_response
from app.presentation.api.v1.retail_assistant.runtime import RetailAssistantRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_retail_assistant_hub_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: RetailAssistantRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/retail-assistant/quick-actions")
    @login_required
    def retail_assistant_quick_actions():
        svc = runtime.hub_service
        if svc is None:
            return runtime.hub_unavailable_response()
        return ok_response(
            data=svc.quick_actions(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/retail-assistant/overview")
    @login_required
    def retail_assistant_overview():
        svc = runtime.hub_service
        if svc is None:
            return runtime.hub_unavailable_response()
        return ok_response(
            data=svc.overview(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/retail-assistant/knowledge/suggestions")
    @login_required
    def retail_assistant_knowledge_suggestions():
        svc = runtime.hub_service
        if svc is None:
            return runtime.hub_unavailable_response()
        return ok_response(
            data=svc.knowledge_suggestions(symbol=request.args.get("symbol")),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/retail-assistant/portfolio-risk")
    @login_required
    def retail_assistant_portfolio_risk():
        svc = runtime.hub_service
        if svc is None:
            return runtime.hub_unavailable_response()
        return ok_response(
            data=svc.portfolio_risk(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/retail-assistant/refactor-status")
    @login_required
    def retail_assistant_refactor_status():
        """对照 docs/refacter.md 四维能力的落地状态（供架构/产品页展示）。"""
        svc = runtime.hub_service
        if svc is None:
            return ok_response(
                data={"available": False, "summary": "Retail Assistant Hub 未就绪", "dimensions": {}},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        return ok_response(
            data=svc.refactor_status(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
