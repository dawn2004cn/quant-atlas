from __future__ import annotations

import logging

from app.core.logging_config import (
    SQL_LOGGER_NAME,
    configure_third_party_loggers,
    resolve_logging_settings,
)


def test_resolve_logging_settings_defaults(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("LOG_SQL", raising=False)
    monkeypatch.delenv("LOG_SQL_LEVEL", raising=False)
    monkeypatch.delenv("LOG_STRUCTURED", raising=False)

    settings = resolve_logging_settings()

    assert settings.level == logging.INFO
    assert settings.sql_level == logging.WARNING
    assert settings.structured is False
    assert settings.enable_sql_trace is False


def test_resolve_logging_settings_sql_enabled(monkeypatch):
    monkeypatch.setenv("LOG_SQL", "1")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_SQL_LEVEL", "DEBUG")

    settings = resolve_logging_settings()

    assert settings.level == logging.DEBUG
    assert settings.sql_level == logging.DEBUG
    assert settings.enable_sql_trace is True


def test_configure_third_party_loggers_sql_channel(monkeypatch):
    monkeypatch.setenv("LOG_SQL", "1")
    monkeypatch.setenv("LOG_SQL_LEVEL", "INFO")

    settings = resolve_logging_settings()
    configure_third_party_loggers(settings)

    assert logging.getLogger(SQL_LOGGER_NAME).level == logging.INFO
    assert logging.getLogger("sqlalchemy.engine").level == logging.INFO


def test_werkzeug_defaults_to_info_when_app_level_debug(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.delenv("LOG_WERKZEUG_LEVEL", raising=False)

    settings = resolve_logging_settings()

    assert settings.werkzeug_level == logging.INFO


def test_console_colors_forced_on(monkeypatch):
    monkeypatch.setenv("LOG_COLORS", "1")

    settings = resolve_logging_settings()

    assert settings.console_colors is True


def test_console_colors_disabled_for_structured(monkeypatch):
    monkeypatch.setenv("LOG_COLORS", "1")
    monkeypatch.setenv("LOG_STRUCTURED", "1")

    settings = resolve_logging_settings()

    assert settings.console_colors is False


def test_human_readable_formatter_colors_level():
    from app.core.logger import HumanReadableFormatter

    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    line = HumanReadableFormatter(use_colors=True).format(record)

    assert "\033[33m[WARNING]\033[0m" in line


def test_reassert_logging_after_clobber(monkeypatch, tmp_path):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "app.log"))

    from app.core.logger import setup_logging

    setup_logging()
    root = logging.getLogger()
    assert len(root.handlers) == 2
    assert root.level == logging.DEBUG

    root.handlers.clear()
    root.setLevel(logging.WARNING)
    root.addHandler(logging.StreamHandler())
    assert len(root.handlers) == 1
    assert root.level == logging.WARNING

    setup_logging()
    assert len(root.handlers) == 2
    assert root.level == logging.DEBUG


def test_create_watchlist_repository_preserves_logging(monkeypatch):
    """Regression: alembic fileConfig during schema bootstrap must not stick at WARNING."""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    from app.core.runtime_config import _load_dotenv_if_present

    _load_dotenv_if_present()
    from app.core.logger import setup_logging

    setup_logging()
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 2

    from app.config import get_settings
    from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure

    bind_application_infrastructure(get_settings())
    from app.infrastructure.database.db_manager import get_db_manager
    from app.infrastructure.repositories.common.deps import create_watchlist_repository

    settings = get_settings()
    sf = get_db_manager().get_session_factory(settings.mysql)
    create_watchlist_repository(settings, session_factory=sf)

    assert root.level == logging.DEBUG
    assert len(root.handlers) == 2
