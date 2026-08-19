from __future__ import annotations

"""SocketIO init and optional quote broadcast loop."""

import threading
import time
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime, get_runtime_bool, get_runtime_int

logger = get_logger(__name__)

_broadcast_thread: threading.Thread | None = None


def _quote_symbols() -> list[str]:
    raw = (get_runtime("WS_QUOTE_SYMBOLS", "") or "").strip()
    if raw:
        return [s.strip().upper() for s in raw.split(",") if s.strip()]
    return ["600519", "000001", "000858", "601318", "300750"]


def _broadcast_loop(app: Any, market_service: Any) -> None:
    from app.domain.enums import MarketCode
    from app.infrastructure.realtime.smart_degrade_gateway import get_smart_degrade_gateway
    from app.infrastructure.realtime.websocket_adapter import broadcast_quote_update

    gateway = get_smart_degrade_gateway()
    interval = max(1, get_runtime_int("WS_QUOTE_INTERVAL_SEC", 5))
    try:
        from app.infrastructure.realtime.tdx_redis_quote_store import tdx_redis_feed_enabled
        from app.modules.market_data.services.tdx_realtime_feed_service import feed_interval_sec

        if tdx_redis_feed_enabled():
            interval = max(1, int(feed_interval_sec()))
    except Exception:
        pass
    while True:
        try:
            with app.app_context():
                if not hasattr(app, "socketio"):
                    break
                symbols = _quote_symbols()[:40]
                pulse_ctx = None
                try:
                    from flask import current_app

                    api_bundle = current_app.extensions.get("api_bundle")
                    if api_bundle is not None:
                        from app.presentation.api.v1_context import create_api_v1_context

                        pulse_ctx = create_api_v1_context(api_bundle)
                except Exception:
                    pulse_ctx = None

                topo = gateway.resolve(symbols, pulse_ctx=pulse_ctx)
                stream_syms = (
                    symbols
                    if topo.mode.value == "stream"
                    else [s for s in symbols if gateway.should_stream_now(s)]
                )
                batch_syms = gateway.batch_symbol_list(symbols) if gateway.should_batch_now() else []
                fetch_syms = list(dict.fromkeys(stream_syms + batch_syms))
                if not fetch_syms:
                    fetch_syms = stream_syms or symbols[:5]
                quotes = getattr(market_service, "get_realtime_quotes", lambda *a, **kw: None)(fetch_syms, market=MarketCode.CN)
                if quotes is None:
                    quotes = []
                from app.core.event_bus import MarketDataUpdatedEvent, get_event_bus

                bus = get_event_bus()
                for q in quotes or []:
                    sym = getattr(q, "code", None) or getattr(q, "symbol", "")
                    if not sym:
                        continue
                    broadcast_quote_update(
                        str(sym),
                        float(getattr(q, "price", 0) or 0),
                        float(getattr(q, "change_amount", 0) or 0),
                        float(getattr(q, "change_pct", 0) or 0),
                        int(float(getattr(q, "volume", 0) or 0)),
                    )
                    bus.publish(
                        MarketDataUpdatedEvent(
                            source="quote_broadcast",
                            symbol=str(sym),
                            market=MarketCode.CN.value,
                        )
                    )
        except Exception as exc:
            logger.debug("quote broadcast tick: %s", exc)
        time.sleep(interval)


def init_realtime(app: Any, settings: Any, market_service: Any | None = None) -> dict[str, Any]:
    """Mount Flask-SocketIO (or WS Gateway Redis bridge) and start quote broadcaster."""
    global _broadcast_thread
    meta: dict[str, Any] = {"socketio": False, "quote_broadcast": False, "gateway_mode": False}
    if not get_runtime_bool("ENABLE_SOCKETIO", False):
        return meta

    is_gateway = get_runtime("WS_GATEWAY_MODE", "0") in ("1", "true")
    meta["gateway_mode"] = is_gateway

    if is_gateway:
        logger.info("WS_GATEWAY_MODE=1 — SocketIO runs in separate process; Redis Pub/Sub bridge active")
        meta["socketio"] = True
    else:
        try:
            from flask_socketio import SocketIO
        except ImportError:
            logger.warning("flask-socketio not installed; set ENABLE_SOCKETIO=0 or pip install flask-socketio")
            return meta

        from app.core.event_bus import enable_websocket_broadcast
        from app.infrastructure.realtime.websocket_adapter import broadcast_to_room, init_socketio

        allowed_origins = get_runtime("SOCKETIO_ALLOWED_ORIGINS", "")
        cors_map = {}
        for origin in (o.strip() for o in allowed_origins.split(",") if o.strip()):
            cors_map[origin] = True

        if not cors_map:
            logger.error("ENABLE_SOCKETIO=1 but SOCKETIO_ALLOWED_ORIGINS not configured. SocketIO disabled.")
            return meta
        if "*" in cors_map:
            logger.error("SOCKETIO_ALLOWED_ORIGINS must not include '*' (wildcard). SocketIO disabled.")
            return meta

        socketio = SocketIO(app, cors_allowed_origins=cors_map, async_mode="threading")
        app.socketio = socketio
        init_socketio(socketio)
        enable_websocket_broadcast(broadcast_to_room)
        meta["socketio"] = True
        logger.info("Flask-SocketIO initialized")

        _init_browser_node_adapter(socketio)
        _init_canvas_event_bridge()
        _init_perception_bridge()

    if get_runtime_bool("ENABLE_QUOTE_WS_BROADCAST", True) and market_service is not None:
        if _broadcast_thread is None or not _broadcast_thread.is_alive():
            _broadcast_thread = threading.Thread(
                target=_broadcast_loop,
                args=(app, market_service),
                name="quote-ws-broadcast",
                daemon=True,
            )
            _broadcast_thread.start()
            meta["quote_broadcast"] = True
            logger.info("Quote WebSocket broadcast thread started")

    if market_service is not None:
        try:
            from app.modules.market_data.services.tick_stream_service import (
                start_tick_stream,
                wire_event_bus_ticks,
            )

            meta["tick_stream"] = start_tick_stream(app, market_service)
            wire_event_bus_ticks()
        except Exception as exc:
            logger.debug("tick stream init skipped: %s", exc)
            meta["tick_stream"] = False

    return meta


def _init_browser_node_adapter(socketio: Any) -> None:
    from app.core.mesh.browser_node_adapter import BrowserNodeAdapter, configure_browser_node_adapter

    def _emit_func(event: str, data: dict, *, room: str | None = None) -> None:
        socketio.emit(event, data, room=room)

    adapter = BrowserNodeAdapter(emit_func=_emit_func)
    configure_browser_node_adapter(adapter)
    logger.info("BrowserNodeAdapter initialized (9.0 Fabric)")


def _init_canvas_event_bridge() -> None:
    from app.modules.system.services.canvas_event_bridge import get_canvas_event_bridge

    get_canvas_event_bridge()
    logger.info("CanvasEventBridge initialized (9.0 live event streaming)")


def _init_perception_bridge() -> None:
    """Initialize Collective Perception Layer for cross-node neural resonance (10.0)."""
    from app.core.mesh.perception_bridge import start_perception_bridge
    from app.core.runtime_config import get_runtime, get_runtime_bool

    if not get_runtime_bool("PERCEPTION_ENABLED", False):
        logger.debug("perception bridge disabled (PERCEPTION_ENABLED=false)")
        return

    node_id = (get_runtime("MESH_NODE_ID", "cn-gateway-1") or "cn-gateway-1").strip()
    region = (get_runtime("MESH_REGION", "CN") or "CN").strip().upper()

    redis_client = None
    redis_url = get_runtime("MESH_REDIS_URL", "") or get_runtime("TASK_MESSAGE_REDIS_URL", "")
    if redis_url:
        try:
            import redis
            redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            redis_client.ping()
        except Exception as exc:
            logger.debug("perception redis unavailable: %s", exc)
            redis_client = None

    layer = start_perception_bridge(
        node_id=node_id,
        region=region,
        redis_client=redis_client,
    )
    if layer is not None:
        logger.info("PerceptionLayer active node=%s region=%s", node_id, region)
