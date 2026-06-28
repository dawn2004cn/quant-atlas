from __future__ import annotations

"""Headless UI bootstrap APIs — page context without Jinja business logic."""

from flask import Blueprint, request
from flask_login import login_required

from app.core.registry import register_routes

from ...core.middleware.request_context import require_authenticated_user_id
from .common import ok_response, require_ctx_service
from .v1_context import ApiV1Context


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes
def register_ui_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/ui/stock-detail-context")
    @login_required
    def stock_detail_context():
        """Bootstrap payload for stock_detail capability components."""
        symbol = (request.args.get("symbol") or "").strip().lower()
        market = (request.args.get("market") or request.args.get("m") or "CN").strip().upper()
        tenant_ctx: dict = {}
        collab = getattr(ctx, "collaboration_service", None)
        if collab is not None:
            try:
                tenant_ctx = collab.get_user_context(_uid())
            except Exception:
                tenant_ctx = {}
        layout: list[str] = []
        prefs_svc = getattr(ctx, "page_preference_service", None)
        if prefs_svc is not None:
            try:
                prefs = prefs_svc.get_preferences(_uid())
                data = prefs.data if hasattr(prefs, "data") else prefs
                if isinstance(data, dict):
                    layout = list(data.get("stock_detail_layout") or [])
            except Exception:
                layout = []
        return ok_response(
            data={
                "symbol": symbol,
                "market": market,
                "tenant": tenant_ctx.get("tenant"),
                "teams": tenant_ctx.get("teams") or [],
                "active_team_id": tenant_ctx.get("active_team_id"),
                "stock_detail_layout": layout,
                "capabilities_endpoint": "/api/v1/ui/capabilities",
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/ui/collaboration-workspace-context")
    @login_required
    def collaboration_workspace_context():
        """Bootstrap payload for team collaboration workspace."""
        tenant_ctx: dict = {}
        collab = require_ctx_service(ctx, "collaboration_service")
        tenant_ctx = collab.get_user_context(_uid())
        return ok_response(
            data={
                "tenant": tenant_ctx.get("tenant"),
                "teams": tenant_ctx.get("teams") or [],
                "active_team_id": tenant_ctx.get("active_team_id"),
                "workspace_layout": [
                    "team-context-bar",
                    "team-blackboard",
                    "team-research-feed",
                ],
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/ui/capabilities")
    @login_required
    def list_ui_capabilities():
        """Registry of stock-detail capability component ids."""
        return ok_response(
            data={
                "stock_detail": [
                    "live-research-lab",
                    "decision-brief-strip",
                    "attribution-timeline",
                    "strategy-copilot",
                    "evidence-replay",
                    "resonance-meter",
                    "team-context-bar",
                    "team-blackboard",
                    "team-research-feed",
                ],
                "collaboration_workspace": [
                    "team-context-bar",
                    "team-blackboard",
                    "team-research-feed",
                    "cross-team-pulse",
                ],
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
