"""Legacy ``backtest`` package alias for agent backtest tests and imports."""

from __future__ import annotations

import importlib
import pkgutil
import sys

_PKG_ROOT = "app.infrastructure.agent.backtest"


def _register_backtest_alias() -> None:
    if "backtest" in sys.modules:
        return
    root = importlib.import_module(_PKG_ROOT)
    sys.modules["backtest"] = root
    prefix = f"{_PKG_ROOT}."
    for modinfo in pkgutil.walk_packages(root.__path__, prefix):
        short_name = "backtest" + modinfo.name[len(_PKG_ROOT) :]
        if short_name not in sys.modules:
            sys.modules[short_name] = importlib.import_module(modinfo.name)


_register_backtest_alias()
