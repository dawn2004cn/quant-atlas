"""Unit tests for AuthService — authentication with password hashing."""
from __future__ import annotations

import unittest.mock as mock

import pytest

from app.modules.user.services.user.auth_service import AuthService


def _make_repo(**overrides):
    """Create a mock UserRepository with optional method overrides."""
    repo = mock.MagicMock()
    for attr, value in overrides.items():
        setattr(repo, attr, value)
    return repo


@pytest.fixture
def auth_service():
    repo = _make_repo()
    return AuthService(user_repository=repo)


class TestAuthenticate:
    """AuthService.authenticate flow."""

    def test_returns_none_when_user_not_found(self, auth_service):
        auth_service._repo.get_by_username.return_value = None
        result = auth_service.authenticate("nonexistent", "password")
        assert result is None
        auth_service._repo.get_by_username.assert_called_once_with("nonexistent")

    def test_returns_none_when_password_wrong(self, auth_service):
        fake_user = mock.MagicMock()
        fake_user.password_hash = "some_hash"
        auth_service._repo.get_by_username.return_value = fake_user
        with mock.patch.object(auth_service, "_check_password", return_value=False):
            result = auth_service.authenticate("user1", "wrong")
        assert result is None

    def test_returns_user_when_credentials_match(self, auth_service):
        fake_user = mock.MagicMock()
        fake_user.password_hash = "$q$1$abcdef"
        auth_service._repo.get_by_username.return_value = fake_user
        with mock.patch.object(auth_service, "_check_password", return_value=True):
            with mock.patch("app.modules.user.services.user.auth_service.needs_rehash", return_value=False):
                result = auth_service.authenticate("user1", "right")
        assert result is fake_user

    def test_rejects_legacy_sha256_hash_login(self, auth_service):
        fake_user = mock.MagicMock()
        fake_user.password_hash = hashlib_sha256_hex()
        auth_service._repo.get_by_username.return_value = fake_user
        result = auth_service.authenticate("user1", "password")
        assert result is None

    def test_does_not_upgrade_for_v1_hash(self, auth_service):
        fake_user = mock.MagicMock()
        fake_user.password_hash = "$q$1$abcdef"
        auth_service._repo.get_by_username.return_value = fake_user
        with mock.patch.object(auth_service, "_check_password", return_value=True):
            with mock.patch("app.modules.user.services.user.auth_service.needs_rehash", return_value=False) as nr:
                with mock.patch.object(auth_service, "_try_upgrade_password") as tp:
                    auth_service.authenticate("user1", "password")
                assert len(tp.call_args_list) == 0


def hashlib_sha256_hex():
    import hashlib
    return hashlib.sha256("dummy".encode()).hexdigest()


class TestRegister:
    """AuthService.register creates users with hashed passwords."""

    def test_register_calls_repo_create(self, auth_service):
        auth_service.register("newuser", "password123", "viewer")
        auth_service._repo.create.assert_called_once()
        call_args = auth_service._repo.create.call_args
        user_account = call_args[0][0]
        assert user_account.username == "newuser"
        assert user_account.role == "viewer"
        assert user_account.password_hash.startswith("$q$1$")

    def test_register_returns_true_on_success(self, auth_service):
        result = auth_service.register("newuser", "password123")
        assert result is True

    def test_register_returns_false_on_duplicate(self, auth_service):
        auth_service._repo.create.side_effect = ValueError("duplicate")
        result = auth_service.register("existing", "password123")
        assert result is False


class TestPasswordHashing:
    """Verify real PBKDF2 hash path (not mocked)."""

    def test_check_password_accepts_pbkdf2_hash(self, auth_service):
        from app.core.password_hash import hash_password, verify_password

        stored = hash_password("secret-pass")
        assert verify_password("secret-pass", stored)
        assert auth_service._check_password("secret-pass", stored)

