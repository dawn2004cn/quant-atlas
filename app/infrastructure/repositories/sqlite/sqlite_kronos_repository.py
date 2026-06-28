"""SQLite implementation of KronosRepository."""

import json
import sqlite3
from pathlib import Path

from app.domain.ports import KronosRepository
from app.domain.kronos_entities import KronosModel, KronosPrediction


class SQLiteKronosRepository(KronosRepository):
    """SQLite implementation of KronosRepository."""

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
                CREATE TABLE IF NOT EXISTS kronos_models (
                    model_id TEXT PRIMARY KEY,
                    model_type TEXT,
                    hf_path TEXT,
                    local_path TEXT,
                    is_active INTEGER DEFAULT 1,
                    metadata_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS kronos_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    prediction_date TEXT,
                    horizon_days INTEGER,
                    forecast_json TEXT,
                    metrics_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()

    def save_model(self, model: KronosModel) -> None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM kronos_models WHERE model_id = ?",
                (model.model_id,)
            )
            existing = cur.fetchone()
            if not existing:
                conn.execute(
                    """
                    INSERT INTO kronos_models (model_id, model_type, hf_path, local_path, is_active, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        model.model_id,
                        model.model_type,
                        model.hf_path,
                        model.local_path,
                        1 if model.is_active else 0,
                        json.dumps(model.metadata) if model.metadata else "{}"
                    )
                )
            else:
                conn.execute(
                    """
                    UPDATE kronos_models SET
                        model_type = ?,
                        hf_path = ?,
                        local_path = ?,
                        is_active = ?,
                        metadata_json = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE model_id = ?
                    """,
                    (
                        model.model_type,
                        model.hf_path,
                        model.local_path,
                        1 if model.is_active else 0,
                        json.dumps(model.metadata) if model.metadata else "{}",
                        model.model_id
                    )
                )
            conn.commit()

    def get_model(self, model_id: str) -> KronosModel | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM kronos_models WHERE model_id = ?",
                (model_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._map_row_to_model(row)

    def list_active_models(self) -> list[KronosModel]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM kronos_models WHERE is_active = 1"
            )
            rows = cur.fetchall()
            return [self._map_row_to_model(r) for r in rows]

    def save_prediction(self, prediction: KronosPrediction) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO kronos_predictions (ticker, model_id, prediction_date, horizon_days, forecast_json, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    prediction.ticker,
                    prediction.model_id,
                    prediction.prediction_date,
                    prediction.horizon_days,
                    json.dumps(prediction.forecast_data) if prediction.forecast_data else "{}",
                    json.dumps(prediction.metrics) if prediction.metrics else "{}"
                )
            )
            conn.commit()
            prediction.id = cur.lastrowid
            return prediction.id

    def _map_row_to_model(self, row) -> KronosModel:
        return KronosModel(
            model_id=row["model_id"],
            model_type=row["model_type"],
            hf_path=row["hf_path"],
            local_path=row["local_path"],
            is_active=bool(row["is_active"]),
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            created_at=row["created_at"]
        )
