"""Web page decorators for role-based access control."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from flask import abort
from flask_login import current_user

F = TypeVar("F", bound=Callable[..., object])


def role_required(role: str) -> Callable[[F], F]:
    """Require the authenticated user to have a specific role.

    Must be used *after* ``@login_required`` (this decorator does not
    authenticate, only authorizes). Example::

        @blueprint.route("/admin-only")
        @login_required
        @role_required("admin")
        def admin_only():
            ...
    """

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            user_role = getattr(current_user, "role", None)
            # "admin" always passes; otherwise exact match required.
            if user_role != "admin" and user_role != role:
                abort(403)
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def admin_required() -> Callable[[F], F]:
    """Convenience decorator requiring the "admin" role."""
    return role_required("admin")
