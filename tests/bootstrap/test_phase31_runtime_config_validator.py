"""Phase 31: profile-aware runtime config validation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.bootstrap_components.runtime_config_validator import (
    RuntimeConfigReport,
    resolve_deploy_profile,
    should_fail_fast_config,
    validate_runtime_config,
)


def _mysql_settings(**overrides):
    base = {
        "host": "127.0.0.1",
        "port": 3306,
        "user": "quant",
        "password": "secret",
        "database": "quant_atlas",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _settings(**overrides):
    defaults = {
        "use_mysql": False,
        "mysql": None,
        "database_uri": "sqlite:///tmp/test.db",
        "enable_celery": False,
        "celery_broker_url": "redis://192.168.8.103:6380/0",
        "tdx_root_path": None,
        "qmt": SimpleNamespace(enabled=False, qmt_path=None, account_id=None),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_resolve_deploy_profile_defaults_to_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEPLOY_PROFILE", raising=False)
    assert resolve_deploy_profile() == "dev"


def test_validate_runtime_config_warns_on_missing_qmt_path_in_dev() -> None:
    settings = _settings(
        qmt=SimpleNamespace(enabled=True, qmt_path=None, account_id="acc-1"),
    )
    report = validate_runtime_config(settings, strict=False, profile="dev")
    assert report.ok
    assert "qmt_path_required" in report.warnings


def test_validate_runtime_config_strict_raises_on_mysql_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRICT_BOOTSTRAP", "1")
    settings = _settings(
        use_mysql=True,
        mysql=_mysql_settings(),
        database_uri="not-a-valid-uri",
    )
    with pytest.raises(RuntimeError, match="Runtime configuration validation failed"):
        validate_runtime_config(settings, strict=True, profile="dev")


def test_validate_runtime_config_trading_profile_requires_qmt(
    tmp_path: Path,
) -> None:
    qmt_dir = tmp_path / "qmt"
    qmt_dir.mkdir()
    settings = _settings(
        qmt=SimpleNamespace(enabled=True, qmt_path=str(qmt_dir), account_id="acc-1"),
    )
    report = validate_runtime_config(settings, strict=False, profile="trading")
    assert report.ok

    bad = _settings(qmt=SimpleNamespace(enabled=False, qmt_path=None, account_id=None))
    with pytest.raises(RuntimeError, match="trading_profile_requires_qmt_account"):
        validate_runtime_config(bad, strict=False, profile="trading")


def test_should_fail_fast_config_for_prod_profile() -> None:
    assert should_fail_fast_config(strict=False, profile="prod") is True
    assert should_fail_fast_config(strict=False, profile="dev") is False


def test_validate_runtime_config_prod_ok_with_sqlite() -> None:
    report = validate_runtime_config(_settings(), strict=False, profile="prod")
    assert isinstance(report, RuntimeConfigReport)
    assert report.ok
