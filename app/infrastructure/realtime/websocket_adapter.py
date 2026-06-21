from __future__ import annotations
"""Flask-SocketIO real-time market data adapter.

Supports two modes:
1. Direct SocketIO (default) — broadcasts via Flask-SocketIO in-process.
2. WS Gateway mode (WG_GATEWAY_MODE=1) — publishes to Redis Pub/Sub,
   consumed by the standalone ws_gateway/ process.
"""



import json
import os
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from flask import request
from flask_socketio import emit, join_room, leave_room


from app.core.logger import get_logger

logger = get_logger(__name__)

_rooms: Dict[str, set[str]] = {}
_room_lock = threading.Lock()

_REDIS_PUB: Any | None = None

def _get_redis_pub() -> Any | None:
    global _REDIS_PUB
    if _REDIS_PUB is None and os.getenv("WS_GATEWAY_MODE", "0") in ("1", "true"):
        try:
            import redis as _r
            _REDIS_PUB = _r.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        except Exception:
            _REDIS_PUB = False
    return _REDIS_PUB if _REDIS_PUB else None


def _publish_to_gateway(channel: str, data: dict[str, Any]) -> None:
    pub = _get_redis_pub()
    if pub:
        try:
            pub.publish(channel, json.dumps(data, ensure_ascii=False, default=str))
        except Exception:
            logger.debug("Redis publish to gateway failed channel=%s", channel, exc_info=True)


def init_socketio(socketio):
    """Initialize SocketIO event handlers.

    Call this after Flask-SocketIO is configured.
    """
    @socketio.on('connect')
    def handle_connect():
        from flask_login import current_user
        if not current_user or not current_user.is_authenticated:
            logger.warning("WebSocket connect rejected: no auth session %s", request.sid)
            return False
        logger.info(f"Client connected: {request.sid}")
        _register_browser_node(request.sid)
        emit('connected', {'status': 'ok'})

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f"Client disconnected: {request.sid}")
        _unregister_browser_node(request.sid)
        with _room_lock:
            for room in list(_rooms.keys()):
                if request.sid in _rooms.get(room, set()):
                    leave_room(room)

    @socketio.on('subscribe')
    def handle_subscribe(data):
        """Subscribe to symbol updates."""
        symbols = data.get('symbols', [])
        room = data.get('room', 'market')
        
        with _room_lock:
            if room not in _rooms:
                _rooms[room] = set()
            _rooms[room].add(request.sid)
        
        join_room(room)
        _browser_subscribe(request.sid, room)
        logger.info(f"Client {request.sid} subscribed to {symbols} in {room}")
        emit('subscribed', {'room': room, 'symbols': symbols})

    @socketio.on('subscribe_ticks')
    def handle_subscribe_ticks(data):
        """Subscribe to tick-level updates for symbols (room ticks:{SYMBOL})."""
        symbols = [str(s).strip().upper() for s in (data.get('symbols') or []) if str(s).strip()]
        with _room_lock:
            if 'ticks' not in _rooms:
                _rooms['ticks'] = set()
            _rooms['ticks'].add(request.sid)
        join_room('ticks')
        _browser_subscribe(request.sid, 'ticks')
        joined: list[str] = []
        for sym in symbols:
            room = f'ticks:{sym}'
            with _room_lock:
                if room not in _rooms:
                    _rooms[room] = set()
                _rooms[room].add(request.sid)
            join_room(room)
            _browser_subscribe(request.sid, room)
            joined.append(sym)
        logger.info("Client %s subscribed to ticks %s", request.sid, joined)
        emit('ticks_subscribed', {'symbols': joined, 'room': 'ticks'})

    @socketio.on('unsubscribe_ticks')
    def handle_unsubscribe_ticks(data):
        """Leave tick rooms."""
        symbols = [str(s).strip().upper() for s in (data.get('symbols') or []) if str(s).strip()]
        for sym in symbols:
            room = f'ticks:{sym}'
            with _room_lock:
                if room in _rooms:
                    _rooms[room].discard(request.sid)
            leave_room(room)
            _browser_unsubscribe(request.sid, room)
        with _room_lock:
            if 'ticks' in _rooms:
                _rooms['ticks'].discard(request.sid)
        leave_room('ticks')
        _browser_unsubscribe(request.sid, 'ticks')
        emit('ticks_unsubscribed', {'symbols': symbols})

    @socketio.on('unsubscribe')
    def handle_unsubscribe(data):
        """Unsubscribe from symbol updates."""
        room = data.get('room', 'market')
        
        with _room_lock:
            if room in _rooms:
                _rooms[room].discard(request.sid)
        
        leave_room(room)
        _browser_unsubscribe(request.sid, room)
        emit('unsubscribed', {'room': room})

    @socketio.on('heartbeat')
    def handle_heartbeat(data=None):
        """Browser heartbeat — keeps mesh node alive."""
        _browser_heartbeat(request.sid)
        emit('heartbeat_ack', {'ts': datetime.now().isoformat()})


def broadcast_to_room(room: str, event: str, data: Any) -> int:
    """Broadcast message to all clients in a room.

    In WS_GATEWAY_MODE, publishes to Redis Pub/Sub channel ``ws:{event}``.
    Otherwise uses in-process Flask-SocketIO.
    """
    _publish_to_gateway(f"ws:{event}", {"room": room, "event": event, "data": data, "ts": datetime.now().isoformat()})
    try:
        from flask import current_app
        if hasattr(current_app, 'socketio'):
            current_app.socketio.emit(event, data, room=room)
            with _room_lock:
                count = len(_rooms.get(room, set()))
            logger.debug(f"Broadcast {event} to {count} clients in {room}")
            return count
    except Exception as e:
        logger.warning(f"Broadcast failed: {e}")
    return 0


def broadcast_quote_update(symbol: str, price: float, change: float, 
                           change_pct: float, volume: int) -> int:
    """Broadcast a quote update to global market room AND per-symbol room."""
    from datetime import datetime
    data = {
        'symbol': symbol,
        'price': price,
        'change': change,
        'change_pct': change_pct,
        'volume': volume,
        'timestamp': datetime.now().isoformat()
    }
    n1 = broadcast_to_room('market', 'quote_update', data)
    sym_room = f'market:{str(symbol).upper()}'
    n2 = broadcast_to_room(sym_room, 'quote_update', data)
    return max(n1, n2)


def broadcast_tick_update(
    symbol: str,
    price: float,
    *,
    bid: float,
    ask: float,
    volume: int = 0,
    seq: int = 0,
    source: str = "stream",
) -> int:
    """Broadcast a tick-level update to ticks:{symbol} and global ticks room."""
    data = {
        'symbol': str(symbol).upper(),
        'price': price,
        'bid': bid,
        'ask': ask,
        'volume': volume,
        'seq': seq,
        'source': source,
        'timestamp': datetime.now().isoformat(),
    }
    sym_room = f"ticks:{str(symbol).upper()}"
    n1 = broadcast_to_room(sym_room, 'tick_update', data)
    n2 = broadcast_to_room('ticks', 'tick_update', data)
    return max(n1, n2)


def broadcast_cross_team_alert(alert: dict[str, Any]) -> int:
    """Broadcast a cross-team site consensus alert to the alerts room."""
    data = {
        **alert,
        "timestamp": datetime.now().isoformat(),
    }
    return broadcast_to_room("alerts", "cross_team_site_alert", data)


def broadcast_ai_analysis_chunk(symbol: str, market: str, chunk: dict[str, Any]) -> int:
    """Mirror SSE analyze_stream chunks to Socket.IO room ``ai_analysis``."""
    data = {
        "symbol": symbol,
        "market": market,
        "chunk": chunk,
        "timestamp": datetime.now().isoformat(),
    }
    return broadcast_to_room("ai_analysis", "ai_analysis_chunk", data)


def broadcast_trade_executed(user_id: str, symbol: str, action: str, 
                             quantity: float, price: float) -> int:
    """Broadcast a trade execution to relevant clients."""
    data = {
        'user_id': user_id,
        'symbol': symbol,
        'action': action,
        'quantity': quantity,
        'price': price,
        'timestamp': datetime.now().isoformat()
    }
    return broadcast_to_room('trades', 'trade_executed', data)


def get_room_clients(room: str) -> int:
    """Get count of clients in a room."""
    with _room_lock:
        return len(_rooms.get(room, set()))


def _register_browser_node(sid: str) -> None:
    from app.core.mesh.browser_node_adapter import get_browser_node_adapter
    adapter = get_browser_node_adapter()
    if adapter is not None:
        try:
            from flask_login import current_user
            uid = current_user.id if current_user and current_user.is_authenticated else None
        except Exception:
            uid = None
        adapter.register_browser(sid=sid, user_id=uid)


def _unregister_browser_node(sid: str) -> None:
    from app.core.mesh.browser_node_adapter import get_browser_node_adapter
    adapter = get_browser_node_adapter()
    if adapter is not None:
        adapter.unregister_browser(sid)


def _browser_heartbeat(sid: str) -> None:
    from app.core.mesh.browser_node_adapter import get_browser_node_adapter
    adapter = get_browser_node_adapter()
    if adapter is not None:
        adapter.heartbeat(sid)


def _browser_subscribe(sid: str, channel: str) -> None:
    from app.core.mesh.browser_node_adapter import get_browser_node_adapter
    adapter = get_browser_node_adapter()
    if adapter is not None:
        adapter.subscribe(sid, channel)


def _browser_unsubscribe(sid: str, channel: str) -> None:
    from app.core.mesh.browser_node_adapter import get_browser_node_adapter
    adapter = get_browser_node_adapter()
    if adapter is not None:
        adapter.unsubscribe(sid, channel)


__all__ = [
    "init_socketio",
    "broadcast_to_room",
    "broadcast_quote_update",
    "broadcast_tick_update",
    "broadcast_cross_team_alert",
    "broadcast_ai_analysis_chunk",
    "broadcast_trade_executed",
    "get_room_clients",
]