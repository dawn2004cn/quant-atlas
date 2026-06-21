"""Tests verifying the TimeSeriesDBPort DIP is clean.

After the Phase 3 refactor:
  - Pure port interface lives in ``domain.ports.timeseries_port`` (no infra)
  - Concrete adapters live in ``infrastructure.timeseries.adapters``
  - ``timeseries_ports.py`` (the backward-compat re-export) was removed
    because it violated DIP by importing concrete infrastructure classes
    into the domain layer.  Importers should use the pure port from
    ``timeseries_port`` and the adapters directly from infrastructure.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest


class TestTimeSeriesPortDIP:
    """Verify that domain.ports.timeseries_port has NO infrastructure imports."""

    def test_timeseries_port_has_no_infrastructure_import(self):
        """The pure port file must not contain any ``from app.infrastructure``."""
        port_file = Path(__file__).resolve().parent.parent.parent.parent / \
            "app" / "domain" / "ports" / "timeseries_port.py"
        source = port_file.read_text(encoding="utf-8")
        tree = ast.parse(source)

        infra_imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.ImportFrom, ast.Import)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("app.infrastructure"):
                        infra_imports.append(f"from {node.module} import ...")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("app.infrastructure"):
                            infra_imports.append(f"import {alias.name}")

        assert infra_imports == [], (
            f"Domain port file has infrastructure imports (DIP violation): "
            f"{infra_imports}"
        )

    def test_pure_port_can_import_without_hanging(self):
        """Importing the pure port must not hang or trigger agent loading."""
        # Remove from cache if previously loaded
        for mod in list(sys.modules.keys()):
            if "app.domain.ports.timeseries_port" in mod:
                del sys.modules[mod]

        mod = importlib.import_module("app.domain.ports.timeseries_port")
        assert mod.TimeSeriesDBPort is not None
        assert mod.TimeSeriesPoint is not None

    def test_backward_compat_module_removed(self):
        """The DIP-violating timeseries_ports.py is intentionally removed.

        It re-exported concrete infrastructure adapters (ClickHouseAdapter,
        QuestDBAdapter, InMemoryTimeSeriesDB) from the domain layer, which
        violated the Dependency Inversion Principle.  Consumers should import
        the pure port from ``timeseries_port`` and adapters from
        ``infrastructure.timeseries.adapters`` directly.
        """
        # Fresh import attempt — must fail
        for mod in list(sys.modules.keys()):
            if "app.domain.ports.timeseries_ports" in mod:
                del sys.modules[mod]

        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("app.domain.ports.timeseries_ports")

    def test_port_is_abstract(self):
        """TimeSeriesDBPort must be an abstract base class."""
        from app.domain.ports.timeseries_port import TimeSeriesDBPort

        assert hasattr(TimeSeriesDBPort, "__abstractmethods__")
        # All 5 methods must be abstract
        assert len(TimeSeriesDBPort.__abstractmethods__) == 5

    def test_in_memory_implements_port(self):
        """InMemoryTimeSeriesDB from infrastructure must satisfy the port."""
        from app.domain.ports.timeseries_port import TimeSeriesDBPort
        from app.infrastructure.timeseries.adapters import InMemoryTimeSeriesDB

        db = InMemoryTimeSeriesDB()
        assert isinstance(db, TimeSeriesDBPort)
        assert db.connect() is True
        assert db.query_ohlcv("600519", "D", "2024-01-01", "2024-01-31") == []
