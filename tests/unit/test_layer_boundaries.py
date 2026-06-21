"""Architecture layer boundary tests."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT = ROOT / "app" / "application"

# ORM models belong in infrastructure repositories, not application services.
FORBIDDEN_IMPORT_MARKERS = (
    "infrastructure.database.models",
    "infrastructure.database.db_manager",
    "infrastructure.database.stock_cache_db",
    "infrastructure.database.mysql_client",
    "infrastructure.database.mappers",
    "infrastructure.repositories.mysql.mysql_tdx_gpcw_repository",
    "infrastructure.repositories.basic_market_data_repository",
    "infrastructure.repositories.news_archive_repository",
    "infrastructure.repositories.signal_flag_pool_repository",
    "infrastructure.repositories.investment_manager_repository",
    "infrastructure.repositories.moments_repository",
    "infrastructure.repositories.analysis_report_repository",
    "infrastructure.repositories.mysql.mysql_signal_observation_repository",
    "infrastructure.repositories.deps",
    "infrastructure.mappers.symbol_normalizer",
    "infrastructure.providers.market_data",
    "infrastructure.tdx_local",
    "infrastructure.pytdx",
    "infrastructure.providers.tdx_file_adapter",
    "infrastructure.providers",
    "infrastructure.cache.quote_cache",
    "infrastructure.mappers.longhu_mapper",
    "infrastructure.parsers.eastmoney_parser",
    "infrastructure.agent.data.quality_checker",
    "infrastructure.adapters.market_ingestion.longhu_adapter",
    "infrastructure.config_loader.loader",
    "infrastructure.qlib",
    "infrastructure.rdagent",
    "infrastructure.trading.pre_trade_validator",
    "infrastructure.risk.risk_gateway",
    "infrastructure.di.container",
    "infrastructure.external.tdx_finance",
    "infrastructure.execution",
    "infrastructure.tracing",
    "infrastructure.agent",
    "infrastructure.events",
    "infrastructure.messaging",
    "infrastructure.task_pipeline",
    "infrastructure.memory",
    "infrastructure.portfolio",
    "infrastructure.strategy",
    "infrastructure.data_quality",
    "infrastructure.adapters",
)


def _iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _read_source(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    if b"\x00" in raw[:200]:
        return raw.decode("utf-16-le")
    return raw.decode("utf-8")


def _collect_import_violations(path: Path, markers: tuple[str, ...] | None = None) -> list[str]:
    forbidden = markers or FORBIDDEN_IMPORT_MARKERS
    source = _read_source(path)
    tree = ast.parse(source, filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for marker in forbidden:
                    if marker in alias.name:
                        violations.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for marker in forbidden:
                if marker in module:
                    violations.append(f"from {module} import ...")
    return violations


FORBIDDEN_BEHAVIOR_MARKERS = (
    "conn.commit(",
    "conn.rollback(",
    "._session_factory(",
)


def _collect_behavior_violations(path: Path) -> list[str]:
    source = _read_source(path)
    violations: list[str] = []
    for marker in FORBIDDEN_BEHAVIOR_MARKERS:
        if marker in source:
            violations.append(f"uses {marker!r}")
    return violations


def test_application_does_not_import_infrastructure_orm_models():
    offenders: list[str] = []
    for path in _iter_py_files(APPLICATION_ROOT):
        for msg in _collect_import_violations(path):
            rel = path.relative_to(ROOT)
            offenders.append(f"{rel}: {msg}")
    assert not offenders, (
        "application layer must not import infrastructure.database.models "
        "(use domain ports / repositories instead):\n" + "\n".join(offenders)
    )


def test_application_does_not_commit_or_touch_session_factory():
    offenders: list[str] = []
    for path in _iter_py_files(APPLICATION_ROOT):
        for msg in _collect_behavior_violations(path):
            rel = path.relative_to(ROOT)
            offenders.append(f"{rel}: {msg}")
    assert not offenders, (
        "application layer must not call conn.commit/rollback or repo._session_factory "
        "(use mysql_access or repository methods instead):\n" + "\n".join(offenders)
    )


PRESENTATION_REFACTORED_ROUTE_CHECKS: tuple[tuple[Path, tuple[str, ...]], ...] = (
    (
        ROOT / "app" / "presentation" / "api" / "routes_v1_data_optimizer.py",
        ("infrastructure.providers", "infrastructure.tdx_local"),
    ),
    (
        ROOT / "app" / "presentation" / "api" / "routes_v1_hot_sectors.py",
        ("infrastructure.repositories.deps", "infrastructure.providers"),
    ),
    (
        ROOT / "app" / "presentation" / "api" / "routes_v1_tdx_base.py",
        (
            "infrastructure.database.mysql_client",
            "infrastructure.mappers.symbol_normalizer",
        ),
    ),
    (
        ROOT / "app" / "presentation" / "api" / "routes_v1_health.py",
        (
            "infrastructure.database.mysql_client",
            "infrastructure.task_queue",
        ),
    ),
    (
        ROOT / "app" / "presentation" / "api" / "legacy_routes.py",
        ("infrastructure.providers",),
    ),
    (
        ROOT / "app" / "presentation" / "api" / "routes_v1_task_ops.py",
        ("infrastructure.adapters",),
    ),
    (
        ROOT / "app" / "presentation" / "api" / "routes_v1_memory.py",
        ("infrastructure.memory",),
    ),
    (
        ROOT / "app" / "presentation" / "api" / "routes_v1_monitoring.py",
        ("infrastructure.monitoring",),
    ),
    (
        ROOT / "app" / "presentation" / "api" / "routes_metrics.py",
        ("infrastructure.metrics",),
    ),
)


def test_refactored_presentation_routes_do_not_import_infrastructure_providers():
    offenders: list[str] = []
    for path, markers in PRESENTATION_REFACTORED_ROUTE_CHECKS:
        if not path.is_file():
            offenders.append(f"{path.relative_to(ROOT)}: missing file")
            continue
        for msg in _collect_import_violations(path, markers):
            rel = path.relative_to(ROOT)
            offenders.append(f"{rel}: {msg}")
    assert not offenders, (
        "refactored presentation routes must not import forbidden infrastructure modules "
        "(use application helpers / bootstrap services instead):\n" + "\n".join(offenders)
    )
