"""Shared runtime for signal-flag HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.errors import ValidationError
from app.presentation.api.v1_context import ApiV1Context


@dataclass(frozen=True)
class SignalFlagRuntime:
    ctx: ApiV1Context

    @property
    def legacy(self) -> bool:
        return self.ctx.enable_legacy_response_fields

    @property
    def enable_celery(self) -> bool:
        return bool(self.ctx.enable_celery)

    @property
    def task_dispatcher(self) -> Any:
        return self.ctx.task_dispatcher

    @property
    def task_message_store(self) -> Any:
        return self.ctx.task_message_store

    def require_service(self) -> Any:
        svc = getattr(self.ctx, "signal_flag_service", None)
        if svc is None:
            raise ValidationError("signal_flag_service_unavailable")
        return svc
