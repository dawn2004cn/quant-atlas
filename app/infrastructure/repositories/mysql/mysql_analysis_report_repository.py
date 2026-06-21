"""MySQL implementation for AnalysisReportRepository."""

from datetime import datetime
from typing import Any
from sqlalchemy import select

from ...database.mysql_client import mysql_get_connection
from ...database.models.advanced import AnalysisReport as DBReport


import logging
logger = logging.getLogger(__name__)
class MySQLAnalysisReportRepository:
    """MySQL implementation of AnalysisReportRepository."""

    def __init__(self, mysql=None, session_factory=None) -> None:
        self._mysql = mysql
        self._session_factory = session_factory

    def _to_dict(self, model_obj) -> dict[str, Any]:
        return {c.name: getattr(model_obj, c.name) for c in model_obj.__table__.columns}

    def save_report(self, ticker: str, user_id: int, dashboard: str, prediction: str, price: float) -> None:
        report_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        created_at = datetime.now().isoformat()

        if self._session_factory:
            session = self._session_factory()
            try:
                session.add(
                    DBReport(
                        id=report_id,
                        ticker=ticker,
                        user_id=user_id,
                        dashboard=dashboard,
                        created_at=created_at,
                        market_price=price,
                        prediction_type=prediction,
                        validation_status="pending",
                        validation_score=0.0,
                    )
                )
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
            return

        conn = None
        cur = None
        try:
            conn = mysql_get_connection(self._mysql, autocommit=False)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO analysis_reports
                (id, ticker, user_id, dashboard, created_at, market_price, prediction_type, validation_status, validation_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        except Exception:
            if conn:
                conn.ping(reconnect=True)
                if cur:
                    try:
                        cur.close()
                    except Exception as e:
                        logger.debug("mysql_analysis_report_repository.py.save_report: %s", e)
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO analysis_reports
                    (id, ticker, user_id, dashboard, created_at, market_price, prediction_type, validation_status, validation_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    def get_pending_reports(self) -> list[dict[str, Any]]:
        if self._session_factory:
            session = self._session_factory()
            try:
                rows = session.scalars(select(DBReport).where(DBReport.validation_status == "pending")).all()
                return [self._to_dict(r) for r in rows]
            finally:
                session.close()

        conn = None
        cur = None
        try:
            conn = mysql_get_connection(self._mysql, autocommit=False)
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM analysis_reports WHERE validation_status = 'pending' ORDER BY created_at DESC"
            )
            return [dict(r) for r in cur.fetchall()]
        except Exception:
            if conn:
                conn.ping(reconnect=True)
                if cur:
                    try:
                        cur.close()
                    except Exception as e:
                        logger.debug("mysql_analysis_report_repository.py.get_pending_reports: %s", e)
                cur = conn.cursor()
                cur.execute(
                    "SELECT * FROM analysis_reports WHERE validation_status = 'pending' ORDER BY created_at DESC"
                )
                return [dict(r) for r in cur.fetchall()]
            return []
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    def update_validation(self, report_id: str, score: float) -> None:
        if self._session_factory:
            session = self._session_factory()
            try:
                db_r = session.get(DBReport, report_id)
                if db_r:
                    db_r.validation_status = "validated"
                    db_r.validation_score = float(score)
                    session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
            return

        conn = None
        cur = None
        try:
            conn = mysql_get_connection(self._mysql, autocommit=False)
            cur = conn.cursor()
            cur.execute(
                "UPDATE analysis_reports SET validation_status=%s, validation_score=%s WHERE id=%s",
                ("validated", float(score), report_id),
            )
            conn.commit()
        except Exception:
            if conn:
                conn.ping(reconnect=True)
                if cur:
                    try:
                        cur.close()
                    except Exception as e:
                        logger.debug("mysql_analysis_report_repository.py.update_validation: %s", e)
                cur = conn.cursor()
                cur.execute(
                    "UPDATE analysis_reports SET validation_status=%s, validation_score=%s WHERE id=%s",
                    ("validated", float(score), report_id),
                )
                conn.commit()
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
