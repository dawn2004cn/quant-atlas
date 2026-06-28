"""Wiring helpers — dependency injection binding layer.

DEPRECATED: These files implement the legacy bind/get DI pattern.
They will be removed when the ServiceRegistry (Phase 2) is fully migrated.

Migration path:
  1. Replace from app.modules.system.services.helpers.timescale_bar_wiring import get_foo()
     with dependency injection via the application service constructor.
  2. Remove the bind_foo() call from bootstrap_components/infrastructure_binding.py.
  3. Delete this file once all callers are migrated.
"""

from __future__ import annotations

import warnings

from app.domain.ports.timescale_bar_port import TimescaleBarPort

# One-time deprecation warning per module load
warnings.warn(
    'app.modules.system.services.helpers.timescale_bar_wiring is deprecated. '
    'Migrate to ServiceRegistry (Phase 2). This module will be removed.',
    DeprecationWarning,
    stacklevel=2,
)


_bar_repo: TimescaleBarPort | None = None
_port_ready = False


def bind_timescale_bar_port(port: TimescaleBarPort | None) -> None:
    global _bar_repo
    _bar_repo = port


def get_timescale_bar_port() -> TimescaleBarPort | None:
    return _bar_repo


def ensure_timescale_bar_port() -> None:
    """CLI/Celery 未走 Flask bootstrap 时惰性绑定 Timescale 写入端口。"""
    global _port_ready
    if _port_ready:
        return
    from app.config import get_settings
    from app.infrastructure.repositories.deps import create_timescale_bar_repository
    from app.infrastructure.repositories.postgres.postgres_timescale_bar_repository import (
        NullPostgresTimescaleBarRepository,
        PostgresTimescaleBarRepository,
    )

    settings = get_settings()
    if not settings.use_timescaledb:
        _port_ready = True
        return
    existing = get_timescale_bar_port()
    if isinstance(existing, PostgresTimescaleBarRepository):
        _port_ready = True
        return
    if existing is not None and isinstance(existing, NullPostgresTimescaleBarRepository):
        raise RuntimeError(
            "USE_TIMESCALEDB=1 但 PostgreSQL/Timescale 未配置，请检查 TIMESCALEDB_* / POSTGRES_*"
        )
    port = create_timescale_bar_repository(settings)
    if isinstance(port, NullPostgresTimescaleBarRepository):
        raise RuntimeError(
            "USE_TIMESCALEDB=1 但无法创建 Timescale 仓库，请检查 TIMESCALEDB_* / POSTGRES_*"
        )
    bind_timescale_bar_port(port)
    _port_ready = True
