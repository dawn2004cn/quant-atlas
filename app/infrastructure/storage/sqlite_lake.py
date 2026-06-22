from __future__ import annotations

from app.core.mesh.unified_data_lake import UnifiedDataStore, DataQuery, DataScope
import pandas as pd
import sqlite3
import os
from typing import Any, Dict, List, Optional
from app.config import BASE_DIR


class SQLiteDataLakeStore(UnifiedDataStore):
    """
    SQLite implementation of the Unified Data Lake.
    This serves as the 'Migration Bridge'. It replaces scattered .db files
    with a single, structured lake database.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(str(BASE_DIR), "instance", "quant_atlas_lake.db")
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS time_series_data (
                    symbol TEXT,
                    market TEXT,
                    timestamp DATETIME,
                    value REAL,
                    column_name TEXT,
                    scope TEXT,
                    PRIMARY KEY (symbol, timestamp, column_name)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON time_series_data(timestamp)")

    async def fetch_data(self, query: DataQuery) -> pd.DataFrame:
        """Fetch data from the unified SQLite lake."""
        with sqlite3.connect(self.db_path) as conn:
            sql = "SELECT timestamp, column_name, value FROM time_series_data WHERE symbol = ? AND market = ?"
            params = [query.symbol, query.market]

            if query.start_date:
                sql += " AND timestamp >= ?"
                params.append(query.start_date.isoformat())
            if query.end_date:
                sql += " AND timestamp <= ?"
                params.append(query.end_date.isoformat())

            df = pd.read_sql_query(sql, conn, params=params)

            if df.empty:
                return pd.DataFrame()

            # Pivot from long format to wide format
            df = df.pivot(index="timestamp", columns="column_name", values="value")
            return df

    async def write_data(self, symbol: str, data: pd.DataFrame, scope: DataScope):
        """Write wide-format data into the long-format lake table."""
        with sqlite3.connect(self.db_path) as conn:
            for col in data.columns:
                df_long = data[[col]].reset_index()
                df_long.columns = ["timestamp", "value"]
                df_long["symbol"] = symbol
                df_long["column_name"] = col
                df_long["scope"] = scope.value

                # Build correct (symbol, timestamp, value, column_name, scope) tuples
                records = [
                    (row["symbol"], str(row["timestamp"]), float(row["value"]),
                     row["column_name"], row["scope"])
                    for _, row in df_long.iterrows()
                ]
                conn.executemany(
                    "INSERT OR REPLACE INTO time_series_data (symbol, timestamp, value, column_name, scope) VALUES (?, ?, ?, ?, ?)",
                    records,
                )

    def get_health_status(self) -> Dict[str, Any]:
        return {
            "type": "sqlite_bridge",
            "path": self.db_path,
            "status": "healthy",
            "metrics": {"latency": "low", "reliability": "high"},
        }
