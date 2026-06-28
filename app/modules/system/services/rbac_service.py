"""RBAC service - role-based access control backed by SQLAlchemy."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.core.logger import get_logger
from app.infrastructure.database.models import Role, UserRoleAssignment

logger = get_logger(__name__)

Permission = Literal["read", "write", "execute", "admin"]
ResourceType = Literal[
    "data", "strategy", "factor", "order", "account", "user"
]


class RBACService:
    """Fine-grained role-based access control backed by SQLAlchemy.

    Roles are defined in the ``roles`` table with JSON permissions.
    User assignments live in ``user_role_assignments``.
    """

    # Default role definitions: role_id -> {name, permissions}
    _DEFAULT_ROLES: dict[str, dict[str, Any]] = {
        "researcher": {
            "name": "研究员",
            "permissions": {
                "data": ["read"],
                "strategy": ["read", "write"],
                "factor": ["read", "write"],
                "order": ["read"],
                "account": [],
                "user": [],
            },
        },
        "trader": {
            "name": "交易员",
            "permissions": {
                "data": ["read"],
                "strategy": ["read"],
                "factor": ["read"],
                "order": ["read", "write", "execute"],
                "account": ["read"],
                "user": [],
            },
        },
        "risk_manager": {
            "name": "风控经理",
            "permissions": {
                "data": ["read"],
                "strategy": ["read"],
                "factor": ["read"],
                "order": ["read"],
                "account": ["read", "write"],
                "user": [],
            },
        },
        "compliance": {
            "name": "合规官",
            "permissions": {
                "data": ["read"],
                "strategy": ["read"],
                "factor": ["read"],
                "order": ["read"],
                "account": ["read"],
                "user": ["read"],
            },
        },
        "admin": {
            "name": "管理员",
            "permissions": {
                "data": ["read", "write", "execute"],
                "strategy": ["read", "write", "execute"],
                "factor": ["read", "write", "execute"],
                "order": ["read", "write", "execute"],
                "account": ["read", "write", "admin"],
                "user": ["read", "write", "admin"],
            },
        },
    }

    def __init__(self, session=None):
        self._session = session

    # -- Internal helpers --

    def _get_session(self):
        if self._session is not None:
            return self._session
        return None

    @staticmethod
    def _register_default_roles(session) -> None:
        """Seed canonical role definitions (idempotent via code uniqueness)."""
        for role_id, info in RBACService._DEFAULT_ROLES.items():
            role = session.query(Role).filter_by(code=role_id).first()
            if role is None:
                role = Role(
                    code=role_id,
                    label=info["name"],
                    permissions_json=json.dumps(
                        info["permissions"], ensure_ascii=False
                    ),
                )
                session.add(role)
        session.flush()

    # -- Public API --

    def assign_role(
        self,
        user_id: int,
        role_id: str,
        scope: str = "global",
        assigned_by: int | None = None,
    ) -> dict[str, Any]:
        """Assign a role to a user."""
        session = self._get_session()
        if session is None:
            raise RuntimeError("RBACService requires a SQLAlchemy session")

        self._register_default_roles(session)

        role = session.query(Role).filter_by(code=role_id).first()
        if role is None:
            raise ValueError(f"Unknown role: {role_id}")

        assignment = (
            session.query(UserRoleAssignment)
            .filter_by(user_id=user_id)
            .first()
        )
        if assignment is None:
            assignment = UserRoleAssignment(
                user_id=user_id,
                role_id=role.id,
                scope=scope,
                assigned_by=assigned_by,
            )
            session.add(assignment)
        else:
            assignment.role_id = role.id
            assignment.scope = scope
            if assigned_by is not None:
                assignment.assigned_by = assigned_by

        session.flush()
        logger.info(
            "User %d assigned role %s (scope=%s)",
            user_id, role_id, scope,
        )
        return {"user_id": user_id, "role_id": role_id, "scope": scope}

    def check_permission(
        self, user_id: int, resource: ResourceType, permission: Permission
    ) -> bool:
        """Check if a user has a specific permission."""
        session = self._get_session()
        if session is None:
            return True  # no session = legacy open access

        assignment = (
            session.query(UserRoleAssignment)
            .filter_by(user_id=user_id)
            .first()
        )
        if assignment is None:
            return True  # no assignment = legacy open access

        role = session.query(Role).filter_by(id=assignment.role_id).first()
        if role is None:
            return False

        perms = json.loads(role.permissions_json)
        resource_perms = perms.get(resource, [])
        return permission in resource_perms or "admin" in resource_perms

    def require_permission(
        self, user_id: int, resource: ResourceType, permission: Permission
    ) -> None:
        """Raise PermissionError if user lacks permission."""
        if not self.check_permission(user_id, resource, permission):
            raise PermissionError(
                f"User {user_id} lacks {permission} on {resource}"
            )

    def get_user_role(self, user_id: int) -> str | None:
        """Get the role name for a user."""
        session = self._get_session()
        if session is None:
            return None
        assignment = (
            session.query(UserRoleAssignment)
            .filter_by(user_id=user_id)
            .first()
        )
        if not assignment:
            return None
        role = session.query(Role).filter_by(id=assignment.role_id).first()
        return role.label if role else None

    def check_multi_resource(
        self, user_id: int, resources: dict[str, str]
    ) -> dict[str, bool]:
        """Check multiple resource permissions at once."""
        result = {}
        for resource, permission in resources.items():
            result[f"{resource}:{permission}"] = self.check_permission(
                user_id, resource, permission
            )
        return result

    def list_user_permissions(self, user_id: int) -> dict[str, list[str]]:
        """List all permissions for a user, grouped by resource."""
        session = self._get_session()
        if session is None:
            resources = [
                "data", "strategy", "factor", "order", "account", "user"
            ]
            return {res: ["read", "write"] for res in resources}

        assignment = (
            session.query(UserRoleAssignment)
            .filter_by(user_id=user_id)
            .first()
        )
        if not assignment:
            return {}

        role = session.query(Role).filter_by(id=assignment.role_id).first()
        if not role:
            return {}

        perms = json.loads(role.permissions_json) if role.permissions_json else {}
        return perms

    def audit_change(
        self,
        changed_by: int,
        target_user: int,
        action: str,
        detail: dict | None = None,
    ) -> dict:
        """Log a permission change for audit trail."""
        record = {
            "audit_id": f"perm.{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "changed_by": changed_by,
            "target_user": target_user,
            "action": action,
            "detail": detail or {},
        }
        log_path = (
            Path(__file__).resolve().parents[4] / "instance" / "rbac_audit.jsonl"
        )
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info(
            "RBAC audit: %s by user %d on user %d",
            action, changed_by, target_user,
        )
        return record

    def list_roles(self) -> list[dict]:
        """List all available roles with their permissions."""
        session = self._get_session()
        if session is None:
            return [
                {
                    "role_id": rid,
                    "name": info["name"],
                    "permissions": {
                        k: v for k, v in info["permissions"].items() if v
                    },
                }
                for rid, info in self._DEFAULT_ROLES.items()
            ]

        roles = session.query(Role).all()
        return [
            {
                "role_id": r.code,
                "name": r.label,
                "permissions": {
                    k: v
                    for k, v in (
                        json.loads(r.permissions_json)
                        if r.permissions_json
                        else {}
                    ).items()
                    if v
                },
            }
            for r in roles
        ]

    def get_user_assignment(self, user_id: int) -> dict[str, Any] | None:
        """Get role assignment for a user."""
        session = self._get_session()
        if session is None:
            return None

        assignment = (
            session.query(UserRoleAssignment)
            .filter_by(user_id=user_id)
            .first()
        )
        if not assignment:
            return None
        role = session.query(Role).filter_by(id=assignment.role_id).first()
        return {
            "user_id": user_id,
            "role_id": assignment.role_id,
            "role_name": role.label if role else assignment.role_id,
            "scope": assignment.scope,
        }
