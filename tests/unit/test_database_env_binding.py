from __future__ import annotations

from app.config import get_settings, reset_settings
from app.config.database_settings import DatabaseBackend
from app.presentation.web.page_shell import ux_env_hints


def test_env_file_binds_mysql_and_tdx(monkeypatch) -> None:
    """Nested DatabaseConfig/TdxConfig must read flat .env keys."""
    monkeypatch.delenv("DATABASE_BACKEND", raising=False)
    monkeypatch.delenv("MYSQL_HOST", raising=False)
    monkeypatch.delenv("TDX_ROOT_PATH", raising=False)
    reset_settings()

    settings = get_settings()

    assert settings.database_backend == DatabaseBackend.MYSQL
    assert settings.use_mysql is True
    assert settings.database.mysql_host == "192.168.8.103"
    assert settings.tdx_root_path == r"E:\tdx\通达信金融终端(开心果交易版)V2024.02"

    hints = ux_env_hints(settings)
    titles = [h["title"] for h in hints]
    assert not any("MySQL" in t for t in titles)
    assert not any("通达信" in t for t in titles)
