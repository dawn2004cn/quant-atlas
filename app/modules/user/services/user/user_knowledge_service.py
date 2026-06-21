from __future__ import annotations

import json
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.config import BASE_DIR
from app.core.interfaces.user_knowledge_service_abc import UserKnowledgeServiceABC


class UserKnowledgeService(UserKnowledgeServiceABC):
    """In-memory/JSON user knowledge store for retail workflow personalization."""

    def __init__(self, store_path: Path | None = None) -> None:
        self._path = Path(store_path or BASE_DIR / "instance" / "user_knowledge.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._profiles: dict[str, dict[str, Any]] = {}
        self._interactions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._decisions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._patterns: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._load()

    def get_profile(self, user_id: str | int) -> dict[str, Any]:
        key = self._key(user_id)
        with self._lock:
            profile = self._profiles.setdefault(key, {"user_id": key, "decision_patterns": []})
            interactions = self._interactions.get(key, [])
            decisions = self._decisions.get(key, [])
            return {
                "user_id": profile.get("user_id", key),
                "total_decisions": len(decisions),
                "total_interactions": len(interactions),
                "last_active": profile.get("last_active"),
                "winning_patterns": self.get_all_patterns(key, outcome=("win", "profit")),
                "decision_patterns": profile.get("decision_patterns", []),
                "recent_decisions": decisions[-10:],
                "recent_interactions": interactions[-10:],
            }

    def get_pattern(self, user_id: str | int, pattern_type: str) -> dict[str, Any] | None:
        pattern_type = (pattern_type or "").strip().lower()
        patterns = self._patterns.get(self._key(user_id), [])
        if pattern_type:
            patterns = [p for p in patterns if str(p.get("pattern_type", "")).lower() == pattern_type]
        return patterns[-1] if patterns else None

    def get_all_patterns(self, user_id: str | int, outcome: str | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
        patterns = list(self._patterns.get(self._key(user_id), []))
        if outcome:
            allowed = {outcome} if isinstance(outcome, str) else set(outcome)
            patterns = [p for p in patterns if str(p.get("outcome", "")).lower() in allowed]
        return patterns[-20:]

    def snapshot_for_user(self, user: Any) -> dict[str, Any]:
        user_id = getattr(user, "id", getattr(user, "user_id", "anonymous"))
        return self.get_profile(user_id)

    def get_workflow_context(self, user_id: str | int) -> dict[str, Any]:
        profile = self.get_profile(user_id)
        return {
            "user_id": user_id,
            "winning_patterns": profile.get("winning_patterns", []),
            "recent_decisions": profile.get("recent_decisions", [])[-5:],
            "preferences": profile.get("preferences", {}),
        }

    def record_interaction(
        self,
        user_id: str | int,
        *,
        outcome: str = "neutral",
        evidence_refs: list[str] | None = None,
        action: str = "unknown",
        page: str | None = None,
        symbol: str | None = None,
        market: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from datetime import datetime, timezone

        entry = {
            "action": action,
            "outcome": outcome,
            "evidence_refs": evidence_refs or [],
            "page": page,
            "symbol": symbol,
            "market": market,
            "detail": detail or {},
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        with self._lock:
            key = self._key(user_id)
            self._interactions[key].append(entry)
            self._interactions[key] = self._interactions[key][-500:]
            self._touch(key)
            self._derive_patterns_locked(key)
            self._save_locked()
        return entry

    def record_decision(
        self,
        user_id: str | int,
        *,
        symbol: str,
        action: str,
        workflow_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from datetime import datetime, timezone

        entry = {
            "symbol": symbol,
            "action": action,
            "workflow_id": workflow_id,
            "detail": detail or {},
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        with self._lock:
            key = self._key(user_id)
            self._decisions[key].append(entry)
            self._decisions[key] = self._decisions[key][-500:]
            self._touch(key)
            self._derive_patterns_locked(key)
            self._save_locked()
        return entry

    def set_preference(self, user_id: str | int, key: str, value: Any) -> None:
        with self._lock:
            profile = self._profiles.setdefault(self._key(user_id), {"user_id": self._key(user_id), "decision_patterns": []})
            profile.setdefault("preferences", {})[key] = value
            self._save_locked()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(data, dict):
            return
        self._profiles = {str(k): v for k, v in data.get("profiles", {}).items()}
        self._interactions = defaultdict(list, {str(k): v for k, v in data.get("interactions", {}).items()})
        self._decisions = defaultdict(list, {str(k): v for k, v in data.get("decisions", {}).items()})
        self._patterns = defaultdict(list, {str(k): v for k, v in data.get("patterns", {}).items()})

    def _save_locked(self) -> None:
        self._path.write_text(
            json.dumps(
                {
                    "profiles": self._profiles,
                    "interactions": dict(self._interactions),
                    "decisions": dict(self._decisions),
                    "patterns": dict(self._patterns),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _touch(self, key: str) -> None:
        from datetime import datetime, timezone

        profile = self._profiles.setdefault(key, {"user_id": key, "decision_patterns": []})
        profile["last_active"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _derive_patterns_locked(self, key: str) -> None:
        decisions = self._decisions.get(key, [])[-100:]
        by_symbol: dict[str, dict[str, Any]] = {}
        for decision in decisions:
            symbol = str(decision.get("symbol") or "unknown")
            row = by_symbol.setdefault(symbol, {"symbol": symbol, "count": 0, "actions": defaultdict(int)})
            row["count"] += 1
            row["actions"][str(decision.get("action") or "unknown")] += 1
            row["last_action"] = decision.get("action")
        self._patterns[key] = [
            {
                "pattern_type": "symbol_focus",
                "symbol": symbol,
                "outcome": "win" if row["count"] >= 2 else "neutral",
                "confidence": min(0.95, row["count"] / 5.0),
                "count": row["count"],
                "actions": dict(row["actions"]),
                "last_action": row.get("last_action"),
            }
            for symbol, row in sorted(by_symbol.items(), key=lambda item: item[1]["count"], reverse=True)
        ]

    @staticmethod
    def _key(user_id: str | int) -> str:
        return str(user_id)


_user_knowledge_service: UserKnowledgeService | None = None


def get_user_knowledge_service() -> UserKnowledgeService:
    global _user_knowledge_service
    if _user_knowledge_service is None:
        _user_knowledge_service = UserKnowledgeService()
    return _user_knowledge_service


def configure_user_knowledge_service(service: UserKnowledgeService | None) -> None:
    global _user_knowledge_service
    if service is not None:
        _user_knowledge_service = service
