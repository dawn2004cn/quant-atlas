from __future__ import annotations

from typing import Any


class CollaborationService:
    """Service for team/collaboration operations backed by a repository."""

    def __init__(
        self,
        collaboration_repository: Any = None,
        repository: Any = None,
    ) -> None:
        self._repo = collaboration_repository or repository

    def create_team(self, user_id: int, name: str, slug: str | None = None) -> dict[str, Any]:
        """Create a new team and assign the creator as owner."""
        tenant = self._repo.ensure_personal_tenant(user_id)
        team_slug = slug or name.lower().replace(" ", "-")
        team = self._repo.create_team(tenant_id=tenant.id, slug=team_slug, name=name)
        self._repo.add_team_member(team_id=team.id, user_id=user_id, role="owner")
        return {
            "ok": True,
            "team": {"id": team.id, "slug": team.slug, "name": team.name},
        }

    def get_user_context(self, user_id: int) -> dict[str, Any]:
        """Return the user's tenant + team context."""
        tenant = self._repo.ensure_personal_tenant(user_id)
        teams = self._repo.list_user_teams(user_id)
        active_team_id = teams[0].id if teams else None
        return {
            "tenant": {"id": tenant.id, "slug": tenant.slug, "name": tenant.name, "plan": tenant.plan},
            "teams": [{"id": t.id, "slug": t.slug, "name": t.name} for t in teams],
            "active_team_id": active_team_id,
        }
