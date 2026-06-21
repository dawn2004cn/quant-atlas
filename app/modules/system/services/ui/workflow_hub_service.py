from __future__ import annotations

from typing import Any

from app.domain.dto.workflow_hub_dto import WorkflowHubDTO, WorkflowHubSectionDTO


class WorkflowHubService:
    """Aggregate workflow, task, and journey entrypoints for the unified hub."""

    def build_hub(self, ctx: Any, *, active_limit: int = 20) -> WorkflowHubDTO:
        active_jobs = self._active_jobs(ctx, active_limit)
        workflows = self._workflows(ctx)
        capabilities = self._capabilities(ctx)
        return WorkflowHubDTO(
            active_jobs=active_jobs,
            workflows=workflows,
            capabilities=capabilities,
            sections=self._sections(),
            human_intervention_count=sum(
                1 for item in workflows if item.get("state") == "waiting_human"
            ),
        )

    def _active_jobs(self, ctx: Any, limit: int) -> list[dict[str, Any]]:
        tracker = getattr(ctx, "active_job_tracker_service", None)
        if tracker is None:
            return []
        try:
            return tracker.list_active_jobs(limit=limit).get("items", [])
        except Exception:
            return []

    def _workflows(self, ctx: Any) -> list[dict[str, Any]]:
        service = getattr(ctx, "workflow_service", None)
        if service is None:
            return []
        try:
            return service.list_workflows()
        except Exception:
            return []

    def _capabilities(self, ctx: Any) -> list[str]:
        facade = getattr(ctx, "tool_facade_service", None)
        if facade is None or not hasattr(facade, "list_capabilities"):
            return []
        try:
            return sorted(facade.list_capabilities())
        except Exception:
            return []

    def _sections(self) -> list[WorkflowHubSectionDTO]:
        return [
            WorkflowHubSectionDTO(
                id="discovery",
                label="Discovery",
                entrypoints=[
                    {"label": "Market Panorama", "href": "/markets/CN/panorama"},
                    {"label": "Hot Sectors", "href": "/hot-sectors"},
                    {"label": "Stock Discovery", "href": "/stocks/search?mode=discover"},
                ],
            ),
            WorkflowHubSectionDTO(
                id="research",
                label="Research",
                entrypoints=[
                    {"label": "AI Evidence", "href": "/ai-evidence"},
                    {"label": "Strategy Copilot", "href": "/strategy/copilot"},
                    {"label": "Attribution Timeline", "href": "/stocks/{market}/{symbol}/attribution-timeline"},
                ],
            ),
            WorkflowHubSectionDTO(
                id="execution",
                label="Execution",
                entrypoints=[
                    {"label": "Backtest Workflow", "href": "/workflows/trading"},
                    {"label": "Trade Plan", "href": "/trade-plan"},
                    {"label": "Task Feedback", "href": "/system/task-messages"},
                ],
            ),
        ]

