from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.user.services.user.collaboration_service import CollaborationService
from app.domain.entities import Team, Tenant


def test_create_team_assigns_owner() -> None:
    repo = MagicMock()
    repo.ensure_personal_tenant.return_value = Tenant(id=1, slug="personal-u1", name="个人", plan="personal")
    repo.create_team.return_value = Team(id=10, tenant_id=1, slug="alpha-desk", name="Alpha Desk")
    repo.add_team_member.return_value = MagicMock()
    svc = CollaborationService(collaboration_repository=repo)
    out = svc.create_team(user_id=1, name="Alpha Desk")
    assert out["ok"] is True
    assert out["team"]["slug"] == "alpha-desk"
    repo.add_team_member.assert_called_once_with(team_id=10, user_id=1, role="owner")


def test_user_context_includes_tenant() -> None:
    repo = MagicMock()
    repo.ensure_personal_tenant.return_value = Tenant(id=2, slug="personal-u5", name="个人", plan="personal")
    repo.list_user_teams.return_value = []
    svc = CollaborationService(collaboration_repository=repo)
    ctx = svc.get_user_context(5)
    assert ctx["tenant"]["id"] == 2
    assert ctx["active_team_id"] is None
