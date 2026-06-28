from __future__ import annotations

"""Celery 任务事件写入 Redis 列表（或内存回退），供消息中心 API 读取。"""


import json
from collections import deque
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.logger import get_logger

from ...core.runtime_config import get_runtime

logger = get_logger(__name__)

REDIS_KEY = "quant:task_messages"
MAX_MESSAGES = 500

_singleton: TaskMessageStore | None = None


def configure_task_message_store(url: str) -> TaskMessageStore:
    """在 Flask ``create_app`` 中调用，与 Celery worker 环境变量保持一致。"""
    global _singleton
    _singleton = TaskMessageStore(url)
    return _singleton


def get_task_message_store() -> TaskMessageStore:
    """Worker 信号与未显式 configure 时的默认入口。"""
    global _singleton
    if _singleton is None:
        url = (
            (get_runtime("TASK_MESSAGE_REDIS_URL", "") or "").strip()
            or (get_runtime("CELERY_BROKER_URL", "") or "").strip()
            or ""
        )
        _singleton = TaskMessageStore(url)
    return _singleton

_LABELS: dict[str, str] = {}

def task_label(task_name: str) -> str:
    if not _LABELS:
        from app.core.logger import get_logger
        try:
            from app.tasks.registry import ensure_task_registry
            reg = ensure_task_registry()
            _LABELS.update({
                name: info.get("label", name)
                for name, info in reg.items()
            })
        except Exception as exc:
            get_logger(__name__).debug("Failed to load TASK_REGISTRY for labels: %s", exc)
    return _LABELS.get(task_name, task_name)



class TaskMessageStore:
    def __init__(self, redis_url: str) -> None:
        self._url = (redis_url or "").strip()
        self._redis: Any = None
        self._memory: deque[dict[str, Any]] = deque(maxlen=MAX_MESSAGES)
        self._use_memory = self._url in ("", "memory://", "disabled")
        if not self._use_memory:
            try:
                import redis

                self._redis = redis.Redis.from_url(
                    self._url,
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                    socket_timeout=2.0,
                )
                self._redis.ping()
            except Exception as exc:
                logger.warning("task message redis unavailable, using memory: %s", exc)
                self._redis = None
                self._use_memory = True

    @property
    def enabled_backend(self) -> str:
        if self._redis is not None:
            return "redis"
        return "memory"

    def push(
        self,
        *,
        event: str,
        task_id: str,
        task_name: str,
        detail: str = "",
        meta: dict[str, Any] | None = None,
    ) -> str:
        msg_id = str(uuid4())
        payload: dict[str, Any] = {
            "id": msg_id,
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event": event,
            "task_id": task_id,
            "task_name": task_name,
            "label": task_label(task_name),
            "detail": (detail or "")[:2000],
            "meta": meta or {},
        }
        line = json.dumps(payload, ensure_ascii=False)
        if self._redis is not None:
            try:
                pipe = self._redis.pipeline()
                pipe.lpush(REDIS_KEY, line)
                pipe.ltrim(REDIS_KEY, 0, MAX_MESSAGES - 1)
                pipe.execute()
            except Exception as exc:
                logger.warning("task message lpush failed: %s", exc)
                self._memory.appendleft(payload)
        else:
            self._memory.appendleft(payload)
        try:
            from app.infrastructure.messaging.task_event_hub import get_task_event_hub

            get_task_event_hub().publish(task_id, payload)
        except Exception as exc:
            logger.debug("task event hub publish skipped: %s", exc)
        return msg_id

    def list_recent(self, *, limit: int = 80) -> list[dict[str, Any]]:
        lim = min(max(1, limit), 200)
        if self._redis is not None:
            try:
                rows = self._redis.lrange(REDIS_KEY, 0, lim - 1)
                out: list[dict[str, Any]] = []
                for x in rows:
                    try:
                        out.append(json.loads(x))
                    except json.JSONDecodeError:
                        continue
                return out
            except Exception as exc:
                logger.warning("task message lrange failed: %s", exc)
        return list(self._memory)[:lim]
