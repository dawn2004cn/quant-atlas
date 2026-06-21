"""Schema bootstrap (Alembic vs create_all) tests."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from app.infrastructure.database.schema_bootstrap import (
    alembic_enabled,
    bootstrap_schema,
    run_alembic_upgrade_head,
)


def test_alembic_enabled_by_default(monkeypatch):
    monkeypatch.delenv("DB_SCHEMA_CREATE_ALL", raising=False)
    assert alembic_enabled() is True


def test_alembic_disabled_when_create_all_flag_set(monkeypatch):
    monkeypatch.setenv("DB_SCHEMA_CREATE_ALL", "1")
    assert alembic_enabled() is False


def test_bootstrap_sqlite_uses_create_all():
    engine = MagicMock()
    engine.dialect.name = "sqlite"
    fake_models = MagicMock()
    with patch("app.infrastructure.database.orm.Base") as base:
        with patch.dict(sys.modules, {"app.infrastructure.database.models": fake_models}):
            bootstrap_schema(engine)
    base.metadata.create_all.assert_called_once_with(bind=engine)


def test_bootstrap_mysql_runs_alembic(monkeypatch):
    monkeypatch.delenv("DB_SCHEMA_CREATE_ALL", raising=False)
    engine = MagicMock()
    engine.dialect.name = "mysql"
    fake_models = MagicMock()
    with patch("app.infrastructure.database.schema_bootstrap.run_alembic_upgrade_head") as upgrade:
        with patch.dict(sys.modules, {"app.infrastructure.database.models": fake_models}):
            bootstrap_schema(engine)
    upgrade.assert_called_once()


def test_run_alembic_upgrade_head_invokes_command(tmp_path):
    ini = tmp_path / "alembic.ini"
    ini.write_text("[alembic]\nscript_location = alembic\n", encoding="utf-8")
    with patch("app.infrastructure.database.schema_bootstrap.command.upgrade") as upgrade:
        run_alembic_upgrade_head(ini_path=ini)
    upgrade.assert_called_once()
