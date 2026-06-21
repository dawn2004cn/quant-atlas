from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.modules.user.services.user.user_lifecycle_service import UserLifecycleService
from app.domain.entities import Tenant


def _make_svc(tmp_path: Path, collab: MagicMock | None = None) -> UserLifecycleService:
    deps = {k: MagicMock() for k in (
        "access", "profile", "pages", "audit", "watchlist", "groups"
    )}
    deps["access"].snapshot_for_user.return_value = {}
    deps["profile"].get_profile.return_value = {}
    deps["pages"].get_preferences.return_value = {}
    deps["audit"].list_user_actions.return_value = []
    deps["watchlist"].list_symbols.return_value = []
    deps["groups"].list_groups.return_value = []
    return UserLifecycleService(
        store_path=tmp_path / "lifecycle.json",
        access_policy_service=deps["access"],
        investment_profile_service=deps["profile"],
        page_preference_service=deps["pages"],
        audit_trail_service=deps["audit"],
        watchlist_service=deps["watchlist"],
        stock_group_service=deps["groups"],
        collaboration_repository=collab,
    )


def test_lifecycle_uses_sql_when_collab_available(tmp_path: Path) -> None:
    collab = MagicMock()
    collab.ensure_personal_tenant.return_value = Tenant(id=9, slug="personal-u3", name="P", plan="personal")
    collab.get_lifecycle_row.return_value = {
        "notifications": {"site_message": False},
        "privacy_consent": {},
        "deletion_request": None,
    }
    svc = _make_svc(tmp_path, collab)
    user = MagicMock(id=3)
    settings = svc.get_settings(user=user)
    assert settings["tenant_id"] == 9
    assert settings["sync_status"]["mode"] == "sql_tenant"
    assert settings["notifications"]["site_message"] is False
