from __future__ import annotations
"""Celery reliability helpers: retry baseline + idempotent enqueue."""


import hashlib
import json
import threading
import time
from collections.abc import Mapping, Sequence
from typing import Any

from ...core.runtime_config import get_runtime, get_runtime_int

import logging
logger = logging.getLogger(__name__)
_MEMORY_KEYS: dict[str, float] = {}
_MEMORY_LOCK = threading.Lock()


def _default_redis_url() -> str:
    return (
        (get_runtime("CELERY_IDEMPOTENCY_REDIS_URL", "") or "").strip()
        or (get_runtime("TASK_MESSAGE_REDIS_URL", "") or "").strip()
        or (get_runtime("CELERY_BROKER_URL", "") or "").strip()
    )


def _stable_obj(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _stable_obj(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_stable_obj(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def build_idempotency_task_id(
    *,
    task_name: str,
    args: Sequence[Any] | None = None,
    kwargs: Mapping[str, Any] | None = None,
    bucket_seconds: int = 0,
) -> str:
    bucket = 0
    if int(bucket_seconds or 0) > 0:
        now = int(time.time())
        b = int(bucket_seconds)
        bucket = now - (now % b)
    payload = {
        "task": str(task_name or ""),
        "args": _stable_obj(list(args or [])),
        "kwargs": _stable_obj(dict(kwargs or {})),
        "bucket": bucket,
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"idem-{digest[:40]}"


def _memory_claim(key: str, ttl_seconds: int) -> bool:
    now = time.time()
    exp = now + max(1, int(ttl_seconds))
    with _MEMORY_LOCK:
        dead = [k for k, t in _MEMORY_KEYS.items() if t <= now]
        for k in dead:
            _MEMORY_KEYS.pop(k, None)
        if key in _MEMORY_KEYS:
            return False
        _MEMORY_KEYS[key] = exp
        return True


def _memory_release(key: str) -> None:
    with _MEMORY_LOCK:
        _MEMORY_KEYS.pop(key, None)


def claim_idempotency_key(key: str, ttl_seconds: int) -> bool:
    redis_url = _default_redis_url()
    if redis_url:
        try:
            import redis

            cli = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1.5, socket_timeout=1.5)
            return bool(cli.set(name=key, value=str(int(time.time())), nx=True, ex=max(1, int(ttl_seconds))))
        except Exception as e:
            logger.warning("celery_reliability.py.claim_idempotency_key: %s", e)
    return _memory_claim(key, ttl_seconds)


def release_idempotency_key(key: str) -> None:
    redis_url = _default_redis_url()
    if redis_url:
        try:
            import redis

            cli = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1.5, socket_timeout=1.5)
            cli.delete(key)
            return
        except Exception as e:
            logger.warning("celery_reliability.py.release_idempotency_key: %s", e)
    _memory_release(key)


def enqueue_task_idempotent(
    task: Any,
    *,
    task_name: str,
    args: Sequence[Any] | None = None,
    kwargs: Mapping[str, Any] | None = None,
    bucket_seconds: int | None = None,
    ttl_seconds: int | None = None,
) -> tuple[Any | None, str, bool]:
    if not callable(getattr(task, "apply_async", None)):
        raise TypeError(f"Task {task_name!r} is not a Celery task (no apply_async): {type(task)}")
    bucket = int(bucket_seconds if bucket_seconds is not None else get_runtime_int("CELERY_IDEMPOTENCY_BUCKET_SECONDS", 60))
    ttl = int(ttl_seconds if ttl_seconds is not None else get_runtime_int("CELERY_IDEMPOTENCY_TTL_SECONDS", 600))
    task_id = build_idempotency_task_id(task_name=task_name, args=args, kwargs=kwargs, bucket_seconds=bucket)
    idem_key = f"quant:celery:idem:{task_name}:{task_id}"
    if not claim_idempotency_key(idem_key, ttl):
        return None, task_id, False
    try:
        ar = task.apply_async(args=list(args or []), kwargs=dict(kwargs or {}), task_id=task_id)
        return ar, task_id, True
    except Exception:
        release_idempotency_key(idem_key)
        raise

