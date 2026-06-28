"""MySQL implementation for NewsArchiveRepository."""

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, desc, func, select

from app.core.logger import get_logger
from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer

from ...database.models.advanced import ArchivedNews as DBNews
from ...database.models.advanced import NewsSymbolMeta as DBMeta
from ...database.mysql_client import mysql_get_connection

logger = get_logger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _row_hash(market: str, symbol: str, scope: str, title: str, published_at: str, url: str) -> str:
    raw = f"{market}|{symbol}|{scope}|{title}|{published_at}|{url}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


class MySQLNewsArchiveRepository:
    """MySQL implementation of NewsArchiveRepository."""

    def __init__(self, mysql=None, session_factory=None) -> None:
        self._mysql = mysql
        self._session_factory = session_factory

    def _normalize_symbol(self, symbol: str) -> str:
        return SymbolNormalizer.to_db_code(symbol)

    def latest_fetched_at(self, market: str, symbol: str) -> str | None:
        m = market.upper()
        sym = self._normalize_symbol(symbol)
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(func.max(DBNews.fetched_at)).where(and_(DBNews.market == m, DBNews.symbol == sym))
                res = session.execute(stmt).scalar()
                return str(res) if res else None
            finally:
                session.close()
                self._session_factory.remove()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT MAX(fetched_at) AS ts FROM archived_news WHERE market = %s AND symbol = %s",
                    (m, sym),
                )
                row = cur.fetchone()
                return str(row["ts"]) if row and row["ts"] else None
        finally:
            conn.close()

    def get_meta(self, market: str, symbol: str) -> dict[str, Any]:
        m = market.upper()
        sym = self._normalize_symbol(symbol)
        if self._session_factory:
            session = self._session_factory()
            try:
                db_m = session.get(DBMeta, (m, sym))
                if not db_m:
                    return {}
                return {
                    "company_name": db_m.company_name or "",
                    "industry_hint": db_m.industry_hint or "",
                    "updated_at": db_m.updated_at or "",
                }
            finally:
                session.close()
                self._session_factory.remove()

        conn = mysql_get_connection(self._mysql)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT company_name, industry_hint, updated_at FROM news_symbol_meta "
                    "WHERE market = %s AND symbol = %s",
                    (m, sym),
                )
                r = cur.fetchone()
                if r:
                    return {
                        "company_name": r.get("company_name", ""),
                        "industry_hint": r.get("industry_hint", ""),
                        "updated_at": str(r.get("updated_at", "")),
                    }
                return {}
        finally:
            conn.close()

    def upsert_meta(self, market: str, symbol: str, *, company_name: str, industry_hint: str) -> None:
        m = market.upper()
        sym = self._normalize_symbol(symbol)
        now = _utc_now()
        if self._session_factory:
            session = self._session_factory()
            try:
                db_m = session.get(DBMeta, (m, sym))
                if not db_m:
                    db_m = DBMeta(market=m, symbol=sym)
                    session.add(db_m)
                db_m.company_name = company_name
                db_m.industry_hint = industry_hint
                db_m.updated_at = now
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
                self._session_factory.remove()
            return

        # Fallback raw SQL
        conn = mysql_get_connection(self._mysql, autocommit=True)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO news_symbol_meta (market, symbol, company_name, industry_hint, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        company_name=VALUES(company_name),
                        industry_hint=VALUES(industry_hint),
                        updated_at=VALUES(updated_at)
                    """,
                    (m, symbol, company_name, industry_hint, now),
                )
        finally:
            conn.close()

    def ingest_snapshot(self, market: str, symbol: str, snapshot: dict[str, Any]) -> int:
        m = market.upper()
        sym = symbol
        self.upsert_meta(m, sym, company_name=str(snapshot.get("company_name_hint") or ""), industry_hint=str(snapshot.get("industry_hint") or ""))
        now = _utc_now()
        inserted = 0

        if self._session_factory:
            session = self._session_factory()
            try:
                for scope, key in (("symbol", "news"), ("industry", "industry_news")):
                    for item in snapshot.get(key) or []:
                        title = str(item.get("title") or "")
                        url = str(item.get("url") or "")
                        if not title and not url:
                            continue
                        ch = _row_hash(m, sym, scope, title, str(item.get("published_at") or ""), url)

                        stmt = select(DBNews).where(and_(DBNews.market == m, DBNews.symbol == sym, DBNews.scope == scope, DBNews.content_hash == ch))
                        if session.scalars(stmt).first():
                            continue

                        db_n = DBNews(
                            market=m, symbol=sym, scope=scope, title=title,
                            summary=str(item.get("summary") or ""),
                            url=url or f"urn:empty:{ch[:16]}",
                            source=str(item.get("source") or ""),
                            published_at=str(item.get("published_at") or ""),
                            content_hash=ch, fetched_at=now
                        )
                        session.add(db_n)
                        inserted += 1
                session.commit()
                return inserted
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
                self._session_factory.remove()

        # Fallback raw SQL
        conn = mysql_get_connection(self._mysql, autocommit=True)
        try:
            with conn.cursor() as cur:
                for scope, key in (("symbol", "news"), ("industry", "industry_news")):
                    for item in snapshot.get(key) or []:
                        title = str(item.get("title") or "")
                        url = str(item.get("url") or "")
                        if not title and not url:
                            continue
                        ch = _row_hash(m, sym, scope, title, str(item.get("published_at") or ""), url)

                        cur.execute(
                            "SELECT 1 FROM archived_news WHERE market = %s AND symbol = %s AND scope = %s AND content_hash = %s",
                            (m, sym, scope, ch)
                        )
                        if cur.fetchone():
                            continue

                        cur.execute(
                            """
                            INSERT INTO archived_news (market, symbol, scope, title, summary, url, source, published_at, content_hash, fetched_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                m, sym, scope, title,
                                str(item.get("summary") or ""),
                                url or f"urn:empty:{ch[:16]}",
                                str(item.get("source") or ""),
                                str(item.get("published_at") or ""),
                                ch, now
                            )
                        )
                        inserted += 1
            return inserted
        finally:
            conn.close()

    def list_for_symbol(self, market: str, symbol: str, *, limit: int = 80) -> list[dict[str, Any]]:
        m = market.upper()
        sym = self._normalize_symbol(symbol)
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(DBNews).where(and_(DBNews.market == m, DBNews.symbol == sym)).order_by(desc(DBNews.fetched_at), desc(DBNews.published_at)).limit(limit)
                rows = session.scalars(stmt).all()
                return [{
                    "title": r.title, "summary": r.summary or "", "url": r.url,
                    "source": r.source or "", "published_at": r.published_at or "",
                    "fetched_at": r.fetched_at or "", "news_scope": r.scope
                } for r in rows]
            finally:
                session.close()
                self._session_factory.remove()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT title, summary, url, source, published_at, fetched_at, scope
                    FROM archived_news
                    WHERE market = %s AND symbol = %s
                    ORDER BY fetched_at DESC, published_at DESC
                    LIMIT %s
                    """,
                    (m, sym, limit)
                )
                rows = cur.fetchall()
                return [{
                    "title": r["title"], "summary": r["summary"] or "", "url": r["url"],
                    "source": r["source"] or "", "published_at": r["published_at"] or "",
                    "fetched_at": r["fetched_at"] or "", "news_scope": r["scope"]
                } for r in rows]
        finally:
            conn.close()
