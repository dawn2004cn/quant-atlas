"""Tick-level WebSocket stream bridge for institutional realtime feeds."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool, get_runtime_int

logger = get_logger(__name__)

_tick_thread: threading.Thread | None = None
_seq_counters: dict[str, int] = {}
_seq_lock = threading.Lock()


def _next_seq(symbol: str) -> int:
    sym = symbol.upper()
    with _seq_lock:
        _seq_counters[sym] = _seq_counters.get(sym, 0) + 1
        return _seq_counters[sym]


def broadcast_tick(
    symbol: str,
    *,
    price: float,
    bid: float | None = None,
    ask: float | None = None,
    volume: int = 0,
    source: str = "stream",
) -> int:
    """Emit tick_update to symbol room and global ticks room."""
    from app.infrastructure.realtime.websocket_adapter import broadcast_tick_update

    return broadcast_tick_update(
        symbol=symbol,
        price=price,
        bid=bid if bid is not None else price,
        ask=ask if ask is not None else price,
        volume=volume,
        seq=_next_seq(symbol),
        source=source,
    )


def _tick_symbols() -> list[str]:
    from app.bootstrap_components.realtime import _quote_symbols

    raw = get_runtime_int("WS_TICK_MAX_SYMBOLS", 20)
    return _quote_symbols()[: max(1, raw)]


def _tick_loop(app: Any, market_service: Any) -> None:
    from app.domain.enums import MarketCode
    from app.infrastructure.realtime.websocket_adapter import get_room_clients

    interval = max(1, get_runtime_int("WS_TICK_INTERVAL_SEC", 1))
    while True:
        try:
            with app.app_context():
                if not hasattr(app, "socketio"):
                    break
                if get_room_clients("ticks") == 0 and not _any_tick_room_active():
                    time.sleep(interval)
                    continue
                symbols = _tick_symbols()
                quotes = market_service.get_realtime_quotes(symbols, market=MarketCode.CN)
                for q in quotes or []:
                    sym = getattr(q, "code", None) or getattr(q, "symbol", "")
                    if not sym:
                        continue
                    price = float(getattr(q, "price", 0) or 0)
                    if price <= 0:
                        continue
                    vol = int(float(getattr(q, "volume", 0) or 0))
                    spread = max(price * 0.0001, 0.01)
                    broadcast_tick(
                        str(sym),
                        price=price,
                        bid=round(price - spread / 2, 4),
                        ask=round(price + spread / 2, 4),
                        volume=vol,
                        source="tick_loop",
                    )
        except Exception as exc:  # noqa: BLE001
            logger.debug("tick broadcast tick: %s", exc)
        time.sleep(interval)


def _any_tick_room_active() -> bool:
    from app.infrastructure.realtime.websocket_adapter import get_room_clients

    for sym in _tick_symbols():
        if get_room_clients(f"ticks:{sym.upper()}") > 0:
            return True
    return False


def start_tick_stream(app: Any, market_service: Any | None) -> bool:
    """Start background tick broadcaster when ENABLE_TICK_WS=1."""
    global _tick_thread
    if not get_runtime_bool("ENABLE_TICK_WS", False):
        return False
    if market_service is None:
        logger.warning("tick stream skipped: market_service unavailable")
        return False
    if _tick_thread is not None and _tick_thread.is_alive():
        return True
    _tick_thread = threading.Thread(
        target=_tick_loop,
        args=(app, market_service),
        name="tick-ws-broadcast",
        daemon=True,
    )
    _tick_thread.start()
    logger.info("Tick WebSocket broadcast thread started (interval=%ss)", get_runtime_int("WS_TICK_INTERVAL_SEC", 1))
    return True


def wire_event_bus_ticks() -> None:
    """Bridge MarketDataUpdatedEvent to tick broadcasts for subscribed symbols."""
    from app.core.event_bus import MarketDataUpdatedEvent, get_event_bus

    def _on_market(event: MarketDataUpdatedEvent) -> None:
        sym = (event.symbol or "").strip().upper()
        if not sym:
            return
        price = float(getattr(event, "price", 0) or 0)
        if price <= 0:
            return
        broadcast_tick(sym, price=price, volume=int(getattr(event, "volume", 0) or 0), source=event.source or "event_bus")

    bus = get_event_bus()
    bus.subscribe(MarketDataUpdatedEvent, _on_market)


def stream_status() -> dict[str, Any]:
    from app.infrastructure.realtime.websocket_adapter import get_room_clients

    symbols = _tick_symbols()
    return {
        "enabled": get_runtime_bool("ENABLE_TICK_WS", False),
        "interval_sec": get_runtime_int("WS_TICK_INTERVAL_SEC", 1),
        "max_symbols": get_runtime_int("WS_TICK_MAX_SYMBOLS", 20),
        "global_subscribers": get_room_clients("ticks"),
        "symbol_subscribers": {s: get_room_clients(f"ticks:{s.upper()}") for s in symbols[:10]},
        "timestamp": datetime.now().isoformat(),
    }
