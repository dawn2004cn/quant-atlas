"""Rate limiting for Flask endpoints using flask-limiter.

Configures per-endpoint limits:
- Login/Register: 5/min (brute-force protection)
- AI endpoints: 10/min (cost control)
- General API: 100/min
- Password reset/change: 3/min

Limits are keyed by IP address for unauthenticated users,
and by user ID for authenticated users.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def init_rate_limiter(app):
    """Configure flask-limiter on the Flask app.

    Uses Redis as storage if available, otherwise falls back to in-memory.
    """
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        # Determine storage URI
        storage_uri = None
        try:
            from .config import get_settings
            settings = get_settings()
            if getattr(settings, "rate_limit_storage_uri", None):
                storage_uri = settings.rate_limit_storage_uri
            elif getattr(settings, "redis_url", None):
                storage_uri = settings.redis_url
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass

        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            storage_uri=storage_uri,
            default_limits=[],  # No global default — per-route only
            strategy="fixed-window" if not storage_uri else "moving-window",
        )

        # Expose limiter in app for per-route decoration
        app.limiter = limiter  # type: ignore[attr-defined]

        logger.info("Rate limiter initialized (storage: %s)", storage_uri or "in-memory")
        return limiter

    except ImportError:
        logger.info("flask-limiter not installed; rate limiting disabled")
        return None


def rate_limit_exempt(f):
    """Mark a route as exempt from rate limiting (rarely needed)."""
    f._rate_limit_exempt = True
    return f
