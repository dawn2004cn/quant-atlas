from __future__ import annotations

"""Telemetry service for tracking asynchronous Swarm and Agent tasks.

Provides a unified interface for the message store system.
"""


from typing import Any


class AgentTelemetryService:
    """Service for reporting agent task progress."""

    def __init__(self, store: Any | None = None):
        if store is not None:
            self.store = store
        else:
            from app.domain.ports.infrastructure_ports import IMessageStore
            from app.modules.system.services.helpers.service_resolver_access import resolve_optional_service
            self.store = resolve_optional_service(IMessageStore)
            if self.store is None:
                from app.modules.system.services.helpers.task_message_access import get_task_message_store
                self.store = get_task_message_store()

    def report_event(
        self,
        event: str,
        task_id: str,
        task_name: str,
        detail: str = "",
        meta: dict[str, Any] | None = None,
    ) -> str:
        """Report a Swarm/Agent task event."""
        return self.store.push(
            event=event,
            task_id=task_id,
            task_name=task_name,
            detail=detail,
            meta=meta
        )
