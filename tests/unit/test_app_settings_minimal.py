"""Minimal AppSettings instantiation without .env (replaces tests/test_config_minimal.py)."""

from __future__ import annotations

from pydantic_settings import SettingsConfigDict

from app.config.settings import AppSettings


def test_settings_instantiate_without_env_file():
    class IsolatedSettings(AppSettings):
        model_config = SettingsConfigDict(
            env_prefix="",
            populate_by_name=True,
            extra="ignore",
            env_file=None,
        )

    settings = IsolatedSettings()
    assert settings.database is not None
    assert isinstance(settings.debug, bool)
