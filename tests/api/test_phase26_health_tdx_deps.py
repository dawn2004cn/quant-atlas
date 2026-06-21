"""Phase 26: health probe, TDX base deps, Celery beat hooks."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.modules.system.services.system.system_health_probe_service import SystemHealthProbeService
from app.presentation.api.route_deps import TdxBaseRouteDeps, require_tdx_base_read_service


def test_system_health_probe_mysql_skipped_without_mysql(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.use_mysql = False
    monkeypatch.setattr(
        "app.modules.system.services.system.system_health_probe_service.get_settings",
        lambda: settings,
    )
    result = SystemHealthProbeService.probe_mysql()
    assert result["status"] == "skipped"


def test_tdx_base_route_deps_require_service() -> None:
    svc = object()
    resolved = require_tdx_base_read_service(TdxBaseRouteDeps(tdx_base_read_service=svc))
    assert resolved is svc
