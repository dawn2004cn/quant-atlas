from __future__ import annotations

"""Resolve per-user presentation density for decision-oriented APIs."""

from pathlib import Path
from typing import Any

from app.core.registry import register_service
from app.core.runtime_config import get_runtime


ROLE_PRESETS: dict[str, dict[str, Any]] = {
    "researcher": {
        "role": "researcher",
        "response_density": "deep",
        "include_raw_factors": True,
        "include_signals": True,
        "include_risk_warnings": True,
        "primary_components": ["raw_factors", "evidence_chain", "scenario_notes"],
        "narrative_level": "full",
    },
    "trader": {
        "role": "trader",
        "response_density": "compact",
        "include_raw_factors": False,
        "include_signals": True,
        "include_risk_warnings": True,
        "primary_components": ["signals", "risk_warnings", "action_items"],
        "narrative_level": "brief",
    },
    "default": {
        "role": "default",
        "response_density": "balanced",
        "include_raw_factors": False,
        "include_signals": True,
        "include_risk_warnings": True,
        "primary_components": ["summary", "evidence_chain", "signals"],
        "narrative_level": "normal",
    },
}


@register_service(name="user_decision_context_service")
class UserDecisionContextService:
    """Build a stable DTO contract for user-specific API shaping."""

    def __init__(self, journal: Any | None = None) -> None:
        from .decision_event_journal import DecisionEventJournal

        store = get_runtime("DECISION_EVENT_STORE", "instance/decision_events.json")
        self._journal = journal or DecisionEventJournal(store_path=Path(store))

    def record_event(
        self,
        user_id: str | int,
        *,
        event_type: str,
        symbol: str = "",
        market: str = "CN",
        page: str = "",
        component: str = "",
        action: str = "",
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._journal.record(
            user_id,
            event_type=event_type,
            symbol=symbol,
            market=market,
            page=page,
            component=component,
            action=action,
            detail=detail,
        )

    def event_history(
        self,
        user_id: str | int,
        *,
        limit: int = 50,
        event_type: str | None = None,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._journal.history(user_id, limit=limit, event_type=event_type, symbol=symbol)

    def event_summary(self, user_id: str | int) -> dict[str, Any]:
        return self._journal.summary(user_id)

    def build_context(
        self,
        *,
        user_id: str | int = "anonymous",
        role: str | None = None,
        investment_profile: dict[str, Any] | None = None,
        page_preferences: dict[str, Any] | None = None,
        page: str | None = None,
    ) -> dict[str, Any]:
        profile = investment_profile or {}
        preferences = page_preferences or {}
        resolved_role = self._resolve_role(role, profile)
        preset = dict(ROLE_PRESETS[resolved_role])

        hidden = set(str(x) for x in preferences.get("hidden_cards") or [])
        components = [
            component for component in preset["primary_components"] if component not in hidden
        ]

        event_summary = self._journal.summary(user_id) if user_id != "anonymous" else {}

        return {
            "user_id": str(user_id or "anonymous"),
            "page": page or "global",
            "role": preset["role"],
            "response_density": preset["response_density"],
            "dto_directives": {
                "include_raw_factors": preset["include_raw_factors"],
                "include_signals": preset["include_signals"],
                "include_risk_warnings": preset["include_risk_warnings"],
                "narrative_level": preset["narrative_level"],
                "primary_components": components,
            },
            "risk_context": {
                "risk_level": profile.get("risk_level", "balanced"),
                "horizon": profile.get("horizon", "swing"),
                "style_tags": profile.get("style_tags", []),
            },
            "decision_history": {
                "total_events": event_summary.get("total_events", 0),
                "frequent_symbols": event_summary.get("frequent_symbols", []),
                "recent_actions": event_summary.get("recent_actions", [])[:5],
            },
        }

    @staticmethod
    def _resolve_role(role: str | None, profile: dict[str, Any]) -> str:
        raw_role = str(role or profile.get("decision_role") or "").strip().lower()
        if raw_role in ROLE_PRESETS and raw_role != "default":
            return raw_role

        style_tags = {str(tag).strip().lower() for tag in profile.get("style_tags") or []}
        horizon = str(profile.get("horizon") or "").strip().lower()
        if style_tags & {"research", "factor", "alpha"}:
            return "researcher"
        if style_tags & {"trading", "execution", "intraday"} or horizon in {"intraday", "day"}:
            return "trader"
        return "default"


__all__ = ["UserDecisionContextService", "ROLE_PRESETS"]
