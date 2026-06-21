"""API v1: Switcher telemetry endpoint for Flask/SPA grayscale tracking."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request

from app.core.registry import register_routes

logger = logging.getLogger(__name__)

# ── IP-based rate limiter (in-memory, per-process) ──────────────────────────

_RATE_LIMIT = 10  # requests per second per IP
_RATE_WINDOW = 1.0  # seconds

_ip_counts: dict[str, list[float]] = defaultdict(list)
_rate_lock = threading.Lock()


def _is_rate_limited(ip: str) -> bool:
    """Return True if the IP has exceeded 10 requests per second."""
    now = time.monotonic()
    with _rate_lock:
        timestamps = _ip_counts[ip]
        # Prune timestamps older than the window
        _ip_counts[ip] = timestamps = [t for t in timestamps if now - t < _RATE_WINDOW]
        if len(timestamps) >= _RATE_LIMIT:
            return True
        timestamps.append(now)
        return False


# ── JSONL writer ────────────────────────────────────────────────────────────

_TELEMETRY_DIR = Path(os.environ.get("INSTANCE_PATH", "instance"))
_TELEMETRY_FILE = _TELEMETRY_DIR / "telemetry.jsonl"
_write_lock = threading.Lock()

_VALID_EVENTS = frozenset({"switch_to_spa", "back_to_classic"})


def _append_event(event: str, page: str, user_id: str | None) -> None:
    """Append a telemetry event to the JSONL file."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "page": page,
        "user_id": user_id,
    }
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with _write_lock:
        _TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        with open(_TELEMETRY_FILE, "a", encoding="utf-8") as f:
            f.write(line)


# ── Route registration ──────────────────────────────────────────────────────


@register_routes(name="telemetry", context="system", description="Switcher telemetry for Flask→SPA migration")
def register_telemetry_routes(blueprint: Blueprint, ctx) -> None:  # type: ignore[typeddict-item]
    """Register switcher telemetry endpoint."""

    @blueprint.route("/telemetry/switcher", methods=["POST"])
    def telemetry_switcher():
        """Accept switcher telemetry events.

        Body: {"event": "switch_to_spa" | "back_to_classic", "page": str, "user_id": str|null}
        Returns 204 No Content on success, 400 on validation error, 429 on rate limit.
        """
        ip = request.remote_addr or "unknown"
        if _is_rate_limited(ip):
            return jsonify({"success": False, "error": "rate_limited", "data": None, "meta": {"code": "rate_limited"}}), 429

        body = request.get_json(silent=True) or {}
        event = body.get("event")
        page = body.get("page")
        user_id = body.get("user_id")

        # Validate event type
        if event not in _VALID_EVENTS:
            return jsonify({"success": False, "error": "invalid_event", "data": None, "meta": {"code": "invalid_event", "valid_events": sorted(_VALID_EVENTS)}}), 400

        # Validate page
        if not page or not isinstance(page, str) or not page.strip():
            return jsonify({"success": False, "error": "page_required", "data": None, "meta": {"code": "page_required"}}), 400

        # Write to JSONL
        try:
            _append_event(event, page.strip(), user_id)
        except Exception:
            logger.exception("Failed to write telemetry event")
            # Fire-and-forget: still return 204 so client isn't blocked

        return "", 204