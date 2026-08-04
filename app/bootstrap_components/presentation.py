"""Presentation layer configuration."""

from __future__ import annotations

from typing import Any

from flask import Flask
from flask_login import LoginManager

from app.core.logger import get_logger

logger = get_logger(__name__)


def _load_user_account(user_repository: Any, user_id: str) -> Any:
    getter = getattr(user_repository, "get_by_id", None)
    if callable(getter):
        return getter(user_id)
    list_fn = getattr(user_repository, "list_users", None)
    if not callable(list_fn):
        return None
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    for account in list_fn():
        if account.user_id == uid:
            return account
    return None


def configure_login_manager(app: Flask, user_repository: Any = None, logger: Any = None) -> LoginManager:
    """Configure Flask-Login."""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.session_protection = "strong"
    login_manager.login_disabled = False

    @login_manager.user_loader
    def load_user(user_id: str):
        if not user_repository:
            return None
        try:
            from app.presentation.web.models import SessionUser

            account = _load_user_account(user_repository, user_id)
            if account is None:
                return None
            return SessionUser.from_entity(account)
        except Exception:
            if logger is not None:
                logger.exception("user_loader failed for user_id=%s", user_id)
            return None

    @login_manager.request_loader
    def load_user_from_request(request):
        from app.presentation.api.auth_guard import user_from_bearer_token

        bearer_user = user_from_bearer_token(request)
        if bearer_user is not None:
            return bearer_user
        # In test mode we must NOT implicitly authenticate every request.
        # Tests assert that routes protected by @login_required return 401
        # for anonymous clients unless a valid bearer token is provided.
        return None

    return login_manager


def register_blueprints(app: Flask, settings: Any = None, api_bundle: Any = None, task_message_store: Any = None, services: Any = None) -> None:
    """Register Flask blueprints."""
    # Register API blueprints
    try:
        from app.presentation.api import create_api_blueprint
        _task_dispatcher = None
        try:
            from app.infrastructure.messaging.task_dispatcher import (
                CeleryTaskDispatcher,
            )
            _task_dispatcher = CeleryTaskDispatcher()
        except Exception as exc:
            if logger is not None:
                logger.warning("task_dispatcher unavailable: %s", exc)
        api_blueprint = create_api_blueprint(
            api_bundle,
            task_dispatcher=_task_dispatcher,
            task_message_store=task_message_store,
            enable_celery=getattr(settings, "enable_celery", False),
            enable_legacy_response_fields=getattr(
                settings, "enable_api_legacy_response_fields", False
            ),
            enable_qlib=getattr(settings, "enable_qlib", False),
            enable_rd_agent=getattr(settings, "enable_rd_agent", False),
        )
        app.register_blueprint(api_blueprint)
        from app.bootstrap_components.service_readiness import is_strict_bootstrap
        from app.presentation.api.routes import apply_v1_route_contract

        apply_v1_route_contract(app, strict=is_strict_bootstrap())
    except Exception as e:
        from app.bootstrap_components.service_readiness import is_strict_bootstrap

        logger.error("Could not register API blueprint: %s", e, exc_info=True)
        if is_strict_bootstrap():
            raise

    # Register legacy API blueprint (/api/* compatibility routes)
    try:
        from app.presentation.api.legacy_routes import create_legacy_api_blueprint
        _svc = services or (api_bundle.services if api_bundle else None)
        if _svc is not None:
            legacy_bp = create_legacy_api_blueprint(
                market_service=getattr(_svc, "market_service", None),
                stock_service=getattr(_svc, "stock_service", None),
                strategy_service=getattr(_svc, "strategy_service", None),
                watchlist_service=getattr(_svc, "watchlist_service", None),
                stock_group_service=getattr(_svc, "stock_group_service", None),
                user_service=getattr(_svc, "user_service", None),
            )
            if legacy_bp is not None:
                app.register_blueprint(legacy_bp)
    except Exception as e:
        logger.warning("Could not register legacy API blueprint: %s", e, exc_info=True)

    # Register API v2 blueprint (DTO-validated, standardized response format)
    try:
        from app.presentation.api.routes_v2 import create_api_v2_blueprint
        _svc = services or (api_bundle.services if api_bundle else None)
        if _svc is None:
            raise RuntimeError("services bundle not available for v2 blueprint")

        v2_bp = create_api_v2_blueprint(
            market_service=getattr(_svc, "market_service", None),
            market_facade=getattr(_svc, "market_facade", None),
            backtest_facade=getattr(_svc, "backtest_facade", None),
            ai_facade=getattr(_svc, "ai_facade", None),
            stock_service=getattr(_svc, "stock_service", None),
            news_provider=getattr(_svc, "news_provider", None),
            fundamental_access=getattr(_svc, "fundamental_access", None),
            news_archive=getattr(_svc, "news_archive", None),
            qlib_pipeline_service=getattr(_svc, "qlib_pipeline_service", None),
            strategy_service=getattr(_svc, "strategy_service", None),
            pool_service=getattr(_svc, "pool_service", None),
            ai_analysis_service=getattr(_svc, "ai_analysis_service", None),
            ai_research_service=getattr(_svc, "ai_research_service", None),
            analysis_service=getattr(_svc, "analysis_service", None),
            watchlist_service=getattr(_svc, "watchlist_service", None),
            stock_group_service=getattr(_svc, "stock_group_service", None),
            user_service=getattr(_svc, "user_service", None),
            rdagent_run_service=getattr(_svc, "rdagent_run_service", None),
            prediction_service=getattr(_svc, "prediction_service", None),
            selection_source_service=getattr(_svc, "selection_source_service", None),
            basic_market_data_service=getattr(_svc, "basic_market_data_service", None),
            task_message_store=task_message_store,
            enable_celery=getattr(settings, "enable_celery", False),
            enable_qlib=getattr(settings, "enable_qlib", False),
            enable_rd_agent=getattr(settings, "enable_rd_agent", False),
            enable_dto_validation=True,
            signal_flag_service=getattr(_svc, "signal_flag_service", None),
            investment_manager_service=getattr(_svc, "investment_manager_service", None),

            integration_stack_service=getattr(_svc, "integration_stack_service", None),
            fingpt_application_service=getattr(_svc, "fingpt_application_service", None),
            portfolio_service=getattr(_svc, "portfolio_service", None),
            portfolio_trade_service=getattr(_svc, "portfolio_trade_service", None),
            risk_service=getattr(_svc, "risk_service", None),
            system_service=getattr(_svc, "system_service", None),
            auth_service=getattr(_svc, "auth_service", None),
        )
        app.register_blueprint(v2_bp)
        logger.info("API v2 blueprint registered at /api/v2")
    except Exception as e:
        logger.warning("Could not register API v2 blueprint: %s", e)

    # Register Web blueprints using factory functions
    try:
        from app.presentation.strategic_sunset_hooks import register_strategic_sunset
        from app.presentation.web.pages import create_pages_blueprint

        register_strategic_sunset(app)
        pages_bp = create_pages_blueprint()
        app.register_blueprint(pages_bp)
    except Exception as e:
        logger.warning("Could not register pages blueprint: %s", e, exc_info=True)

    # Phase 2A-2G: Initialize dual-write proxy for microservice extraction
    try:
        from app.infrastructure.gateway.dual_write_middleware import init_dual_write
        dual_write = init_dual_write()

        # Register microservices by URL for real HTTP reverse calls
        service_urls = {
            "market_data": "http://localhost:5101",
            "strategy": "http://localhost:5201",
            "ai_agent": "http://localhost:5301",
            "portfolio_risk": "http://localhost:5401",
            "execution": "http://localhost:5501",
            "system_user": "http://localhost:5601",
            "data": "http://localhost:5701",
            "research": "http://localhost:5801",
        }

        for name, url in service_urls.items():
            try:
                dual_write.register_service(name, url, traffic_split=0.0)
            except Exception as exc:
                logger.debug("Dual-write service %s not registered: %s", name, exc)

        app.extensions["dual_write"] = dual_write
        logger.info("Dual-write proxy initialized with %d services", len(service_urls))
    except Exception as exc:
        logger.warning("Dual-write initialization skipped: %s", exc)

    try:
        from app.presentation.web.auth import create_auth_blueprint
        auth_service = getattr(services, 'auth_service', None) if services else None
        user_service = getattr(services, 'user_service', None) if services else None
        oauth_provider = getattr(services, 'oauth_provider', None) if services else None
        auth_bp = create_auth_blueprint(
            auth_service=auth_service,
            user_service=user_service,
            app_settings=settings,
            oauth_provider=oauth_provider,
        )
        if auth_bp is not None:
            app.register_blueprint(auth_bp)
        else:
            logger.warning("Auth blueprint not available (services not configured)")
    except Exception as e:
        logger.warning("Could not register auth blueprint: %s", e, exc_info=True)


def create_web_blueprint():
    """Create web blueprint."""
    from flask import Blueprint
    return Blueprint("web", __name__)
