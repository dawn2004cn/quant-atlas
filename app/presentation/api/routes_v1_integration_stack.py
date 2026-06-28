from __future__ import annotations

"""API v1：集成栈（多模块 Facade 只读状态）。"""


from flask import Blueprint
from flask_login import login_required

from app.core.registry import register_routes

from .common import ok_response
from .v1_context import ApiV1Context


@register_routes(name="integration_stack", context="misc", description="集成栈（多模块 Facade 只读状态）")
def register_integration_stack_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/integration/stack-status")
    @login_required
    def integration_stack_status():
        """Kronos / QuantML / Agent / OpenBB 等集成模块运行摘要（不发起外网行情）。"""
        svc = getattr(ctx, "integration_stack_service", None)
        if svc is None:
            return ok_response(
                data={"available": False, "summary": "集成栈服务未就绪", "layers": {}, "issue_count": 0},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        data = svc.get_stack_status()
        return ok_response(data=data, legacy_alias_key=None, enable_legacy_alias=legacy)
