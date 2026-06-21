from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class UserLifecycleService:
    """Manage user lifecycle settings — persisted via JSON or SQL collaboration repo."""

    def __init__(
        self,
        store_path: Optional[Path] = None,
        access_policy_service: Any | None = None,
        investment_profile_service: Any | None = None,
        page_preference_service: Any | None = None,
        audit_trail_service: Any | None = None,
        watchlist_service: Any | None = None,
        stock_group_service: Any | None = None,
        collaboration_repository: Any | None = None,
    ) -> None:
        self._store_path: Path = store_path or Path("user_lifecycle.json")
        self._access = access_policy_service
        self._profile = investment_profile_service
        self._pages = page_preference_service
        self._audit = audit_trail_service
        self._watchlist = watchlist_service
        self._groups = stock_group_service
        self._collab = collaboration_repository
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self._store_path.exists():
            try:
                with open(self._store_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._store_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get_settings(self, user: Any) -> Dict[str, Any]:
        uid = getattr(user, "id", None) or getattr(user, "user_id", None)
        if uid is None:
            return {"error": "user has no id"}

        settings: Dict[str, Any] = self._data.get(str(uid), {})

        # If collaboration repo is available, prefer SQL tenant data
        if self._collab is not None:
            try:
                tenant = self._collab.ensure_personal_tenant(uid)
                settings["tenant_id"] = tenant.id
                settings["sync_status"] = {"mode": "sql_tenant"}

                # Merge lifecycle row data
                row = self._collab.get_lifecycle_row(uid)
                if isinstance(row, dict):
                    settings.update(row)
            except Exception:  # noqa: BLE001
                logger.warning("Suppressed exception in get_settings", exc_info=True)
                pass  # Fall back to JSON data

        # Merge from optional services
        if self._access:
            snap = self._access.snapshot_for_user(uid)
            if snap:
                settings["access_snapshot"] = snap
        if self._profile:
            profile = self._profile.get_profile(uid)
            if profile:
                settings["investment_profile"] = profile
        if self._pages:
            prefs = self._pages.get_preferences(str(uid))
            if prefs:
                settings["page_preferences"] = prefs
        if self._audit:
            actions = self._audit.list_user_actions(uid)
            if actions:
                settings["recent_actions"] = actions[:20]
        if self._watchlist:
            syms = self._watchlist.list_symbols(uid)
            if syms:
                settings["watchlist"] = syms
        if self._groups:
            groups = self._groups.list_groups(uid)
            if groups:
                settings["groups"] = groups

        return settings
