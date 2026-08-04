from __future__ import annotations

"""API v1：投资经理（100 策略一一映射）模拟与排行榜。"""

from flask import Blueprint

from app.core.registry import register_routes
from app.core.middleware.request_context import require_authenticated_user_id
from app.presentation.api.route_deps import SocialRouteDeps, build_social_route_deps, require_investment_manager_service
from app.presentation.api.v1.investment_managers.crud_routes import register_investment_manager_crud_routes
from app.presentation.api.v1.investment_managers.simulation_routes import register_investment_manager_simulation_routes
from app.presentation.api.v1.investment_managers.user_account_routes import register_investment_manager_user_routes
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="investment_manager", context="misc", description="投资经理（100 策略一一映射）模拟与排行榜")
def register_investment_manager_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None = None,
    *,
    deps: SocialRouteDeps | None = None,
) -> None:
    route_deps = deps or build_social_route_deps(ctx)

    def _svc():
        return require_investment_manager_service(route_deps)

    def _uid() -> int:
        return require_authenticated_user_id()

    legacy = route_deps.enable_legacy_response_fields
    enable_celery = route_deps.enable_celery
    task_dispatcher = route_deps.task_dispatcher
    task_message_store = route_deps.task_message_store

    register_investment_manager_crud_routes(
        blueprint,
        legacy=legacy,
        svc=_svc,
        uid=_uid,
    )
    register_investment_manager_simulation_routes(
        blueprint,
        legacy=legacy,
        enable_celery=enable_celery,
        svc=_svc,
        task_dispatcher=task_dispatcher,
        task_message_store=task_message_store,
    )
    register_investment_manager_user_routes(
        blueprint,
        legacy=legacy,
        svc=_svc,
    )
