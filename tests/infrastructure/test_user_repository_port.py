"""UserRepository port compliance tests."""

from __future__ import annotations

import hashlib

from app.domain.entities import UserAccount
from app.domain.ports.repository_ports import UserRepository
from app.infrastructure.repositories.json_repositories import JsonUserRepository
from app.infrastructure.repositories.mysql_repositories import MySQLUserRepository
from app.infrastructure.repositories.user_mapper import user_row_to_account


def test_mysql_user_repository_implements_port():
    assert issubclass(MySQLUserRepository, UserRepository)


def test_user_row_to_account_mapping():
    account = user_row_to_account(
        user_id=7,
        username="alice",
        role="viewer",
        password_hash="abc",
        avatar_url="/a.png",
    )
    assert account.user_id == 7
    assert account.username == "alice"
    assert account.role == "viewer"
    assert account.avatar_url == "/a.png"


def test_json_user_repository_crud_returns_user_account(tmp_path):
    repo = JsonUserRepository(tmp_path / "users.json")
    password_hash = hashlib.sha256(b"secret123").hexdigest()
    user_id = repo.create(
        UserAccount(
            user_id=0,
            username="bob",
            role="viewer",
            password_hash=password_hash,
        )
    )
    assert str(user_id).isdigit()
    loaded = repo.get_by_id(user_id)
    assert isinstance(loaded, UserAccount)
    assert loaded.username == "bob"
    assert loaded in repo.list_all(limit=20)
    assert repo.update(user_id, {"role": "trader"}) is True
    assert repo.get_by_id(user_id).role == "trader"
    assert repo.delete(user_id) is True
    assert repo.get_by_id(user_id) is None
