"""Unit tests for UserApplicationService — registration, change_password, role management."""
from __future__ import annotations

import unittest.mock as mock

import pytest

from app.modules.user.services.user.user_service import UserApplicationService


def _make_repo(**overrides):
    """Create a mock UserRepository with optional method overrides."""
    repo = mock.MagicMock()
    for attr, value in overrides.items():
        setattr(repo, attr, value)
    return repo


def _make_auth_service(**overrides):
    """Create a mock AuthService with optional method overrides."""
    svc = mock.MagicMock()
    for attr, value in overrides.items():
        setattr(svc, attr, value)
    return svc


@pytest.fixture
def user_service():
    repo = _make_repo()
    return UserApplicationService(repository=repo)


@pytest.fixture
def user_service_with_auth():
    repo = _make_repo()
    auth = _make_auth_service()
    return UserApplicationService(repository=repo, auth_service=auth)


class TestRegisterPublic:
    """UserApplicationService.register_public validation."""

    def test_rejects_short_username(self, user_service):
        ok, msg = user_service.register_public("a", "password123")
        assert ok is False
        assert "至少 2" in msg

    def test_rejects_protected_username(self, user_service):
        ok, msg = user_service.register_public("admin", "password123")
        assert ok is False
        assert "受保护" in msg

    def test_rejects_invalid_username_chars(self, user_service):
        ok, msg = user_service.register_public("user@name!", "password123")
        assert ok is False
        assert "只能包含" in msg

    def test_rejects_short_password(self, user_service):
        ok, msg = user_service.register_public("validuser", "12345")
        assert ok is False
        assert "至少 6" in msg

    def test_succeeds_with_valid_input(self, user_service):
        user_service.register_public("newuser", "password123")
        user_service._repository.create_user.assert_called_once_with(
            "newuser", "password123", "viewer"
        )

    def test_returns_false_on_duplicate(self, user_service):
        user_service._repository.create_user.side_effect = ValueError("duplicate")
        ok, msg = user_service.register_public("existing", "password123")
        assert ok is False
        assert "已存在" in msg


class TestChangePassword:
    """UserApplicationService.change_password."""

    def test_requires_new_password_min_8_chars(self, user_service_with_auth):
        ok, msg = user_service_with_auth.change_password(
            target_username="user1",
            old_password="old123",
            new_password="short",
            confirm_password="short",
            current_username="user1",
            current_role="viewer",
        )
        assert ok is False
        assert "至少 8" in msg

    def test_requires_passwords_match(self, user_service_with_auth):
        ok, msg = user_service_with_auth.change_password(
            target_username="user1",
            old_password="old123",
            new_password="newpassword123",
            confirm_password="different",
            current_username="user1",
            current_role="viewer",
        )
        assert ok is False
        assert "不一致" in msg

    def test_requires_old_password_for_regular_user(self, user_service_with_auth):
        user_service_with_auth._auth_service.authenticate.return_value = None
        ok, msg = user_service_with_auth.change_password(
            target_username="user1",
            old_password="wrong_password",
            new_password="newpassword123",
            confirm_password="newpassword123",
            current_username="user1",
            current_role="viewer",
        )
        assert ok is False
        assert "原密码不正确" in msg

    def test_admin_can_skip_old_password(self, user_service_with_auth):
        user_service_with_auth._repository.get_by_username.return_value = mock.MagicMock(user_id=42)
        user_service_with_auth._repository.update.return_value = True
        ok, msg = user_service_with_auth.change_password(
            target_username="user1",
            old_password="",
            new_password="newpassword123",
            confirm_password="newpassword123",
            current_username="admin1",
            current_role="admin",
        )
        assert ok is True
        assert "已更新" in msg

    def test_updates_password_hash(self, user_service_with_auth):
        fake_user = mock.MagicMock(user_id=42)
        user_service_with_auth._repository.get_by_username.return_value = fake_user
        user_service_with_auth._repository.update.return_value = True
        user_service_with_auth._auth_service.authenticate.return_value = fake_user

        ok, msg = user_service_with_auth.change_password(
            target_username="user1",
            old_password="old123",
            new_password="newpassword123",
            confirm_password="newpassword123",
            current_username="user1",
            current_role="viewer",
        )
        assert ok is True
        call_kwargs = user_service_with_auth._repository.update.call_args
        assert call_kwargs[0][1]["password"].startswith("$q$1$")

    def test_returns_false_when_user_not_found(self, user_service_with_auth):
        user_service_with_auth._repository.get_by_username.return_value = None
        ok, msg = user_service_with_auth.change_password(
            target_username="ghost",
            old_password="old123",
            new_password="newpassword123",
            confirm_password="newpassword123",
            current_username="admin1",
            current_role="admin",
        )
        assert ok is False
        assert "用户不存在" in msg

    def test_requires_auth_service(self, user_service):
        ok, msg = user_service.change_password(
            target_username="user1",
            old_password="old123",
            new_password="newpassword123",
            confirm_password="newpassword123",
            current_username="user1",
            current_role="viewer",
        )
        assert ok is False
        assert "未配置" in msg


class TestSetUserRole:
    """UserApplicationService.set_user_role."""

    def test_admin_can_change_role(self, user_service):
        user_service._repository.get_by_username.return_value = mock.MagicMock()
        user_service._repository.update_user_role.return_value = True
        ok, msg = user_service.set_user_role("user1", "editor", actor_role="admin")
        assert ok is True
        assert "已更新" in msg

    def test_non_admin_cannot_change_role(self, user_service):
        ok, msg = user_service.set_user_role("user1", "editor", actor_role="viewer")
        assert ok is False
        assert "仅管理员" in msg

    def test_returns_false_when_user_not_found(self, user_service):
        user_service._repository.get_by_username.return_value = None
        ok, msg = user_service.set_user_role("ghost", "editor", actor_role="admin")
        assert ok is False
        assert "用户不存在" in msg
