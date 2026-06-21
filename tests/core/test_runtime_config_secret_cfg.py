from __future__ import annotations

import os

from app.core import runtime_config


def _reset_runtime_config(monkeypatch):
    monkeypatch.setattr(runtime_config, "_loaded", False)
    monkeypatch.setattr(runtime_config, "_parser", None)
    runtime_config._SECRET_CFG_KEYS_LOADED.clear()


def test_secret_cfg_loads_before_dotenv_and_overrides_it(tmp_path, monkeypatch):
    secret_cfg = tmp_path / "secret.cfg"
    dotenv = tmp_path / ".env"
    cfg = tmp_path / "config.cfg"

    secret_cfg.write_text("MYSQL_PASSWORD=from-secret\nREDIS_URL=redis://secret-host:6379/0\n", encoding="utf-8")
    dotenv.write_text("MYSQL_PASSWORD=from-dotenv\nREDIS_URL=redis://dotenv-host:6379/0\n", encoding="utf-8")

    monkeypatch.delenv("MYSQL_PASSWORD", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr(runtime_config, "_SECRET_CFG_PATH", secret_cfg)
    monkeypatch.setattr(runtime_config, "_DOTENV_PATH", dotenv)
    monkeypatch.setattr(runtime_config, "_CFG_PATH", cfg)
    _reset_runtime_config(monkeypatch)

    assert runtime_config.get_runtime("MYSQL_PASSWORD") == "from-secret"
    assert runtime_config.get_runtime("REDIS_URL") == "redis://secret-host:6379/0"


def test_existing_environment_overrides_secret_cfg(tmp_path, monkeypatch):
    secret_cfg = tmp_path / "secret.cfg"
    dotenv = tmp_path / ".env"
    cfg = tmp_path / "config.cfg"

    secret_cfg.write_text("MYSQL_PASSWORD=from-secret\n", encoding="utf-8")
    dotenv.write_text("MYSQL_PASSWORD=from-dotenv\n", encoding="utf-8")

    monkeypatch.setenv("MYSQL_PASSWORD", "from-env")
    monkeypatch.setattr(runtime_config, "_SECRET_CFG_PATH", secret_cfg)
    monkeypatch.setattr(runtime_config, "_DOTENV_PATH", dotenv)
    monkeypatch.setattr(runtime_config, "_CFG_PATH", cfg)
    _reset_runtime_config(monkeypatch)

    assert runtime_config.get_runtime("MYSQL_PASSWORD") == "from-env"


def test_secret_cfg_fills_empty_placeholder_from_prior_dotenv(tmp_path, monkeypatch):
    """Simulates run.py load_dotenv() leaving MYSQL_PASSWORD='' before secret.cfg."""
    secret_cfg = tmp_path / "secret.cfg"
    dotenv = tmp_path / ".env"
    cfg = tmp_path / "config.cfg"

    secret_cfg.write_text("MYSQL_PASSWORD=from-secret\n", encoding="utf-8")
    dotenv.write_text("MYSQL_PASSWORD=\n", encoding="utf-8")

    monkeypatch.delenv("MYSQL_PASSWORD", raising=False)
    monkeypatch.setenv("MYSQL_PASSWORD", "")
    monkeypatch.setattr(runtime_config, "_SECRET_CFG_PATH", secret_cfg)
    monkeypatch.setattr(runtime_config, "_DOTENV_PATH", dotenv)
    monkeypatch.setattr(runtime_config, "_CFG_PATH", cfg)
    _reset_runtime_config(monkeypatch)

    runtime_config._load_dotenv_if_present()

    assert runtime_config.get_runtime("MYSQL_PASSWORD") == "from-secret"
