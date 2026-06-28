from __future__ import annotations

from collections.abc import Callable

from flask_login import current_user

from app.application.errors import ValidationError
from app.domain.authorization_capabilities import Capability


def _get_user_capabilities() -> set[Capability]:
    fn = getattr(current_user, "capabilities", None)
    if callable(fn):
        return {Capability(c) for c in fn() if c in Capability._value2member_map_}
    return set()


def requires_capability(capability: Capability, error_msg: str | None = None):
    """Decorator that requires the current user to hold a capability.

    Usage:
        @blueprint.get("/ai/analyze")
        @login_required
        @requires_capability(Capability.AI_DIAGNOSIS)
        def analyze(): ...
    """
    def decorator(func: Callable) -> Callable:
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if capability not in _get_user_capabilities():
                raise ValidationError(
                    error_msg or f"missing_capability:{capability}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
