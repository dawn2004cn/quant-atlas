from __future__ import annotations

from app.config import (
    AppSettings,
    get_settings,
    reset_settings,
)
from app.config.slices import QmtExecutionSettings, ThsProviderSettings


def test_get_settings_returns_singleton():
    reset_settings()
    a = get_settings()
    b = get_settings()
    assert a is b


def test_app_settings_slices():
    reset_settings()
    s = AppSettings.from_env()
    assert isinstance(s.qmt, QmtExecutionSettings)
    assert isinstance(s.ths, ThsProviderSettings)
    assert s.data_backend.database_uri == s.database_uri
