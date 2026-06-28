"""SQLite implementation of QuantMLFactorRepository."""

import json
import sqlite3
from pathlib import Path

from app.domain.ports import QuantMLFactorRepository
from app.domain.quantml_entities import QuantMLFactor


class SQLiteQuantMLFactorRepository(QuantMLFactorRepository):
    """SQLite implementation of QuantMLFactorRepository."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else Path(".")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(str(self._db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS quantml_factors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    factor_name TEXT NOT NULL,
                    category TEXT,
                    ic_mean REAL,
                    icir REAL,
                    long_average REAL,
                    long_short REAL,
                    t_stat REAL,
                    metadata_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()

    def save_factor(self, factor: QuantMLFactor) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO quantml_factors (factor_name, category, ic_mean, icir, long_average, long_short, t_stat, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    factor.factor_name,
                    factor.category,
                    factor.ic_mean,
                    factor.icir,
                    factor.long_average,
                    factor.long_short,
                    factor.t_stat,
                    json.dumps(factor.metadata) if factor.metadata else "{}"
                )
            )
            conn.commit()
            factor.id = cur.lastrowid
            return factor.id

    def clear_all(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM quantml_factors")
            conn.commit()

    def list_factors(self, category: str | None = None, limit: int = 100) -> list[QuantMLFactor]:
        with self._connect() as conn:
            if category:
                cur = conn.execute(
                    "SELECT * FROM quantml_factors WHERE category = ? LIMIT ?",
                    (category, limit)
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM quantml_factors LIMIT ?",
                    (limit,)
                )
            rows = cur.fetchall()
            return [self._map_row_to_factor(r) for r in rows]

    def _map_row_to_factor(self, row) -> QuantMLFactor:
        return QuantMLFactor(
            id=row["id"],
            factor_name=row["factor_name"],
            category=row["category"],
            ic_mean=row["ic_mean"],
            icir=row["icir"],
            long_average=row["long_average"],
            long_short=row["long_short"],
            t_stat=row["t_stat"],
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            created_at=row["created_at"]
        )
