"""Realtime WebSocket status API for tick/quote streams."""

from __future__ import annotations

from flask import Blueprint
from flask_login import login_required

from app.core.registry import register_routes
from app.core.runtime_config import get_runtime, get_runtime_bool
from app.infrastructure.realtime.websocket_adapter import get_room_clients

from .common import ok_response
from .v1_context import ApiV1Context


@register_routes
def register_realtime_routes(blueprint: Blueprint, ctx: ApiV1Context | None = None) -> None:
    del ctx

    @blueprint.get("/realtime/status")
    @login_required
    def realtime_status():
        """SocketIO + tick stream health for institutional dashboards."""
        from app.modules.market_data.services.tick_stream_service import stream_status

        socketio_on = get_runtime_bool("ENABLE_SOCKETIO", False)
        tick_on = get_runtime_bool("ENABLE_TICK_WS", False)
        quote_on = get_runtime_bool("ENABLE_QUOTE_WS_BROADCAST", True)
        tick_info = stream_status()
        origins_ok = bool((get_runtime("SOCKETIO_ALLOWED_ORIGINS", "") or "").strip())
        return ok_response(
            data={
                "socketio_enabled": socketio_on,
                "origins_configured": origins_ok,
                "quote_broadcast": quote_on,
                "tick_stream": tick_on,
                "base_subscriptions": ["market", "alerts"],
                "rooms": {
                    "market": get_room_clients("market"),
                    "alerts": get_room_clients("alerts"),
                    "ticks": get_room_clients("ticks"),
                    "trades": get_room_clients("trades"),
                },
                "tick": tick_info,
            },
            ok=True,
            status="success",
        )

    @blueprint.get("/realtime/ticks/status")
    @login_required
    def tick_stream_status():
        """Tick-level subscriber counts and config."""
        from app.modules.market_data.services.tick_stream_service import stream_status

        return ok_response(data=stream_status(), ok=True, status="success")
