from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.errors import AuthorizationError


def make_require_team_member(ctx: Any, uid: Callable[[], int]) -> Callable[[int], None]:
    """Return a guard that ensures the current user belongs to ``team_id``."""

    def _require_team_member(team_id: int) -> None:
        collab = getattr(ctx, "collaboration_service", None)
        if collab is None:
            return
        user_ctx = collab.get_user_context(uid())
        team_ids = {
            int(t.get("id"))
            for t in (user_ctx.get("teams") or [])
            if t.get("id") is not None
        }
        if team_id not in team_ids:
            raise AuthorizationError("team_access_denied")

    return _require_team_member
