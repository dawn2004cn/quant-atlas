"""Injectable broker order sessions for IBKR / CTP live placement."""

from __future__ import annotations

import time
from typing import Any, Protocol

from app.core.logger import get_logger
from app.domain.trading.contracts import OrderRequest, Position

logger = get_logger(__name__)


class BrokerOrderSession(Protocol):
    """Minimal session used by adapters (connect → place → positions)."""

    def connect(self) -> dict[str, Any]: ...

    def place_order(self, request: OrderRequest) -> str: ...

    def list_positions(self) -> list[Position]: ...

    def disconnect(self) -> None: ...


class FakeBrokerSession:
    """In-process session for tests / probe (never talks to a broker)."""

    def __init__(self, *, prefix: str = "IBKR_TWS") -> None:
        self.prefix = prefix
        self.connected = False
        self.orders: list[dict[str, Any]] = []

    def connect(self) -> dict[str, Any]:
        self.connected = True
        return {"ok": True, "mode": "fake", "prefix": self.prefix}

    def place_order(self, request: OrderRequest) -> str:
        if not self.connected:
            self.connect()
        oid = f"{self.prefix}_{request.symbol}_{int(time.time())}_{len(self.orders) + 1}"
        self.orders.append(
            {
                "order_id": oid,
                "symbol": request.symbol,
                "side": request.side,
                "quantity": float(request.quantity),
            }
        )
        return oid

    def list_positions(self) -> list[Position]:
        return []

    def disconnect(self) -> None:
        self.connected = False


class IbInsyncSession:
    """Interactive Brokers session via optional ``ib_insync``."""

    def __init__(self, *, host: str, port: int, client_id: int) -> None:
        self.host = host
        self.port = int(port)
        self.client_id = int(client_id)
        self._ib: Any = None

    def connect(self) -> dict[str, Any]:
        try:
            from ib_insync import IB
        except ImportError as exc:
            raise RuntimeError("ibkr_ib_insync_missing") from exc
        ib = IB()
        ib.connect(self.host, self.port, clientId=self.client_id, timeout=8)
        self._ib = ib
        accounts = []
        try:
            accounts = list(ib.managedAccounts() or [])
        except Exception:
            logger.warning("ib_insync managedAccounts failed", exc_info=True)
        logger.info("IBKR ib_insync connected host=%s:%s accounts=%s", self.host, self.port, accounts)
        return {"ok": True, "mode": "ib_insync", "accounts": accounts}

    def place_order(self, request: OrderRequest) -> str:
        if self._ib is None:
            self.connect()
        from ib_insync import Future, LimitOrder, MarketOrder, Stock

        contract = _ibkr_contract(request, Stock=Stock, Future=Future)
        action = "BUY" if str(request.side).lower() == "buy" else "SELL"
        qty: float | int = (
            int(request.quantity)
            if float(request.quantity).is_integer()
            else float(request.quantity)
        )
        if str(request.order_type).lower() == "limit" and request.price is not None:
            order = LimitOrder(action, qty, float(request.price))
        else:
            order = MarketOrder(action, qty)
        trade = self._ib.placeOrder(contract, order)
        oid = str(getattr(getattr(trade, "order", None), "orderId", "") or "")
        if not oid:
            oid = f"IBKR_TWS_{request.symbol}_{int(time.time())}"
        return oid

    def list_positions(self) -> list[Position]:
        if self._ib is None:
            return []
        out: list[Position] = []
        try:
            for pos in self._ib.positions() or []:
                contract = getattr(pos, "contract", None)
                symbol = str(getattr(contract, "symbol", None) or getattr(contract, "localSymbol", "") or "")
                out.append(
                    Position(
                        symbol=symbol,
                        market="US",
                        quantity=float(getattr(pos, "position", 0) or 0),
                        avg_price=float(getattr(pos, "avgCost", 0) or 0),
                    )
                )
        except Exception:
            logger.warning("ib_insync positions failed", exc_info=True)
        return out

    def disconnect(self) -> None:
        if self._ib is None:
            return
        try:
            self._ib.disconnect()
        except Exception:
            logger.warning("ib_insync disconnect failed", exc_info=True)
        self._ib = None


class CtpTraderSession:
    """CTP session wrapping an injected trader with ``ReqOrderInsert``.

    Full openctp/vnpy login is environment-specific; inject a trader (or FakeBrokerSession)
    rather than embedding a hard-coded front-end handshake here.
    """

    def __init__(self, trader: Any, *, broker_id: str = "", user_id: str = "") -> None:
        self._trader = trader
        self.broker_id = broker_id
        self.user_id = user_id
        self._req_id = 0
        self.connected = False

    def connect(self) -> dict[str, Any]:
        connect = getattr(self._trader, "connect", None) or getattr(self._trader, "Connect", None)
        if callable(connect):
            connect()
        self.connected = True
        return {"ok": True, "mode": "ctp_trader", "broker_id_set": bool(self.broker_id)}

    def place_order(self, request: OrderRequest) -> str:
        if not self.connected:
            self.connect()
        insert = getattr(self._trader, "ReqOrderInsert", None) or getattr(
            self._trader, "req_order_insert", None
        )
        if not callable(insert):
            raise RuntimeError("ctp_trader_missing_ReqOrderInsert")
        self._req_id += 1
        payload = {
            "InstrumentID": request.symbol,
            "Direction": "0" if str(request.side).lower() == "buy" else "1",
            "LimitPrice": float(request.price or 0.0),
            "VolumeTotalOriginal": int(request.quantity),
            "OrderPriceType": "2" if str(request.order_type).lower() == "limit" else "1",
            "BrokerID": self.broker_id,
            "UserID": self.user_id,
        }
        insert(payload, self._req_id)
        return f"CTP_TD_{request.symbol}_{self._req_id}"

    def list_positions(self) -> list[Position]:
        return []

    def disconnect(self) -> None:
        disc = getattr(self._trader, "disconnect", None) or getattr(self._trader, "Release", None)
        if callable(disc):
            try:
                disc()
            except Exception:
                logger.warning("ctp trader disconnect failed", exc_info=True)
        self.connected = False


def _ibkr_contract(request: OrderRequest, *, Stock: Any, Future: Any) -> Any:
    symbol = str(request.symbol or "").strip()
    market = str(request.market or "US").upper()
    ticker = symbol.split(".")[0]
    if market in {"FUT", "FUTURES"} or _looks_like_future(symbol):
        fut = Future(ticker)
        fut.localSymbol = symbol
        fut.exchange = "SMART"
        return fut
    currency = "USD"
    exchange = "SMART"
    if market == "HK" or symbol.upper().endswith(".HK"):
        currency = "HKD"
        exchange = "SEHK"
    return Stock(ticker, exchange, currency)


def _looks_like_future(symbol: str) -> bool:
    s = symbol.upper()
    return s[:2] in {"IF", "IH", "IC", "IM", "TS", "TF", "T "} or any(
        ch.isdigit() for ch in s[-4:]
    ) and s[:2].isalpha() and len(s) >= 5


__all__ = [
    "BrokerOrderSession",
    "CtpTraderSession",
    "FakeBrokerSession",
    "IbInsyncSession",
]
