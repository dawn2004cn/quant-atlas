"""Strategy sandbox mode resolution tests."""

import pytest

from app.infrastructure.sandbox.strategy_docker_runner import (
    StrategySandboxError,
    resolve_sandbox_mode,
)


def test_resolve_sandbox_mode_default_process(monkeypatch):
    monkeypatch.delenv("STRATEGY_SANDBOX", raising=False)
    assert resolve_sandbox_mode() == "process"


def test_resolve_sandbox_mode_docker(monkeypatch):
    monkeypatch.setenv("STRATEGY_SANDBOX", "docker")
    assert resolve_sandbox_mode() == "docker"


def test_resolve_sandbox_mode_invalid(monkeypatch):
    monkeypatch.setenv("STRATEGY_SANDBOX", "unsafe")
    with pytest.raises(StrategySandboxError):
        resolve_sandbox_mode()
