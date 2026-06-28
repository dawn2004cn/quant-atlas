"""Shared runtime for portfolio user / watchlist HTTP routes."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from flask import current_app
from flask_login import current_user

from app.application.errors import AuthorizationError, ValidationError
from app.core.logger import get_logger
from app.core.middleware.request_context import require_authenticated_user_id
from app.presentation.api.route_deps import PortfolioUserRouteDeps
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


class SimpleRateLimiter:
    """Minimal rate limiter (no external dependency)."""

    def __init__(self, window: int = 60, max_attempts: int = 5) -> None:
        self.window = window
        self.max_attempts = max_attempts
        self._buckets: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._buckets.setdefault(key, [])
        bucket[:] = [t for t in bucket if now - t < self.window]
        if len(bucket) >= self.max_attempts:
            return False
        bucket.append(now)
        return True


@dataclass
class PortfolioUserRuntime:
    ctx: ApiV1Context | None
    deps: PortfolioUserRouteDeps
    pwd_change_limiter: SimpleRateLimiter = field(default_factory=lambda: SimpleRateLimiter(window=60, max_attempts=3))

    @property
    def legacy(self) -> bool:
        return self.deps.enable_legacy_response_fields

    def _resolve(self, deps_attr: str, services_attr: str | None = None) -> Any:
        svc = getattr(self.deps, deps_attr, None)
        if svc is not None:
            return svc
        try:
            services = getattr(current_app, "services", None)
            if services is not None:
                return getattr(services, services_attr or deps_attr, None)
        except Exception:
            pass
        return None

    @property
    def watchlist_service(self):
        return self._resolve("watchlist_service")

    @property
    def stock_group_service(self):
        return self._resolve("stock_group_service")

    @property
    def market_service(self):
        return self._resolve("market_service")

    @property
    def user_service(self):
        return self._resolve("user_service")

    @property
    def audit_service(self):
        return self._resolve("audit_trail_service", "user_audit_trail_service")

    def user_id(self) -> int:
        return require_authenticated_user_id()

    def require_ok(self, success: bool, message: str | None = None, *, code: str = "operation_failed") -> None:
        if not success:
            raise ValidationError(code, details={"reason": (message or "").strip()})

    def record_audit(self, action: str, target_type: str, target_id: str, metadata: dict | None = None) -> None:
        if self.audit_service and current_user.is_authenticated:
            try:
                self.audit_service.record(
                    user_id=getattr(current_user, "id", None),
                    action=action,
                    target_type=target_type,
                    target_id=target_id,
                    metadata=metadata or {},
                )
            except (AttributeError, TypeError, ValueError) as exc:
                logger.warning("portfolio_users audit: %s", exc)

    def psychology_after_watchlist(self, action: str, symbol: str) -> None:
        if self.ctx is None or not current_user.is_authenticated:
            return
        sym = (symbol or "").strip()
        if not sym:
            return
        try:
            from app.modules.system.services.helpers.psychology_watchlist_hooks import on_watchlist_mutation

            on_watchlist_mutation(
                user_id=int(self.user_id()),
                symbol=sym,
                action=action,
                market_service=self.market_service,
                task_message_store=getattr(self.ctx, "task_message_store", None),
                lifecycle_service=getattr(self.ctx, "user_lifecycle_service", None),
                notify_message_center=True,
            )
        except (ImportError, AttributeError, TypeError, ValueError) as exc:
            logger.warning("psychology watchlist hook: %s", exc)

    def require_manage_users(self) -> None:
        if not current_user.can_manage_users():
            raise AuthorizationError("user_management_forbidden")
