"""Shared runtime for decision provenance HTTP routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.presentation.api.v1_context import ApiV1Context


@dataclass(frozen=True)
class DecisionProvenanceRuntime:
    ctx: ApiV1Context

    @property
    def legacy(self) -> bool:
        return self.ctx.enable_legacy_response_fields

    @property
    def task_message_store(self):
        return self.ctx.task_message_store

    @staticmethod
    def new_trace_id() -> str:
        return f"trace-{uuid.uuid4().hex[:12]}"
