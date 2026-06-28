"""Regression tests for LegacyDataMigrationService (Phase 14.5)."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from app.modules.data.services.legacy_migration_service import LegacyDataMigrationService


class TestLegacyDataMigrationService:
    """Legacy .db migration to unified data lake."""

    @pytest.fixture
    def registry(self):
        reg = MagicMock()
        reg.get_or_none.return_value = MagicMock()
        return reg

    @pytest.fixture
    def service(self, tmp_path, monkeypatch, registry):
        monkeypatch.setattr("app.modules.data.services.legacy_migration_service.BASE_DIR", tmp_path)
        s = LegacyDataMigrationService(registry)
        s.root_dir = str(tmp_path)
        return s

    def test_find_legacy_db_files_empty(self, service, tmp_path):
        files = service.find_legacy_db_files()
        assert files == []

    def test_find_legacy_db_files_excludes_lake(self, service, tmp_path):
        # Create a legacy .db file
        (tmp_path / "legacy_data.db").write_text("")
        # Create the lake db
        (tmp_path / "quant_atlas_lake.db").write_text("")
        files = service.find_legacy_db_files()
        assert len(files) == 1
        assert "legacy_data.db" in files[0]
        assert "quant_atlas_lake.db" not in str(files[0])

    def test_find_legacy_db_files_nested(self, service, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "old_data.db").write_text("")
        files = service.find_legacy_db_files()
        assert len(files) == 1
        assert "old_data.db" in files[0]

    def test_extract_tables_from_db(self, service, tmp_path):
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE stocks (symbol TEXT, date TEXT, close REAL)")
        conn.execute("CREATE TABLE trades (symbol TEXT, price REAL)")
        conn.close()

        tables = service._extract_tables_from_db(str(db_path))
        assert "stocks" in tables
        assert "trades" in tables

    def test_extract_tables_nonexistent_db(self, service):
        tables = service._extract_tables_from_db("/nonexistent/path.db")
        assert tables == []

    def test_migrate_table_detects_time_and_symbol_cols(self, service, tmp_path):
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE data (symbol TEXT, date TEXT, close REAL, volume INTEGER)")
        conn.execute("INSERT INTO data VALUES ('600519', '2026-01-01', 150.0, 1000000)")
        conn.execute("INSERT INTO data VALUES ('600519', '2026-01-02', 152.0, 1200000)")
        conn.close()

        import asyncio
        rows = asyncio.run(service._migrate_table(str(db_path), "data"))
        assert rows > 0  # at least some rows migrated

    def test_migrate_table_skips_empty(self, service, tmp_path):
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE empty (symbol TEXT, date TEXT)")
        conn.close()

        import asyncio
        rows = asyncio.run(service._migrate_table(str(db_path), "empty"))
        assert rows == 0

    def test_migrate_all_no_files(self, service):
        import asyncio
        result = asyncio.run(service.migrate_all())
        assert result["total_migrated"] == 0
        assert result["migrated_files"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
