from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict
from app.core.registry import ServiceRegistry
from app.modules.data.services.legacy_migration_service import LegacyDataMigrationService
from app.core.logger import get_logger

logger = get_logger(__name__)

class DataMigrationRunner:
    """
    A coordinator that manages the end-to-end migration process,
    providing progress tracking and error recovery.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.migration_service: LegacyDataMigrationService = registry.get("legacy_migration_service")
        self._progress: Dict[str, Any] = {
            "status": "idle",
            "current_file": "",
            "total_files": 0,
            "processed_files": 0,
            "total_rows": 0,
            "errors": []
        }

    async def run_full_migration(self) -> Dict[str, Any]:
        """
        Executes the full migration of all legacy .db files into the Unified Lake.
        """
        logger.info("Starting Full Data Lake Migration...")
        self._progress["status"] = "running"
        
        db_files = self.migration_service.find_legacy_db_files()
        self._progress["total_files"] = len(db_files)
        self._progress["processed_files"] = 0
        self._progress["total_rows"] = 0
        self._progress["errors"] = []

        for db_path in db_files:
            self._progress["current_file"] = db_path
            try:
                # We implement a per-file migration to track progress
                tables = self.migration_service._extract_tables_from_db(db_path)
                file_rows = 0
                for table in tables:
                    file_rows += self.migration_service._migrate_table(db_path, table)
                
                self._progress["processed_files"] += 1
                self._progress["total_rows"] += file_rows
                logger.info(f"Migrated {db_path}: {file_rows} rows.")
            except Exception as e:
                err_msg = f"Failed to migrate {db_path}: {str(e)}"
                logger.error(err_msg)
                self._progress["errors"].append(err_msg)

        self._progress["status"] = "completed"
        logger.info(f"Migration finished. Total rows: {self._progress['total_rows']}")
        return self._progress

    def get_progress(self) -> Dict[str, Any]:
        """Return current migration status."""
        return self._progress
