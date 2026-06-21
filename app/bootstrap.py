from __future__ import annotations

"""Application bootstrap."""

import logging
import time
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from flask import Flask

from app.core.runtime_config import get_runtime_bool

# Flask's test_client expects ``werkzeug.__version__`` on older Werkzeug.
# Werkzeug 3 removed this attribute; tests rely on a lightweight shim.
try:
    import werkzeug  # type: ignore

    if not hasattr(werkzeug, "__version__"):
        werkzeug.__version__ = "3.0.0"  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    logger.warning("werkzeug patch failed", exc_info=True)

from .core.secrets import run_security_sanity_checks
from .bootstrap_components.bootstrap_helpers import (
    build_registry_config,
    init_cluster_event_bus,
    init_optional,
    init_required,
    init_side_effects,
    register_data_sources,
    start_truth_sentry,
)
from .bootstrap_components.module_wiring import initialize_all_modules
from .bootstrap_components.presentation import register_blueprints
from .bootstrap_components.realtime import init_realtime
from .bootstrap_components.services import create_services
from .config import get_settings
from .config.app_settings import reset_settings
from .core.logger import setup_logging
from .core.i18n import t
from .core.asset_versioning import init_app as init_asset_versioning
from .core.plugins import PluginRegistry
from .presentation.csrf_protection import csrf_protect
from .bootstrap_components.presentation import configure_login_manager
from .bootstrap_components.security_headers import configure_security_headers, csp_nonce
from app.presentation.api.error_handlers import register_api_error_handlers, setup_flask_login_errors

logger = logging.getLogger(__name__)


def _load_warm_runtime_extensions() -> None:
    import app.warm_runtime_extensions  # noqa: F401


class _ApiBundle:
    def __init__(self, services: Any):
        self.services = services
        self.repositories = services
        news_provider = getattr(services, "news_provider", None)
        if news_provider is None:
            try:
                from app.modules.system.services.helpers.news_provider_wiring import get_news_provider

                news_provider = get_news_provider()
            except Exception:
                news_provider = None
        self.providers = SimpleNamespace(news_provider=news_provider)


def create_app() -> Flask:
    """Create and configure the Flask application."""
    start_time = time.perf_counter()

    # Tests often mutate env vars (e.g. ENABLE_QLIB). Settings are cached
    # process-wide, so we must reset them on each create_app().
    reset_settings()

    setup_logging()

    # Security: fail fast if .env still contains known default passwords or
    # hardcoded internal IPs. Operators must move secrets to environment vars
    # or a secrets manager before starting the app.
    run_security_sanity_checks()

    settings = get_settings()
    if not settings.secret_key:
        raise RuntimeError(
            "FLASK_SECRET_KEY must be set in .env or environment. "
            "Sessions will be invalidated on restart without it."
        )

    PluginRegistry.discover_and_register("app.infrastructure.market.plugins")
    Path(settings.static_folder).mkdir(parents=True, exist_ok=True)

    app = Flask(
        __name__,
        template_folder=settings.template_folder,
        static_folder=settings.static_folder,
    )
    app.config.update(
        SECRET_KEY=settings.secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=get_runtime_bool("SESSION_COOKIE_SECURE", not settings.debug),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        WTF_CSRF_ENABLED=False,  # custom csrf_protect() handles web + API token paths
    )

    # Security: never allow debug mode in production
    is_test = app.config.get("TESTING", False)
    is_dev = get_runtime_bool("FLASK_DEBUG", False)
    if not is_dev and not is_test:
        app.debug = False

    services = create_services(registry_config=build_registry_config(settings))
    # Alembic schema bootstrap during service wiring may clobber logging via fileConfig.
    setup_logging()
    app.services = services
    app.container = services

    from .core.data_gateway import DataGateway
    app.data_gateway = DataGateway(settings)

    from .core.data_write_broker import init_write_broker
    app.write_broker = init_write_broker(data_dir=getattr(settings, "DATA_DIR", None))

    init_required("service_registry", lambda: None)
    init_optional("truth_sentry", start_truth_sentry)
    init_optional("warm_runtime_extensions", _load_warm_runtime_extensions)
    register_data_sources()
    init_cluster_event_bus(app, settings)

    # Wire Redis Streams persistence into the EventBus singleton
    from .core.runtime_config import get_runtime
    redis_url = (get_runtime("REDIS_URL") or "").strip()
    if redis_url:
        from .core.event_bus import RedisStreamBackend, get_event_bus
        get_event_bus().set_redis_backend(RedisStreamBackend(redis_url))

    user_svc = getattr(services, "user_service", None)
    user_repo = getattr(user_svc, "_repository", None) if user_svc else None
    login_manager = configure_login_manager(app, user_repo, logger=logger)
    csrf_protect(app)
    # Ensure Flask-Login unauthorized requests return JSON 401 for API routes,
    # aligning with API contract tests.
    register_api_error_handlers(app)
    from app.presentation.api.v1_deprecation import register_v1_deprecation_headers

    register_v1_deprecation_headers(app)
    setup_flask_login_errors(app, login_manager)
    configure_security_headers(app, debug=bool(getattr(settings, "debug", False)))

    # CORS: restrict to configured allowed origins for API routes
    try:
        from flask_cors import CORS
        from app.core.runtime_config import get_runtime as _cors_get_runtime
        _cors_allowed = (getattr(settings, "cors_allowed_origins", None)
                         or (_cors_get_runtime("CORS_ALLOWED_ORIGINS") or "")
                         or "")
        if _cors_allowed:
            origins = [o.strip() for o in _cors_allowed.split(",") if o.strip()]
        else:
            origins = []
        CORS(
            app,
            resources={
                r"/api/*": {"origins": origins if origins else "*"},
                r"/v2/*": {"origins": origins if origins else "*"},
            },
            supports_credentials=True,
        )
    except Exception as exc:
        logger.warning("CORS init skipped: %s", exc)

    from app.core.middleware.prometheus_middleware import init_prometheus_middleware
    from app.core.middleware.request_context import init_request_context_middleware

    init_request_context_middleware(app)
    from app.core.middleware.api_rate_limit import init_api_rate_limit_middleware

    init_api_rate_limit_middleware(app)
    init_prometheus_middleware(app)
    init_asset_versioning(app)
    app.jinja_env.globals["csp_nonce"] = csp_nonce
    app.jinja_env.globals["t"] = t
    app.jinja_env.globals["_"] = t
    api_bundle = _ApiBundle(services)
    init_side_effects()
    task_message_store = None
    try:
        from app.modules.system.services.helpers.task_message_wiring import get_task_message_store

        task_message_store = get_task_message_store()
    except Exception as exc:
        logger.warning("task_message_store unavailable for API context: %s", exc)
    register_blueprints(
        app,
        settings=settings,
        api_bundle=api_bundle,
        services=services,
        task_message_store=task_message_store,
    )
    initialize_all_modules(container=services)

    init_optional("realtime", lambda: init_realtime(app, settings, market_service=getattr(services, "market_service", None)))

    elapsed = time.perf_counter() - start_time
    logger.info("Application bootstrap completed in %.3fs", elapsed)
    return app
