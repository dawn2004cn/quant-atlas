from __future__ import annotations

import os
import sqlite3
import pandas as pd
import logging
from typing import List, Tuple, Dict, Any
from app.core.registry import ServiceRegistry
from app.core.mesh.unified_data_lake import DataScope, DataQuery
from app.modules.data.services.data_lake_manager import DataLakeManager
from app.config import BASE_DIR

logger = logging.getLogger(__name__)

class LegacyDataMigrationService:
    """
    Service to migrate data from scattered legacy .db files into the Unified Data Lake.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.lake_manager: DataLakeManager | None = registry.get_or_none("data_lake_manager")
        self.root_dir = str(BASE_DIR)

    def find_legacy_db_files(self) -> List[str]:
        """Find all .db files excluding the unified lake itself."""
        legacy_files = []
        lake_db_name = "quant_atlas_lake.db"
        
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith(".db") and file != lake_db_name:
                    legacy_files.append(os.path.join(root, file))
        
        return legacy_files

    def _extract_tables_from_db(self, db_path: str) -> List[str]:
        """Get a list of tables from a sqlite db."""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Could not read tables from {db_path}: {e}")
            return []

    async def _migrate_table(self, db_path: str, table_name: str):
        """
        Attempt to migrate a single table. 
        This requires heuristic mapping since legacy schemas vary.
        """
        try:
            with sqlite3.connect(db_path) as conn:
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                
                if df.empty:
                    return 0

                time_col = next((c for c in df.columns if any(x in c.lower() for x in ['date', 'time', 'ts'])), None)
                symbol_col = next((c for c in df.columns if any(x in c.lower() for x in ['symbol', 'code', 'ticker'])), None)
                
                if time_col and symbol_col:
                    symbols = df[symbol_col].unique()
                    rows_migrated = 0
                    for sym in symbols:
                        sym_df = df[df[symbol_col] == sym].copy()
                        sym_df = sym_df.set_index(time_col).drop(columns=[symbol_col])
                        
                        await self.lake_manager.save_data(
                            symbol=str(sym),
                            data=sym_df,
                            scope=DataScope.HISTORICAL
                        )
                        rows_migrated += len(sym_df)
                    return rows_migrated
                else:
                    logger.debug(f"Skipping table {table_name} in {db_path}: No time/symbol columns found.")
                    return 0
        except Exception as e:
            logger.debug(f"Skipping table {table_name} in {db_path}: {e}")
            return 0

    async def migrate_all(self) -> Dict[str, Any]:
        """Main entry point for full migration."""
        db_files = self.find_legacy_db_files()
        logger.info(f"Found {len(db_files)} potential legacy database files.")
        
        total_migrated = 0
        migrated_files = []

        for db_path in db_files:
            tables = self._extract_tables_from_db(db_path)
            file_migrated_count = 0
            for table in tables:
                file_migrated_count += await self._migrate_table(db_path, table)
            
            if file_migrated_count > 0:
                migrated_files.append({"path": db_path, "rows": file_migrated_count})
                total_migrated += file_migrated_count

        return {
            "status": "completed",
            "total_files_scanned": len(db_files),
            "total_rows_migrated": total_migrated,
            "details": migrated_files
        }
