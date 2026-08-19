"""Flask middleware: inject request_id and user_id into ContextVars."""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.core.middleware.degraded_context import (
    clear_degraded_state,
    get_degraded_reasons,
    is_system_degraded,
)
from app.core.middleware.resilience import (
    clear_context,
    get_request_id,
    init_context,
    set_user_id,
)

logger = get_logger(__name__)
http_logger = get_logger("app.http")


def current_user_id() -> int | None:
    """Return authenticated user id from ContextVar, or ``None``."""
    from app.core.middleware.resilience import get_user_id

    raw = get_user_id()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def require_authenticated_user_id() -> int:
    """Return authenticated user id from ContextVar or Flask-Login."""
    uid = current_user_id()
    if uid is not None:
        return uid
    try:
        from flask_login import current_user

        if current_user.is_authenticated:
            return int(current_user.id)
    except Exception:
        logger.warning("Suppressed exception", exc_info=True)
        pass
    from app.application.errors import AuthorizationError

    raise AuthorizationError("authentication_required")


def init_request_context_middleware(app: Any) -> None:
    """Register before/after hooks to populate request and user context."""
    from flask import g, request

    @app.before_request
    def _inject_request_context() -> None:
        clear_degraded_state()
        req_id = (request.headers.get("X-Request-ID") or "").strip()
        ctx = init_context(req_id)
        g.request_id = get_request_id()
        g.trace_id = ctx.trace_id
        try:
            from flask_login import current_user

            if current_user.is_authenticated:
                set_user_id(str(current_user.id))
        except Exception as exc:
            logger.debug("request_context.user_id skipped: %s", exc)

    @app.after_request
    def _finalize_request_context(response: Any) -> Any:
        if not request.path.startswith("/static/"):
            path = request.path or ""
            is_socketio_probe = path.startswith("/socket.io")
            status = response.status_code
            if is_socketio_probe and status in (404, 405):
                http_logger.debug(
                    "%s %s %s (socketio not enabled on this process)",
                    request.method,
                    path,
                    status,
                )
            else:
                http_logger.info(
                    "%s %s %s",
                    request.method,
                    path,
                    status,
                )
        rid = get_request_id()
        if rid:
            response.headers.setdefault("X-Request-ID", rid)
        if is_system_degraded():
            response.headers["X-System-Degraded"] = "true"
            reasons = get_degraded_reasons()
            if reasons:
                response.headers["X-System-Degraded-Reason"] = ",".join(reasons[:5])
        clear_degraded_state()
        clear_context()
        return response

    @app.context_processor
    def _inject_realtime_template_flags() -> dict[str, Any]:
        """Expose REALTIME_META to Jinja (base.html socket.io script gate)."""
        from flask import current_app

        meta = current_app.config.get("REALTIME_META") or {}
        if not isinstance(meta, dict):
            meta = {}
        socketio_boot = bool(meta.get("socketio"))
        integrated = bool(getattr(current_app, "socketio", None))
        gateway = bool(meta.get("gateway_mode"))
        return {
            "enable_socketio": socketio_boot and (integrated or gateway),
        }

    logger.debug("Request context middleware initialized")


__all__ = ["init_request_context_middleware", "current_user_id", "require_authenticated_user_id"]
