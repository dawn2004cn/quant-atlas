from __future__ import annotations

import configparser

import pytest

import app.core.runtime_config as runtime_config


@pytest.fixture(autouse=True)
def _reset_runtime_config_state(monkeypatch):
    """Isolate module-level parser state between tests."""
    monkeypatch.setattr(runtime_config, "_loaded", False, raising=False)
    monkeypatch.setattr(runtime_config, "_parser", None, raising=False)


def test_get_runtime_reads_env_after_dotenv_load(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)

    def _inject_dotenv() -> None:
        runtime_config._loaded = True
        import os

        os.environ["REDIS_URL"] = "redis://192.168.8.103:6380/0"

    monkeypatch.setattr(runtime_config, "_ensure_loaded", _inject_dotenv)

    assert runtime_config.get_runtime("REDIS_URL", "") == "redis://192.168.8.103:6380/0"


def test_resolved_redis_url_prefers_redis_url(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://192.168.8.103:6380/0")
    monkeypatch.setenv("TASK_MESSAGE_REDIS_URL", "redis://other:6379/1")
    runtime_config._loaded = True

    assert runtime_config.resolved_redis_url() == "redis://192.168.8.103:6380/0"


def test_resolved_redis_url_falls_back_to_task_message(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("TASK_MESSAGE_REDIS_URL", "redis://192.168.8.103:6380/0")
    runtime_config._loaded = True

    assert runtime_config.resolved_redis_url() == "redis://192.168.8.103:6380/0"


def test_get_runtime_uses_config_cfg_when_env_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("REDIS_URL", raising=False)
    cfg = tmp_path / "config.cfg"
    cfg.write_text("[app]\nREDIS_URL = redis://cfg-host:6379/2\n", encoding="utf-8")
    monkeypatch.setattr(runtime_config, "_CFG_PATH", cfg)
    monkeypatch.setattr(runtime_config, "_DOTENV_PATH", tmp_path / "missing.env")
    runtime_config._loaded = False
    runtime_config._parser = None

    assert runtime_config.get_runtime("REDIS_URL", "") == "redis://cfg-host:6379/2"
