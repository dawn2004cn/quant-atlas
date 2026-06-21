from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.config as app_config
from app.infrastructure.repositories.mysql import mysql_tdx_dayk_repository as repo_mod
from app.infrastructure.repositories.mysql.mysql_tdx_dayk_repository import MySQLTdxDaykRepository


class _FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None


class _FakeConn:
    def __init__(self, rows):
        self.cursor_obj = _FakeCursor(rows)
        self.committed = 0
        self.rolled_back = 0
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def close(self):
        self.closed = True


class _FakePort:
    def __init__(self, rows):
        self.rows = list(rows)
        self.connections = []
        self._mysql = object()

    def connect(self, autocommit=False):
        conn = _FakeConn(self.rows.pop(0))
        self.connections.append(conn)
        return conn

    def commit(self, conn):
        conn.commit()

    def rollback(self, conn):
        conn.rollback()

    def close(self, conn):
        conn.close()


def _repo_with_rows(rows):
    repo = MySQLTdxDaykRepository.__new__(MySQLTdxDaykRepository)
    repo._conn_port = _FakePort(rows)
    return repo


def test_truncate_history_tables_acquires_and_releases_lock(monkeypatch):
    monkeypatch.setenv("ALLOW_HISTORY_TRUNCATE", "1")
    admin_calls = []
    monkeypatch.setattr("app.infrastructure.database.mysql_client.mysql_admin_execute", lambda _ms, sql: admin_calls.append(sql))
    repo = _repo_with_rows([(1,), (1,)])

    repo.truncate_history_tables()

    executed = [sql for sql, _params in repo._conn_port.connections[0].cursor_obj.executed]
    assert executed[0] == "SELECT GET_LOCK(%s, %s)"
    assert any(sql.startswith("TRUNCATE TABLE stock_history_sh") for sql in admin_calls)
    assert any(sql.startswith("TRUNCATE TABLE stock_history_sz") for sql in admin_calls)
    assert any(sql.startswith("TRUNCATE TABLE stock_history_bj") for sql in admin_calls)
    assert executed[-1] == "SELECT RELEASE_LOCK(%s)"


def test_truncate_history_tables_raises_when_lock_unavailable(monkeypatch):
    monkeypatch.setenv("ALLOW_HISTORY_TRUNCATE", "1")
    monkeypatch.setattr("app.infrastructure.database.mysql_client.mysql_admin_execute", lambda _ms, sql: admin_calls.append(sql))
    repo = _repo_with_rows([(0,)])

    with pytest.raises(RuntimeError, match="mysql_lock_not_acquired"):
        repo.truncate_history_tables()

    executed = [sql for sql, _params in repo._conn_port.connections[0].cursor_obj.executed]
    assert executed == ["SELECT GET_LOCK(%s, %s)"]
    assert repo._conn_port.connections[0].closed


class _SwapPort:
    def __init__(self, lock_conn, ddl_conn):
        self.lock_conn = lock_conn
        self.ddl_conn = ddl_conn
        self.calls = 0
        self.committed = []
        self.rolled_back = []
        self.closed = []

    def connect(self, autocommit=False):
        self.calls += 1
        return self.lock_conn if self.calls == 1 else self.ddl_conn

    def commit(self, conn):
        self.committed.append(conn)

    def rollback(self, conn):
        self.rolled_back.append(conn)

    def close(self, conn):
        self.closed.append(conn)


def test_truncate_history_tables_requires_explicit_reset_flag(monkeypatch):
    monkeypatch.delenv("ALLOW_HISTORY_TRUNCATE", raising=False)
    repo = _repo_with_rows([(1,), (1,)])

    with pytest.raises(RuntimeError, match="ddl_reset_requires_explicit_flag"):
        repo.truncate_history_tables()

    assert repo._conn_port.connections == []


def test_swap_reload_tables_uses_same_connection_for_lock_and_rename(monkeypatch):
    monkeypatch.setenv("ALLOW_HISTORY_TRUNCATE", "1")
    lock_rows = [(1,), (1,)]
    ddl_rows = []
    lock_conn = _FakeConn(lock_rows)
    ddl_conn = _FakeConn(ddl_rows)
    fake_port = _SwapPort(lock_conn, ddl_conn)
    fake_port.calls = 1
    settings = SimpleNamespace(mysql=object())

    monkeypatch.setattr(app_config, "get_settings", lambda: settings)
    monkeypatch.setattr(repo_mod, "MySQLConnectionAdapter", lambda mysql: fake_port)
    monkeypatch.setattr(repo_mod, "_acquire_mysql_lock", lambda conn_port, name, timeout=10: lock_conn)
    released = []
    monkeypatch.setattr(repo_mod, "_release_mysql_lock", lambda conn_port, conn, name: released.append((conn, name)))

    repo_mod.MySQLTdxDaykRepository.swap_reload_tables()

    ddl_sql = [sql for sql, _params in ddl_conn.cursor_obj.executed]
    assert ddl_sql[0].startswith("RENAME TABLE ")
    assert released == [(lock_conn, "quant_atlas_tdx_swap_history")]
    assert ddl_conn.closed is True
