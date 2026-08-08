"""Unit tests for QuestDB OHLCV SYMBOL migration helper."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
MOD_PATH = ROOT / "scripts" / "migrations" / "questdb_ohlcv_symbol_index.py"


def _load_mig():
    spec = importlib.util.spec_from_file_location("questdb_ohlcv_symbol_index", MOD_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migrate_skipped_when_questdb_not_configured(monkeypatch) -> None:
    mig = _load_mig()
    monkeypatch.setattr(mig, "load_questdb_settings", lambda: None)
    assert mig.migrate(dry_run=True) == {"status": "skipped", "reason": "questdb_not_configured"}


def test_migrate_noop_when_already_symbol(monkeypatch) -> None:
    mig = _load_mig()
    monkeypatch.setattr(mig, "load_questdb_settings", lambda: SimpleNamespace())
    adapter = MagicMock()
    adapter.connect.return_value = True
    adapter.execute_raw_query.side_effect = [
        [{"x": 1}],
        [{"column": "stock_code", "type": "SYMBOL"}],
    ]
    monkeypatch.setattr(mig, "create_questdb_adapter", lambda cfg: adapter)
    monkeypatch.setattr(mig, "get_runtime", lambda key, default=None: default)
    monkeypatch.setattr(mig, "safe_table_name", lambda name, default: default)

    out = mig.migrate(dry_run=False)
    assert out["status"] == "ok"
    assert out["action"] == "noop"
    adapter.disconnect.assert_called_once()


def test_migrate_dry_run_alter(monkeypatch) -> None:
    mig = _load_mig()
    monkeypatch.setattr(mig, "load_questdb_settings", lambda: SimpleNamespace())
    adapter = MagicMock()
    adapter.connect.return_value = True
    adapter.execute_raw_query.side_effect = [
        [{"x": 1}],
        [{"column": "stock_code", "type": "VARCHAR"}],
    ]
    monkeypatch.setattr(mig, "create_questdb_adapter", lambda cfg: adapter)
    monkeypatch.setattr(mig, "get_runtime", lambda key, default=None: default)
    monkeypatch.setattr(mig, "safe_table_name", lambda name, default: default)

    out = mig.migrate(dry_run=True)
    assert out["status"] == "dry_run"
    assert out["action"] == "alter_column"
    assert "ALTER COLUMN stock_code SYMBOL" in out["sql"]
