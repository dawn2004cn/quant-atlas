"""RBAC guard helpers for API route protection."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Literal

from flask import jsonify

from app.core.logger import get_logger

logger = get_logger(__name__)

Permission = Literal["read", "write", "execute", "admin"]
ResourceType = Literal["data", "strategy", "factor", "order", "account", "user"]


def _get_rbac(session=None):
    from app.modules.system.services.institution_tier_service import RBACService

    return RBACService(session=session)


def require_rbac(resource: ResourceType, permission: Permission) -> Callable:
    """Decorator: require RBAC permission for the current user."""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask_login import current_user

            rbac = _get_rbac()
            if not rbac.check_permission(current_user.id, resource, permission):
                return jsonify({
                    "ok": False,
                    "error": "rbac_forbidden",
                    "resource": resource,
                    "permission": permission,
                }), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def check_rbac(user_id: int, resource: ResourceType, permission: Permission, session=None) -> bool:
    """Check RBAC without raising."""
    return _get_rbac(session=session).check_permission(user_id, resource, permission)
