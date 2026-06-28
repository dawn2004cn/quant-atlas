"""MySQL implementation for MomentsRepository."""

import json
import logging

logger = logging.getLogger(__name__)
from typing import Any

from sqlalchemy import and_, desc, func, select

from ....core.shanghai_time import now_sh_str
from ...database.models.moments import MomentAttachment as DBAttachment
from ...database.models.moments import MomentLike as DBLike
from ...database.models.moments import MomentPost as DBPost
from ...database.mysql_client import mysql_get_connection


class MySQLMomentsRepository:
    """MySQL implementation of MomentsRepository."""

    def __init__(self, mysql=None, session_factory=None) -> None:
        self._mysql = mysql
        self._session_factory = session_factory

    def _to_dict(self, model_obj):
        return {c.name: getattr(model_obj, c.name) for c in model_obj.__table__.columns}

    def _row_to_dict(self, row, cur) -> dict[str, Any]:
        columns = [d[0] for d in cur.description]
        return dict(zip(columns, row))

    def create_post(self, *, actor_type: str, actor_id: str, author_name: str, content_text: str, content: dict[str, Any] | None = None, market_date: str | None = None) -> int:
        now = now_sh_str()
        payload_json = json.dumps(content or {}, ensure_ascii=False)
        if self._session_factory:
            session = self._session_factory()
            try:
                db_p = DBPost(
                    actor_type=actor_type,
                    actor_id=actor_id,
                    author_name=author_name,
                    content_text=content_text,
                    content_json=payload_json,
                    market_date=(market_date[:10] if market_date else None),
                    created_at=now
                )
                session.add(db_p)
                session.commit()
                return db_p.post_id
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        conn = None
        cur = None
        try:
            conn = mysql_get_connection(self._mysql, autocommit=False)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO moments_posts (actor_type, actor_id, author_name, content_text, content_json, market_date, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (actor_type, actor_id, author_name, content_text, payload_json, market_date[:10] if market_date else None, now)
            )
            conn.commit()
            return cur.lastrowid or 0
        except Exception:
            if conn:
                conn.ping(reconnect=True)
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO moments_posts (actor_type, actor_id, author_name, content_text, content_json, market_date, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (actor_type, actor_id, author_name, content_text, payload_json, market_date[:10] if market_date else None, now)
                )
                conn.commit()
                return cur.lastrowid or 0
            return 0
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    def add_attachment(self, *, post_id: int, media_type: str, file_name: str, file_path: str, file_url: str, mime_type: str | None, size_bytes: int, meta: dict[str, Any] | None = None) -> int:
        now = now_sh_str()
        meta_json = json.dumps(meta or {}, ensure_ascii=False)
        if self._session_factory:
            session = self._session_factory()
            try:
                db_a = DBAttachment(
                    post_id=post_id,
                    media_type=media_type,
                    file_name=file_name,
                    file_path=file_path,
                    file_url=file_url,
                    mime_type=mime_type or "",
                    size_bytes=int(size_bytes or 0),
                    meta_json=meta_json,
                    created_at=now
                )
                session.add(db_a)
                session.commit()
                return db_a.attachment_id
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        conn = None
        cur = None
        try:
            conn = mysql_get_connection(self._mysql, autocommit=False)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO moment_attachments (post_id, media_type, file_name, file_path, file_url, mime_type, size_bytes, meta_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (post_id, media_type, file_name, file_path, file_url, mime_type or "", int(size_bytes or 0), meta_json, now)
            )
            conn.commit()
            return cur.lastrowid or 0
        except Exception:
            if conn:
                conn.ping(reconnect=True)
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO moment_attachments (post_id, media_type, file_name, file_path, file_url, mime_type, size_bytes, meta_json, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (post_id, media_type, file_name, file_path, file_url, mime_type or "", int(size_bytes or 0), meta_json, now)
                )
                conn.commit()
                return cur.lastrowid or 0
            return 0
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    def list_feed(self, *, limit: int = 50, before_post_id: int | None = None) -> list[dict[str, Any]]:
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(DBPost).order_by(desc(DBPost.post_id)).limit(limit)
                if before_post_id:
                    stmt = stmt.where(DBPost.post_id < before_post_id)

                posts = session.scalars(stmt).all()
                res = []
                for p in posts:
                    d = self._to_dict(p)
                    d["attachments"] = [self._to_dict(a) for a in p.attachments]
                    d["like_count"] = len(p.likes)
                    d["comment_count"] = len(p.comments)
                    res.append(d)
                return res
            finally:
                session.close()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        cur = None
        try:
            cur = conn.cursor()
            if before_post_id:
                cur.execute(
                    "SELECT * FROM moments_posts WHERE post_id < %s ORDER BY post_id DESC LIMIT %s",
                    (before_post_id, limit)
                )
            else:
                cur.execute("SELECT * FROM moments_posts ORDER BY post_id DESC LIMIT %s", (limit,))
            posts = cur.fetchall()
            res = []
            for p in posts:
                d = self._row_to_dict(p, cur)
                d["attachments"] = []
                d["like_count"] = 0
                d["comment_count"] = 0
                res.append(d)
            return res
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_moments_repository.py.list_feed: %s", e)
            cur = conn.cursor()
            if before_post_id:
                cur.execute(
                    "SELECT * FROM moments_posts WHERE post_id < %s ORDER BY post_id DESC LIMIT %s",
                    (before_post_id, limit)
                )
            else:
                cur.execute("SELECT * FROM moments_posts ORDER BY post_id DESC LIMIT %s", (limit,))
            posts = cur.fetchall()
            res = []
            for p in posts:
                d = self._row_to_dict(p, cur)
                d["attachments"] = []
                d["like_count"] = 0
                d["comment_count"] = 0
                res.append(d)
            return res
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_moments_repository.py.list_feed: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_moments_repository.py.list_feed: %s", e)

    def toggle_like(self, *, post_id: int, user_id: str) -> dict[str, Any]:
        if self._session_factory:
            session = self._session_factory()
            try:
                stmt = select(DBLike).where(and_(DBLike.post_id == post_id, DBLike.user_id == user_id))
                like = session.scalars(stmt).first()
                if like:
                    session.delete(like)
                    liked = False
                else:
                    like = DBLike(post_id=post_id, user_id=user_id, created_at=now_sh_str())
                    session.add(like)
                    liked = True
                session.commit()

                cnt = session.query(func.count(DBLike.like_id)).where(DBLike.post_id == post_id).scalar()
                return {"ok": True, "liked": liked, "like_count": cnt}
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        conn = mysql_get_connection(self._mysql, autocommit=False)
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT like_id FROM moment_likes WHERE post_id = %s AND user_id = %s", (post_id, user_id))
            existing = cur.fetchone()
            if existing:
                cur.execute("DELETE FROM moment_likes WHERE post_id = %s AND user_id = %s", (post_id, user_id))
                liked = False
            else:
                cur.execute(
                    "INSERT INTO moment_likes (post_id, user_id, created_at) VALUES (%s, %s, %s)",
                    (post_id, user_id, now_sh_str())
                )
                liked = True
            conn.commit()
            cur.execute("SELECT COUNT(*) as cnt FROM moment_likes WHERE post_id = %s", (post_id,))
            cnt_row = self._row_to_dict(cur.fetchone(), cur)
            cnt = cnt_row["cnt"]
            return {"ok": True, "liked": liked, "like_count": cnt}
        except Exception:
            conn.ping(reconnect=True)
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_moments_repository.py.toggle_like: %s", e)
            cur = conn.cursor()
            cur.execute("SELECT like_id FROM moment_likes WHERE post_id = %s AND user_id = %s", (post_id, user_id))
            existing = cur.fetchone()
            if existing:
                cur.execute("DELETE FROM moment_likes WHERE post_id = %s AND user_id = %s", (post_id, user_id))
                liked = False
            else:
                cur.execute(
                    "INSERT INTO moment_likes (post_id, user_id, created_at) VALUES (%s, %s, %s)",
                    (post_id, user_id, now_sh_str())
                )
                liked = True
            conn.commit()
            cur.execute("SELECT COUNT(*) as cnt FROM moment_likes WHERE post_id = %s", (post_id,))
            cnt_row = self._row_to_dict(cur.fetchone(), cur)
            cnt = cnt_row["cnt"]
            return {"ok": True, "liked": liked, "like_count": cnt}
        finally:
            if cur:
                try:
                    cur.close()
                except Exception as e:
                    logger.debug("mysql_moments_repository.py.toggle_like: %s", e)
            try:
                conn.close()
            except Exception as e:
                logger.debug("mysql_moments_repository.py.toggle_like: %s", e)
