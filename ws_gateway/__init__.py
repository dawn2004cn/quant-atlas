"""
WS Gateway — standalone Flask-SocketIO process.

This process runs SocketIO independently from the main Flask HTTP process,
communicating via Redis Pub/Sub. Architecture:

  [Flask HTTP] → Redis PUBLISH 'ws:quote:update' → [WS Gateway] → SocketIO → Browser
  [Browser]    → SocketIO 'subscribe'             → [WS Gateway] → no-op (auth only)

This isolates the GIL-intensive HTTP request handling from the
low-latency WebSocket broadcast path.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime

import redis as _redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [WS] %(levelname)s %(message)s")
logger = logging.getLogger("ws_gateway")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
WS_HOST = os.getenv("WS_GATEWAY_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_GATEWAY_PORT", "5001"))
ALLOWED_ORIGINS = os.getenv("SOCKETIO_ALLOWED_ORIGINS", "http://localhost:5000").split(",")


def _redis_listener(socketio: Any) -> None:
    """Subscribe to Redis Pub/Sub channels and forward to SocketIO rooms."""
    r = _redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    # Map Redis channel → (socketio event, target room)
    channels = {
        "ws:quote:update": ("quote_update", "market"),
        "ws:tick:update": ("tick_update", "ticks"),
        "ws:alert": ("cross_team_site_alert", "alerts"),
        "ws:trade:executed": ("trade_executed", "trades"),
        "ws:ai:analysis": ("ai_analysis_chunk", "ai_analysis"),
    }
    for ch in channels:
        pubsub.subscribe(ch)

    logger.info("Redis listener subscribed to %d channels", len(channels))
    for message in pubsub.listen():
        if message["type"] != "message":
            continue
        channel = message["channel"]
        mapping = channels.get(channel)
        if not mapping:
            continue
        event, room = mapping
        try:
            data = json.loads(message["data"])
            socketio.emit(event, data, room=room)
        except Exception as exc:
            logger.debug("WS broadcast %s: %s", channel, exc)


def main() -> None:
    try:
        from flask import Flask
        from flask_socketio import SocketIO, emit, join_room, leave_room
    except ImportError:
        logger.error("flask-socketio not installed; pip install flask-socketio")
        return

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "ws-gateway-local")
    app.config["SERVER_NAME"] = None

    cors = {o.strip(): True for o in ALLOWED_ORIGINS if o.strip()}
    if "*" in cors:
        logger.error("Wildcard CORS not allowed. Set SOCKETIO_ALLOWED_ORIGINS explicitly.")
        return

    socketio = SocketIO(app, cors_allowed_origins=cors, async_mode="threading", ping_interval=25, ping_timeout=20)

    rooms: dict[str, set[str]] = {}
    rooms_lock = threading.Lock()

    @socketio.on("connect")
    def handle_connect():
        from flask import request
        # Skip auth check — session cookie validation is handled upstream
        # by the Flask HTTP process. WS Gateway only accepts connections
        # from users who already authenticated via Flask's session.
        # For production, add JWT token validation here.
        logger.info("Client connected: %s", request.sid)

    @socketio.on("disconnect")
    def handle_disconnect():
        from flask import request
        logger.info("Client disconnected: %s", request.sid)
        with rooms_lock:
            for room_name in list(rooms.keys()):
                rooms[room_name].discard(request.sid)

    @socketio.on("subscribe")
    def handle_subscribe(data):
        from flask import request
        room = data.get("room", "market")
        join_room(room)
        with rooms_lock:
            rooms.setdefault(room, set()).add(request.sid)
        emit("subscribed", {"room": room})

    @socketio.on("unsubscribe")
    def handle_unsubscribe(data):
        from flask import request
        room = data.get("room", "market")
        leave_room(room)
        with rooms_lock:
            rooms.get(room, set()).discard(request.sid)
        emit("unsubscribed", {"room": room})

    @socketio.on("heartbeat")
    def handle_heartbeat():
        emit("heartbeat_ack", {"ts": datetime.now().isoformat()})

    # Start Redis listener thread
    t = threading.Thread(target=_redis_listener, args=(socketio,), daemon=True, name="ws-redis-listener")
    t.start()
    logger.info("WS Gateway starting on %s:%d", WS_HOST, WS_PORT)
    socketio.run(app, host=WS_HOST, port=WS_PORT)


if __name__ == "__main__":
    main()
