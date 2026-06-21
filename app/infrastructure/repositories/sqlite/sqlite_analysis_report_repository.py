"""SQLite implementation for AnalysisReportRepository."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class SQLiteAnalysisReportRepository:
    """SQLite implementation of AnalysisReportRepository."""

    def __init__(self, sqlite_path: Path | str | None = None) -> None:
        self._sqlite_path = Path(sqlite_path) if sqlite_path else Path(".")
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_sqlite_db()

    def _init_sqlite_db(self) -> None:
        with sqlite3.connect(self._sqlite_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_reports (
                    id TEXT PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    dashboard TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    market_price REAL DEFAULT 0,
                    prediction_type TEXT,
                    validation_status TEXT DEFAULT 'pending',
                    validation_score REAL DEFAULT 0
                )
                """
            )
            conn.commit()

    def save_report(self, ticker: str, user_id: int, dashboard: str, prediction: str, price: float) -> None:
        report_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        created_at = datetime.now().isoformat()
        with sqlite3.connect(self._sqlite_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO analysis_reports
                (id, ticker, user_id, dashboard, created_at, market_price, prediction_type, validation_status, validation_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    ticker,
                    int(user_id),
                    dashboard,
                    created_at,
                    float(price),
                    prediction,
                    "pending",
                    0.0,
                ),
            )
            conn.commit()

    def get_pending_reports(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self._sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM analysis_reports WHERE validation_status = 'pending' ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def update_validation(self, report_id: str, score: float) -> None:
        with sqlite3.connect(self._sqlite_path) as conn:
            conn.execute(
                "UPDATE analysis_reports SET validation_status=?, validation_score=? WHERE id=?",
                ("validated", float(score), report_id),
            )
            conn.commit()
