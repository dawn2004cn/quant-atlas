from __future__ import annotations

from typing import Any

from app.core.event_bus import get_event_bus


class RealtimeGatewayService:
    """Unified contract for realtime market, agent, task, and healing streams."""

    def build_manifest(self, ctx: Any) -> dict[str, Any]:
        bus = get_event_bus()
        return {
            "schema_version": "v1",
            "channels": [
                {"id": "market", "transport": "socketio", "events": ["MarketDataUpdatedEvent"]},
                {
                    "id": "agent",
                    "transport": "event_bus",
                    "events": [
                        "CapabilityExecutedEvent",
                        "WorkflowCompletedEvent",
                        "DebateRoundEvent",
                    ],
                },
                {"id": "tasks", "transport": "sse", "events": ["task_started", "task_progress", "task_succeeded", "task_failed"]},
                {
                    "id": "system",
                    "transport": "event_bus",
                    "events": [
                        "ServiceStartedEvent",
                        "ServiceStoppedEvent",
                        "TruthDeviationEvent",
                        "AnalysisStaleEvent",
                    ],
                },
                {
                    "id": "truth",
                    "transport": "event_bus",
                    "events": ["TruthDeviationEvent", "AnalysisStaleEvent"],
                    "priority_range": [50, 100],
                },
                {
                    "id": "alerts",
                    "transport": "socketio",
                    "room": "alerts",
                    "events": ["CrossTeamSiteAlertEvent", "MetaArbiterActivatedEvent"],
                },
                {
                    "id": "collaboration",
                    "transport": "socketio",
                    "room": "team_blackboard:{team_id}",
                    "events": ["team_blackboard_entry", "team_blackboard_consensus"],
                },
            ],
            "endpoints": {
                "task_stream": "/api/v1/system/tasks/{task_id}/stream",
                "recent_events": "/api/v1/system/events/recent",
                "system_pulse": "/api/v1/system/pulse",
                "cross_team_alerts": "/api/v1/system/cross-team/alerts",
                "meta_arbiter_recent": "/api/v1/system/meta-arbiter/recent",
                "alert_center": "/api/v1/system/alerts?category=consensus",
            },
            "socketio_enabled": hasattr(ctx, "socketio") or False,
            "subscribers": bus.list_subscribers(),
        }

    def recent_events(self, *, limit: int = 50) -> dict[str, Any]:
        items = get_event_bus().list_recent_events(limit=limit)
        return {"items": items, "count": len(items)}

    @staticmethod
    def team_blackboard_room(team_id: int) -> str:
        return f"team_blackboard:{int(team_id)}"

    def push_team_blackboard_entry(self, team_id: int, entry: dict[str, Any]) -> dict[str, Any]:
        """Socket.IO push when a teammate submits blackboard evidence."""
        from app.infrastructure.realtime.websocket_adapter import broadcast_to_room

        room = self.team_blackboard_room(team_id)
        receivers = broadcast_to_room(
            room,
            "team_blackboard_entry",
            {"team_id": int(team_id), "entry": entry},
        )
        return {"ok": True, "room": room, "receivers": receivers}

    def push_team_blackboard_consensus(self, team_id: int, consensus: dict[str, Any]) -> dict[str, Any]:
        from app.infrastructure.realtime.websocket_adapter import broadcast_to_room

        room = self.team_blackboard_room(team_id)
        receivers = broadcast_to_room(
            room,
            "team_blackboard_consensus",
            {"team_id": int(team_id), "consensus": consensus},
        )
        return {"ok": True, "room": room, "receivers": receivers}

