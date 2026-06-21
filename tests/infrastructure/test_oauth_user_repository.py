"""OAuth user provisioning tests (JsonUserRepository)."""

from __future__ import annotations

from app.infrastructure.repositories.common.json_repositories import JsonUserRepository


def test_link_or_create_oauth_user_creates_viewer(tmp_path):
    repo = JsonUserRepository(tmp_path / "users.json")
    user = repo.link_or_create_oauth_user("kc-sub-123", display_name="alice@example.com")
    assert user is not None
    assert user.username
    assert user.role == "viewer"

    again = repo.link_or_create_oauth_user("kc-sub-123", display_name="alice@example.com")
    assert again is not None
    assert again.user_id == user.user_id
    assert again.username == user.username
