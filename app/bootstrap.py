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

# Flasks test_client expects werkzeug.__version__ on older Werkzeug.
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


def _load_warm_runtime_extensions():
    import app.warm_runtime_extensions  # noqa: F401


class _ApiBundle:
    def __init__(self, services):
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


def _build_flask_app(settings):
    """Step 1: Build Flask app shell + security config."""
    run_security_sanity_checks()
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
        WTF_CSRF_ENABLED=False,
    )
    is_test = app.config.get("TESTING", False)
    is_dev = get_runtime_bool("FLASK_DEBUG", False)
    if not is_dev and not is_test:
        app.debug = False
    return app


def _wire_services(app, settings):
    """Step 2: Wire services and data infrastructure."""
    services = create_services(registry_config=build_registry_config(settings))
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
    return services


def _wire_event_bus(app):
    """Step 3: Wire Redis Streams persistence into EventBus."""
    from .core.runtime_config import get_runtime
    redis_url = (get_runtime("REDIS_URL") or "").strip()
    if redis_url:
        from .core.event_bus import RedisStreamBackend, get_event_bus
        get_event_bus().set_redis_backend(RedisStreamBackend(redis_url))


def _wire_auth_and_security(app, services, settings):
    """Step 4: Auth + security headers + CSRF."""
    user_svc = getattr(services, "user_service", None)
    user_repo = getattr(user_svc, "_repository", None) if user_svc else None
    login_manager = configure_login_manager(app, user_repo, logger=logger)
    csrf_protect(app)
    register_api_error_handlers(app)
    from app.presentation.api.v1_deprecation import register_v1_deprecation_headers
    register_v1_deprecation_headers(app)
    setup_flask_login_errors(app, login_manager)
    configure_security_headers(app, debug=bool(getattr(settings, "debug", False)))


def _wire_cors(app, settings):
    """Step 5: CORS strict allowlist, no wildcard fallback."""
    try:
        from flask_cors import CORS
        from app.core.runtime_config import get_runtime as _cors_get_runtime
        raw = (
            getattr(settings, "cors_allowed_origins", None)
            or (_cors_get_runtime("CORS_ALLOWED_ORIGINS") or "")
            or ""
        )
        if raw:
            origins = [o.strip() for o in raw.split(",") if o.strip()]
        else:
            origins = []
        if not origins:
            origins = ["http://localhost:5173"]
            logger.info(
                "CORS allowed origins set to [http://localhost:5173] (dev default). "
                "Set CORS_ALLOWED_ORIGINS in .env to override."
            )
        CORS(
            app,
            resources={
                r"/api/*": {"origins": origins},
                r"/v2/*": {"origins": origins},
            },
            supports_credentials=True,
        )
    except Exception as exc:
        logger.warning("CORS init skipped: %s", exc)


def _wire_middleware(app):
    """Step 6: Middleware stack."""
    from app.core.middleware.prometheus_middleware import init_prometheus_middleware
    from app.core.middleware.request_context import init_request_context_middleware
    init_request_context_middleware(app)
    from app.presentation.api.auth_middleware import install as install_auth_middleware
    install_auth_middleware(app)
    from app.core.middleware.api_rate_limit import init_api_rate_limit_middleware
    init_api_rate_limit_middleware(app)
    init_prometheus_middleware(app)


def _wire_blueprints_and_modules(app, services, settings):
    """Step 7: Blueprints + modules + realtime."""
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
    init_optional(
        "realtime",
        lambda: init_realtime(
            app, settings,
            market_service=getattr(services, "market_service", None),
        ),
    )



def _trigger_legacy_migration(services: object) -> None:
    "Auto-detect legacy .db files and migrate to data lake on boot."
    "Non-blocking: runs via threading so the app starts immediately."
    "Any migration errors are logged but do not block the bootstrap."
    try:
        lake_manager = getattr(services, "data_lake_manager", None)
        if lake_manager is None:
            return
        manifest = lake_manager.get_manifest()
        if manifest.get("status") == "migration_complete":
            return
        import threading
        import asyncio

        def _run():
            try:
                from app.bootstrap_components.service_wiring import _get_registry
                reg = _get_registry()
                from app.modules.data.services.legacy_migration_service import LegacyDataMigrationService
                svc = LegacyDataMigrationService(reg)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(svc.migrate_all())
                    logger.info("Legacy migration completed: %d rows from %d files",
                                result.get("total_rows_migrated", 0),
                                result.get("total_files_scanned", 0))
                finally:
                    loop.close()
            except Exception as exc:
                logger.warning("Legacy migration background task failed: %s", exc)

        t = threading.Thread(target=_run, daemon=True, name="legacy-migration")
        t.start()
    except Exception as exc:
        logger.debug("Legacy migration trigger skipped: %s", exc)
def create_app():
    """Create and configure the Flask application."""
    start_time = time.perf_counter()
    reset_settings()
    setup_logging()
    settings = get_settings()
    app = _build_flask_app(settings)
    services = _wire_services(app, settings)
    _wire_event_bus(app)
    _wire_auth_and_security(app, services, settings)
    _wire_cors(app, settings)
    _wire_middleware(app)
    _wire_blueprints_and_modules(app, services, settings)
    elapsed = time.perf_counter() - start_time
    # Auto-trigger legacy .db migration to data lake (async, non-blocking)
    _trigger_legacy_migration(services)
    logger.info("Application bootstrap completed in %.3fs", elapsed)
    return app
