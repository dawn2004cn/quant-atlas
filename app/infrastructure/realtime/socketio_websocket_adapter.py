from __future__ import annotations
"""WebSocketPort backed by Flask-SocketIO server rooms."""

from app.domain.ports.websocket_ports import Subscription, WebSocketPort
from app.infrastructure.realtime.websocket_adapter import get_room_clients


class SocketIOWebSocketAdapter(WebSocketPort):
    """Server-side SocketIO is always 'connected' when the extension is mounted."""

    def __init__(self) -> None:
        self._subscriptions: set[str] = set()

    def connect(self) -> bool:
        try:
            from flask import current_app

            return hasattr(current_app, "socketio")
        except Exception:
            return False

    def disconnect(self) -> None:
        self._subscriptions.clear()

    def subscribe(self, subscription: Subscription) -> bool:
        if not self.is_connected():
            return False
        for sym in subscription.symbols:
            self._subscriptions.add(str(sym).upper())
        return True

    def unsubscribe(self, subscription: Subscription) -> bool:
        for sym in subscription.symbols:
            self._subscriptions.discard(str(sym).upper())
        return True

    def is_connected(self) -> bool:
        return self.connect()

    def room_client_count(self) -> int:
        return get_room_clients("market")
