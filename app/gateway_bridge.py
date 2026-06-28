import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)
GATEWAY_PORT = 9091
PING_INTERVAL = 30
@dataclass
class GatewayClient:
    websocket: Any
    symbols: set[str] = field(default_factory=set)
class GatewayBridge:
    def __init__(self, host='0.0.0.0', port=GATEWAY_PORT):  # internal WebSocket gateway, intentional all-interfaces bind
        self.host = host; self.port = port
        self._clients = set(); self._lock = asyncio.Lock()
        self._server = None; self._running = False
    async def start(self):
        import websockets
        self._running = True
        self._server = await websockets.serve(self._handle_connection, self.host, self.port, ping_interval=PING_INTERVAL, ping_timeout=10)
        logger.info('[gateway_bridge] serving ws://%s:%d', self.host, self.port)
    async def stop(self):
        self._running = False
        if self._server: self._server.close(); await self._server.wait_closed()
        async with self._lock:
            for c in list(self._clients): await self._close_client(c)
            self._clients.clear()
        logger.info('[gateway_bridge] stopped')
    async def broadcast_quote(self, symbol, quote):
        payload = {'type':'quote','symbol':symbol,'payload':quote,'ts':int(time.time()*1000)}
        data = json.dumps(payload, ensure_ascii=False, default=str)
        sent = 0
        async with self._lock:
            for c in list(self._clients):
                if symbol not in c.symbols: continue
                try: await c.websocket.send(data); sent += 1
                except Exception: self._clients.discard(c)
        return sent
    def broadcast_quote_sync(self, symbol, quote):
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = None
        if loop and loop.is_running():
            f = asyncio.run_coroutine_threadsafe(self.broadcast_quote(symbol,quote), loop)
            try: return f.result(timeout=5)
            except Exception: return 0
        else:
            try: return asyncio.run(self.broadcast_quote(symbol, quote))
            except Exception: return 0
    async def get_client_count(self):
        async with self._lock: return len(self._clients)
    async def _handle_connection(self, ws):
        c = GatewayClient(websocket=ws)
        async with self._lock: self._clients.add(c)
        try:
            async for raw in ws: await self._handle_message(c, raw)
        except Exception: pass
        finally:
            async with self._lock: self._clients.discard(c)
    async def _handle_message(self, c, raw):
        try: msg = json.loads(raw)
        except Exception: return
        t = msg.get('type',''); p = msg.get('payload',{})
        if t == 'subscribe':
            syms = p.get('symbols',[]) if isinstance(p,dict) else []
            c.symbols.update(s.upper() for s in syms)
            ack = json.dumps({'type':'subscribed','symbols':list(syms),'ts':int(time.time()*1000)})
            await self._safe_send(c.websocket, ack)
        elif t == 'unsubscribe':
            for s in p.get('symbols',[]): c.symbols.discard(s.upper())
        elif t == 'ping':
            await self._safe_send(c.websocket, json.dumps({'type':'pong'}))
    async def _safe_send(self, ws, data):
        try: await ws.send(data)
        except Exception: pass
    async def _close_client(self, c):
        try: await c.websocket.close()
        except Exception: pass
_gateway_instance = None
_gateway_thread = None
def launch_gateway(host='0.0.0.0', port=GATEWAY_PORT):  # internal WebSocket gateway, intentional all-interfaces bind
    global _gateway_instance, _gateway_thread
    if _gateway_instance and _gateway_thread:
        logger.info('[gateway_bridge] already running')
        return _gateway_instance
    bridge = GatewayBridge(host=host, port=port)
    def _run():
        try: asyncio.run(bridge.start())
        except Exception as e: logger.warning('[gateway_bridge] exit: %s', e)
    t = threading.Thread(target=_run, daemon=True, name='ws-gateway')
    t.start()
    _gateway_instance = bridge; _gateway_thread = t
    logger.info('[gateway_bridge] launched ws://%s:%d', host, port)
    return bridge
def get_gateway(): return _gateway_instance
def stop_gateway():
    global _gateway_instance, _gateway_thread
    if _gateway_instance:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_gateway_instance.stop())
            loop.close()
        except Exception: pass
    _gateway_instance = None; _gateway_thread = None
