"""
SSE progress streaming for Qlib backtests and RD-Agent factor loops.

Architecture::

    Factor Loop ──(progress callback)──→ Redis PubSub 'sse:qlib:progress:{run_id}'
                                              │
    Browser ←── SSE GET /api/v1/qlib/progress/<run_id>  ←── Redis SUBSCRIBE

Usage (backend)::

    from app.infrastructure.realtime.sse_progress import publish_progress

    def _on_progress(pct: int, msg: str) -> None:
        publish_progress("run-123", pct, msg)

    run_factor_mining_loop(params, progress=_on_progress)

Usage (frontend)::

    const evtSource = new EventSource(`/api/v1/qlib/progress/${runId}`);
    evtSource.onmessage = (e) => {
        const { pct, message } = JSON.parse(e.data);
        updateProgressBar(pct, message);
    };
"""

from __future__ import annotations

import json
import os
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

_REDIS_CHANNEL_PREFIX = "sse:qlib:progress:"


def _redis_client() -> Any:
    try:
        from redis import Redis
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return Redis.from_url(url, decode_responses=True)
    except Exception:
        return None


def publish_progress(run_id: str, pct: int, message: str, meta: dict[str, Any] | None = None) -> None:
    """Publish a progress update to Redis PubSub.

    Called from progress callbacks during long-running qlib/rdagent tasks.
    The SSE endpoint subscribes to this channel and forwards to the browser.
    """
    client = _redis_client()
    if client is None:
        return
    try:
        payload = json.dumps({
            "pct": min(100, max(0, pct)),
            "message": (message or "")[:500],
            "meta": meta or {},
        }, ensure_ascii=False, default=str)
        client.publish(f"{_REDIS_CHANNEL_PREFIX}{run_id}", payload)
    except Exception as exc:
        logger.debug("publish_progress failed: %s", exc)
