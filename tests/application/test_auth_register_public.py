"""开放注册默认 viewer、管理员改角色。"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.application.services.user_service import UserApplicationService


def test_register_public_creates_viewer() -> None:
    repo = MagicMock()
    repo.get_by_username.return_value = None
    repo.create_user.return_value = True
    svc = UserApplicationService(repo)
    ok, msg = svc.register_public("newuser", "secret12")
    assert ok
    repo.create_user.assert_called_once_with("newuser", "secret12", "viewer")


def test_register_rejects_reserved_username() -> None:
    repo = MagicMock()
    svc = UserApplicationService(repo)
    ok, _msg = svc.register_public("admin", "secret12")
    assert not ok
    repo.create_user.assert_not_called()


def test_set_user_role_requires_admin() -> None:
    repo = MagicMock()
    repo.get_by_username.return_value = MagicMock()
    repo.update_user_role.return_value = True
    svc = UserApplicationService(repo)
    ok, msg = svc.set_user_role("bob", "trader", actor_role="viewer")
    assert not ok
    assert "管理员" in msg
    repo.update_user_role.assert_not_called()

    ok2, _msg2 = svc.set_user_role("bob", "trader", actor_role="admin")
    assert ok2
    repo.update_user_role.assert_called_once_with("bob", "trader")
