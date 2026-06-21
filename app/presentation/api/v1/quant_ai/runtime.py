"""Shared runtime helpers for quant/AI HTTP routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.application.errors import ValidationError
from app.core.middleware.request_context import require_authenticated_user_id
from app.presentation.api.route_deps import AiRouteDeps


@dataclass(frozen=True)
class QuantAiRuntime:
    legacy: bool
    enable_qlib: bool
    strategy_service: Any | None
    prediction_service: Any | None
    selection_source_service: Any | None
    ai_analysis_service: Any | None
    ai_research_service: Any | None
    task_message_store: Any | None

    @classmethod
    def from_deps(cls, deps: AiRouteDeps) -> QuantAiRuntime:
        return cls(
            legacy=deps.enable_legacy_response_fields,
            enable_qlib=deps.enable_qlib,
            strategy_service=deps.strategy_service,
            prediction_service=deps.prediction_service,
            selection_source_service=deps.selection_source_service,
            ai_analysis_service=deps.ai_analysis_service,
            ai_research_service=deps.ai_research_service,
            task_message_store=deps.task_message_store,
        )

    def require_strategy_service(self) -> Any:
        if self.strategy_service is None:
            raise ValidationError("strategy_service not configured, enable Qlib or check ENABLE_QLIB")
        return self.strategy_service

    def require_selection_source_service(self) -> Any:
        if self.selection_source_service is None:
            raise ValidationError("selection_source_service not configured; check bootstrap wiring")
        return self.selection_source_service

    def require_ai_research_service(self) -> Any:
        if self.ai_research_service is None:
            raise ValidationError(
                "ai_research_service not configured; check LLM env and bootstrap wiring",
            )
        return self.ai_research_service

    def new_trace_id(self) -> str:
        return f"trace-{uuid.uuid4().hex[:12]}"

    def push_task(
        self,
        *,
        event: str,
        task_name: str,
        detail: str,
        meta: dict[str, Any],
    ) -> None:
        if self.task_message_store is None:
            return
        self.task_message_store.push(
            event=event,
            task_id=f"sync-{uuid.uuid4().hex[:12]}",
            task_name=task_name,
            detail=detail,
            meta={**meta, "trace_id": self.new_trace_id()},
        )


def authenticated_user_id() -> int:
    return require_authenticated_user_id()
