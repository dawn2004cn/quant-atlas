"""SQLite implementation of AgentRepository."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.domain.ports import AgentRepository
from app.domain.agent_entities import MarketInsight, ReportInterpretation


class SQLiteAgentRepository(AgentRepository):
    """SQLite implementation of AgentRepository."""

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
                CREATE TABLE IF NOT EXISTS agent_market_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market TEXT NOT NULL,
                    sentiment_score REAL,
                    sentiment_label TEXT,
                    trend_prediction TEXT,
                    hot_sectors TEXT,
                    full_analysis TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS agent_report_interpretations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_title TEXT NOT NULL,
                    source TEXT,
                    report_date TEXT,
                    summary TEXT,
                    key_takeaways TEXT,
                    market_impact TEXT,
                    full_interpretation TEXT,
                    metadata_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()

    def save_market_insight(self, insight: MarketInsight) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO agent_market_insights (market, sentiment_score, sentiment_label, trend_prediction, hot_sectors, full_analysis)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    insight.market,
                    insight.sentiment_score,
                    insight.sentiment_label,
                    insight.trend_prediction,
                    json.dumps(insight.hot_sectors) if insight.hot_sectors else "[]",
                    insight.full_analysis
                )
            )
            conn.commit()
            insight.id = cur.lastrowid
            return insight.id

    def list_market_insights(self, market: str, limit: int = 10) -> list[MarketInsight]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT * FROM agent_market_insights
                WHERE market = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (market, limit)
            )
            rows = cur.fetchall()
            return [self._map_row_to_insight(r) for r in rows]

    def save_report_interpretation(self, interpretation: ReportInterpretation) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO agent_report_interpretations (report_title, source, report_date, summary, key_takeaways, market_impact, full_interpretation, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    interpretation.report_title,
                    interpretation.source,
                    interpretation.report_date,
                    interpretation.summary,
                    json.dumps(interpretation.key_takeaways) if interpretation.key_takeaways else "[]",
                    interpretation.market_impact,
                    interpretation.full_interpretation,
                    json.dumps(interpretation.metadata) if interpretation.metadata else "{}"
                )
            )
            conn.commit()
            interpretation.id = cur.lastrowid
            return interpretation.id

    def _map_row_to_insight(self, row) -> MarketInsight:
        return MarketInsight(
            id=row["id"],
            market=row["market"],
            sentiment_score=row["sentiment_score"],
            sentiment_label=row["sentiment_label"],
            trend_prediction=row["trend_prediction"],
            hot_sectors=json.loads(row["hot_sectors"]) if row["hot_sectors"] else [],
            full_analysis=row["full_analysis"],
            created_at=row["created_at"]
        )

    def _map_row_to_report(self, row) -> ReportInterpretation:
        return ReportInterpretation(
            id=row["id"],
            report_title=row["report_title"],
            source=row["source"],
            report_date=row["report_date"],
            summary=row["summary"],
            key_takeaways=json.loads(row["key_takeaways"]) if row["key_takeaways"] else [],
            market_impact=row["market_impact"],
            full_interpretation=row["full_interpretation"],
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            created_at=row["created_at"]
        )
