from __future__ import annotations

"""Persist Celery task progress snapshots for UI polling.

Supports three backends (selected automatically):
1. **Redis** — real-time pub/sub sync; preferred when ``redis_url`` is given.
2. **File** — JSON files under ``instance/task_progress/``.
3. **Memory** — in-process dict (fallback when both are unavailable).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config.settings import INSTANCE_DIR

logger = logging.getLogger(__name__)

_REDIS_PROGRESS_CHANNEL = "quant:task_progress"


class TaskProgressStore:
    """Persistent progress store with Redis-backed real-time sync.

    Usage::

        store = TaskProgressStore(redis_url="redis://...")
        store.init("task-123", task_name="回测", steps=["排队","执行","完成"])
        store.update("task-123", step_index=1, message="正在回测…", percent=45)
        snapshot = store.get("task-123")
    """

    def __init__(self, root: Path | None = None, redis_url: str | None = None) -> None:
        self._root = root or (INSTANCE_DIR / "task_progress")
        self._memory: dict[str, dict[str, Any]] = {}
        self._use_memory = False
        self._redis: Any = None
        self._redis_pub: Any = None
        if redis_url:
            self._init_redis(redis_url)

    def _init_redis(self, redis_url: str) -> None:
        try:
            from app.infrastructure.redis_client import RedisClientPool

            self._redis = RedisClientPool.get(redis_url).client
            self._redis.ping()
            self._redis_pub = self._redis.pubsub()
            logger.info("TaskProgressStore: Redis connected (%s)", redis_url[:30])
        except Exception as exc:
            logger.warning("TaskProgressStore: Redis unavailable (%s), fallback to file", exc)
            self._redis = None

    def init(
        self,
        task_id: str,
        *,
        task_name: str = "",
        steps: list[str] | None = None,
    ) -> dict[str, Any]:
        tid = (task_id or "").strip()
        step_labels = list(steps or ["排队", "执行", "完成"])
        payload: dict[str, Any] = {
            "task_id": tid,
            "task_name": task_name,
            "steps": step_labels,
            "step_index": 0,
            "percent": 0,
            "message": "任务已排队…",
            "updated_at": self._now(),
        }
        self._save(tid, payload, event="init")
        return payload

    def update(
        self,
        task_id: str,
        *,
        step_index: int | None = None,
        message: str = "",
        percent: int | float | None = None,
    ) -> dict[str, Any]:
        tid = (task_id or "").strip()
        current = self.get(tid) or self.init(tid)
        steps = list(current.get("steps") or ["排队", "执行", "完成"])
        if step_index is not None:
            current["step_index"] = max(0, min(int(step_index), max(len(steps) - 1, 0)))
        if message:
            current["message"] = str(message)[:500]
        if percent is not None:
            current["percent"] = max(0.0, min(100.0, float(percent)))
        else:
            idx = int(current.get("step_index") or 0)
            current["percent"] = round(((idx + 1) / max(len(steps), 1)) * 100.0, 1)
            current["percent"] = min(100.0, current["percent"])
        current["updated_at"] = self._now()
        self._save(tid, current, event="update")
        return current

    def get(self, task_id: str) -> dict[str, Any] | None:
        tid = (task_id or "").strip()
        if not tid:
            return None
        # Redis backend
        if self._redis is not None:
            key = f"quant:task_progress:{tid}"
            raw = self._redis.get(key)
            if raw is not None:
                try:
                    data = json.loads(raw)
                    return data if isinstance(data, dict) else None
                except (json.JSONDecodeError, TypeError) as exc:
                    logger.warning("task_progress_store.redis.get failed: %s", exc)
        # Memory fallback
        if self._use_memory or tid in self._memory:
            return self._memory.get(tid)
        # File fallback
        path = self._path(tid)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("task_progress_store.get failed (%s): %s", path, exc)
            return None

    def _save(self, task_id: str, payload: dict[str, Any], event: str = "update") -> None:
        # Redis backend
        if self._redis is not None:
            key = f"quant:task_progress:{task_id}"
            try:
                self._redis.setex(key, 86400, json.dumps(payload, ensure_ascii=False))
                self._redis.publish(_REDIS_PROGRESS_CHANNEL, json.dumps({
                    "event": event,
                    "task_id": task_id,
                    "payload": payload,
                }, ensure_ascii=False))
            except Exception as exc:
                logger.warning("task_progress_store.redis.save failed: %s", exc)
        # File fallback
        path = self._path(task_id)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("task_progress_store.save failed (%s): %s", path, exc)
            self._use_memory = True
            self._memory[task_id] = payload

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _path(self, task_id: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in task_id)[:120]
        return self._root / f"{safe}.json"
