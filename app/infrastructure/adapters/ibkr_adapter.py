"""IBKR / CTP adapters (SRS P2). Near-term CN equity execution remains QMT.

Modes
-----
* **simulation** (default): in-process ledger; Risk Guard account ``ibkr_sim`` / ``ctp_sim``.
* **live dry-run** (``*_LIVE_SUBMIT=1``, ``*_ALLOW_REAL_ORDERS=0``): persist intent under
  ``instance/ibkr_orders`` / ``instance/ctp_orders``; TCP + optional SDK probe for readiness.
* **live real** (``*_ALLOW_REAL_ORDERS=1``): ``ib_insync.placeOrder`` / injected CTP trader.
  Paper TWS (7497/4002) is default; live TWS ports (7496/4001) require
  ``IBKR_CONFIRM_LIVE_ACCOUNT=1``. CTP real always requires ``CTP_CONFIRM_LIVE_ACCOUNT=1``.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime, get_runtime_bool, get_runtime_int
from app.domain.trading.contracts import OrderRequest, Position, Tick
from app.infrastructure.adapters.broker_connection import (
    detect_ctp_sdk,
    detect_ib_insync,
    tcp_reachable,
)
from app.infrastructure.adapters.broker_session import (
    BrokerOrderSession,
    CtpTraderSession,
    IbInsyncSession,
)

logger = get_logger(__name__)


class AdapterNotReadyError(RuntimeError):
    """Raised when a P2 market adapter cannot accept the requested op."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_instance(*parts: str) -> Path:
    root = Path(__file__).resolve().parents[3]
    return root.joinpath("instance", *parts)


def _persist_live_order(subdir: str, row: dict[str, Any]) -> str | None:
    try:
        out = _repo_instance(subdir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{row.get('order_id', 'order')}.json"
        path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)
    except Exception:
        logger.warning("live order persist failed (%s)", subdir, exc_info=True)
        return None


class _SimOrderBook:
    """In-process simulation ledger shared by IBKR/CTP skeletons."""

    def __init__(self, *, prefix: str) -> None:
        self.prefix = prefix
        self.orders: list[dict[str, Any]] = []
        self._seq = 0

    def record(self, request: OrderRequest, *, adapter_id: str, kind: str = "sim") -> str:
        self._seq += 1
        order_id = f"{self.prefix}_{request.symbol}_{int(time.time())}_{self._seq}"
        row = {
            "order_id": order_id,
            "adapter_id": adapter_id,
            "symbol": request.symbol,
            "market": request.market,
            "side": request.side,
            "quantity": float(request.quantity),
            "order_type": request.order_type,
            "price": request.price,
            "client_order_id": request.client_order_id,
            "simulation": kind == "sim",
            "live_dry_run": kind == "live_dry_run",
            "ts": _now_iso(),
        }
        self.orders.append(row)
        logger.info(
            "%s %s order %s %s %s qty=%s",
            adapter_id,
            kind,
            order_id,
            request.side,
            request.symbol,
            request.quantity,
        )
        return order_id

    def last_price(self, symbol: str) -> float | None:
        for row in reversed(self.orders):
            if row.get("symbol") == symbol and row.get("price") is not None:
                return float(row["price"])
        return None


class IBKRAdapter:
    """Interactive Brokers — simulation / live dry-run / gated real."""

    market = "US"
    adapter_id = "ibkr"

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        client_id: int | None = None,
        allow_simulation: bool | None = None,
        live_submit: bool | None = None,
        allow_real_orders: bool | None = None,
        confirm_live_account: bool | None = None,
        session: BrokerOrderSession | None = None,
    ) -> None:
        self.host = (host if host is not None else get_runtime("IBKR_HOST", "127.0.0.1")).strip()
        self.port = int(port if port is not None else get_runtime_int("IBKR_PORT", 7497))
        self.client_id = int(
            client_id if client_id is not None else get_runtime_int("IBKR_CLIENT_ID", 1)
        )
        self._live_submit = (
            bool(live_submit)
            if live_submit is not None
            else get_runtime_bool("IBKR_LIVE_SUBMIT", False)
        )
        self._allow_simulation = (
            bool(allow_simulation)
            if allow_simulation is not None
            else get_runtime_bool("IBKR_ALLOW_SIMULATION", True)
        )
        self._allow_real = (
            bool(allow_real_orders)
            if allow_real_orders is not None
            else get_runtime_bool("IBKR_ALLOW_REAL_ORDERS", False)
        )
        self._confirm_live = (
            bool(confirm_live_account)
            if confirm_live_account is not None
            else get_runtime_bool("IBKR_CONFIRM_LIVE_ACCOUNT", False)
        )
        self._session = session
        self._book = _SimOrderBook(prefix="IBKR_SIM" if not self._live_submit else "IBKR_LIVE")
        self._last_probe: dict[str, Any] | None = None
        logger.info(
            "IBKRAdapter initialized (live=%s real=%s confirm_live=%s sim=%s host=%s:%s)",
            self._live_submit,
            self._allow_real,
            self._confirm_live,
            self._allow_simulation and not self._live_submit,
            self.host,
            self.port,
        )

    @property
    def simulation_enabled(self) -> bool:
        return self._allow_simulation and not self._live_submit

    def probe_connection(self, *, timeout_sec: float = 1.5) -> dict[str, Any]:
        tcp = tcp_reachable(self.host, self.port, timeout_sec=timeout_sec)
        sdk = detect_ib_insync()
        report = {
            "adapter_id": self.adapter_id,
            "tcp": tcp,
            "sdk": sdk,
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "live_submit": self._live_submit,
            "allow_real_orders": self._allow_real,
            "confirm_live_account": self._confirm_live,
            "paper_port": not _is_ibkr_live_port(self.port),
            "session_injected": self._session is not None,
            "configured": bool(self.host and self.port > 0),
            "ts": _now_iso(),
        }
        self._last_probe = report
        return report

    def status(self) -> dict[str, Any]:
        probe = self._last_probe or self.probe_connection()
        tcp_ok = bool((probe.get("tcp") or {}).get("ok"))
        sdk_ok = bool((probe.get("sdk") or {}).get("installed"))
        # ready means live path is configured + reachable (+ SDK if real orders intended)
        live_ready = self._live_submit and tcp_ok and (sdk_ok if self._allow_real else True)
        return {
            "adapter_id": self.adapter_id,
            "ready": bool(live_ready),
            "sim_ready": self.simulation_enabled,
            "simulation": self.simulation_enabled,
            "live_submit": self._live_submit,
            "allow_real_orders": self._allow_real,
            "confirm_live_account": self._confirm_live,
            "paper_port": not _is_ibkr_live_port(self.port),
            "session_wired": self._session is not None or (self._allow_real and sdk_ok),
            "phase": "P2",
            "contracts": True,
            "pending_sim_orders": len(self._book.orders),
            "connection": {
                "tcp_ok": tcp_ok,
                "sdk_installed": sdk_ok,
                "host": self.host,
                "port": self.port,
                "latency_ms": (probe.get("tcp") or {}).get("latency_ms"),
                "session_injected": self._session is not None,
                "confirm_live_account": self._confirm_live,
                "paper_port": not _is_ibkr_live_port(self.port),
            },
            "message": self._status_message(live_ready=live_ready, tcp_ok=tcp_ok, sdk_ok=sdk_ok),
        }

    def _status_message(self, *, live_ready: bool, tcp_ok: bool, sdk_ok: bool) -> str:
        if self.simulation_enabled:
            return "IBKR simulation accepts OrderRequest"
        if self._live_submit and not self._allow_real:
            return (
                "IBKR live dry-run: TCP ok, orders persisted locally"
                if tcp_ok
                else "IBKR live dry-run: TWS/Gateway TCP unreachable"
            )
        if self._allow_real and not sdk_ok and self._session is None:
            return "IBKR real orders require ib_insync or injected session"
        if self._allow_real and _is_ibkr_live_port(self.port) and not self._confirm_live:
            return "IBKR live TWS port needs IBKR_CONFIRM_LIVE_ACCOUNT=1"
        if live_ready and self._allow_real:
            return "IBKR live session ready (placeOrder via ib_insync / injected session)"
        return "IBKR live not ready"

    def submit_order(self, request: OrderRequest) -> str:
        from app.modules.execution.services.risk_guard_factory import (
            get_risk_guard_service,
            risk_guard_enabled,
        )

        if self._live_submit:
            account = "ibkr_live"
            if risk_guard_enabled():
                get_risk_guard_service().ensure_order_allowed(account)
            if self._allow_real:
                return self._submit_real(request)
            # dry-run live path
            oid = self._book.record(request, adapter_id=self.adapter_id, kind="live_dry_run")
            row = dict(self._book.orders[-1])
            row["mode"] = "live_dry_run"
            _persist_live_order("ibkr_orders", row)
            return oid

        if not self._allow_simulation:
            raise AdapterNotReadyError("ibkr_adapter_not_ready")
        if risk_guard_enabled():
            get_risk_guard_service().ensure_order_allowed("ibkr_sim")
        return self._book.record(request, adapter_id=self.adapter_id, kind="sim")

    def _submit_real(self, request: OrderRequest) -> str:
        if _is_ibkr_live_port(self.port) and not self._confirm_live:
            raise AdapterNotReadyError("ibkr_live_account_not_confirmed")
        session = self._resolve_session()
        try:
            session.connect()
            oid = session.place_order(request)
        except AdapterNotReadyError:
            raise
        except Exception as exc:
            raise AdapterNotReadyError(f"ibkr_place_order_failed: {exc}") from exc
        row = {
            "order_id": oid,
            "adapter_id": self.adapter_id,
            "symbol": request.symbol,
            "market": request.market,
            "side": request.side,
            "quantity": float(request.quantity),
            "order_type": request.order_type,
            "price": request.price,
            "client_order_id": request.client_order_id,
            "simulation": False,
            "live_dry_run": False,
            "mode": "live_real",
            "ts": _now_iso(),
        }
        self._book.orders.append(row)
        _persist_live_order("ibkr_orders", row)
        _notify_real_order("ibkr", oid, request)
        return oid

    def _resolve_session(self) -> BrokerOrderSession:
        if self._session is not None:
            return self._session
        sdk = detect_ib_insync()
        if not sdk.get("installed"):
            raise AdapterNotReadyError("ibkr_ib_insync_missing")
        return IbInsyncSession(host=self.host, port=self.port, client_id=self.client_id)

    def get_positions(self) -> list[Position]:
        if self._live_submit and self._allow_real:
            try:
                return self._resolve_session().list_positions()
            except AdapterNotReadyError:
                return []
            except Exception:
                logger.warning("ibkr live positions failed", exc_info=True)
                return []
        if self._live_submit:
            return []
        if not self._allow_simulation:
            raise AdapterNotReadyError("ibkr_adapter_not_ready")
        return []

    def get_tick(self, symbol: str) -> Tick:
        if self._live_submit or not self._allow_simulation:
            if self._live_submit:
                last = self._book.last_price(symbol)
                px = float(last) if last is not None else 0.0
                return Tick(symbol=symbol, market="US", last=px, bid=None, ask=None, ts=time.time())
            raise AdapterNotReadyError("ibkr_adapter_not_ready")
        last = self._book.last_price(symbol)
        px = float(last) if last is not None else 0.0
        return Tick(symbol=symbol, market="US", last=px, bid=None, ask=None, ts=time.time())

    def list_sim_orders(self) -> list[dict[str, Any]]:
        return list(self._book.orders)


class CTPAdapter:
    """Domestic futures CTP — simulation / live dry-run; CN equity prefer QMT."""

    market = "FUT"
    adapter_id = "ctp"

    def __init__(
        self,
        *,
        broker_id: str | None = None,
        user_id: str | None = None,
        password: str | None = None,
        md_front: str | None = None,
        td_front: str | None = None,
        allow_simulation: bool | None = None,
        live_submit: bool | None = None,
        allow_real_orders: bool | None = None,
        confirm_live_account: bool | None = None,
        session: BrokerOrderSession | None = None,
        trader: Any | None = None,
    ) -> None:
        self.broker_id = (broker_id if broker_id is not None else get_runtime("CTP_BROKER_ID", "")).strip()
        self.user_id = (user_id if user_id is not None else get_runtime("CTP_USER_ID", "")).strip()
        password_val = password if password is not None else get_runtime("CTP_PASSWORD", "")
        self._password_set = bool(str(password_val or "").strip())
        self.md_front = (md_front if md_front is not None else get_runtime("CTP_MD_FRONT", "")).strip()
        self.td_front = (td_front if td_front is not None else get_runtime("CTP_TD_FRONT", "")).strip()
        self._live_submit = (
            bool(live_submit)
            if live_submit is not None
            else get_runtime_bool("CTP_LIVE_SUBMIT", False)
        )
        self._allow_simulation = (
            bool(allow_simulation)
            if allow_simulation is not None
            else get_runtime_bool("CTP_ALLOW_SIMULATION", True)
        )
        self._allow_real = (
            bool(allow_real_orders)
            if allow_real_orders is not None
            else get_runtime_bool("CTP_ALLOW_REAL_ORDERS", False)
        )
        self._confirm_live = (
            bool(confirm_live_account)
            if confirm_live_account is not None
            else get_runtime_bool("CTP_CONFIRM_LIVE_ACCOUNT", False)
        )
        if session is not None:
            self._session = session
        elif trader is not None:
            self._session = CtpTraderSession(trader, broker_id=self.broker_id, user_id=self.user_id)
        else:
            self._session = None
        self._book = _SimOrderBook(prefix="CTP_SIM" if not self._live_submit else "CTP_LIVE")
        self._last_probe: dict[str, Any] | None = None
        logger.info(
            "CTPAdapter initialized (live=%s real=%s confirm_live=%s sim=%s; prefer QMT near-term)",
            self._live_submit,
            self._allow_real,
            self._confirm_live,
            self._allow_simulation and not self._live_submit,
        )

    @property
    def simulation_enabled(self) -> bool:
        return self._allow_simulation and not self._live_submit

    @staticmethod
    def _parse_front(front: str) -> tuple[str, int] | None:
        # CTP fronts often look like tcp://ip:port
        s = (front or "").strip()
        if not s:
            return None
        s = s.replace("tcp://", "").replace("TCP://", "")
        if ":" not in s:
            return None
        host, _, port_s = s.rpartition(":")
        try:
            return host.strip(), int(port_s)
        except ValueError:
            return None

    def probe_connection(self, *, timeout_sec: float = 1.5) -> dict[str, Any]:
        md = self._parse_front(self.md_front)
        td = self._parse_front(self.td_front)
        md_tcp = tcp_reachable(md[0], md[1], timeout_sec=timeout_sec) if md else {
            "ok": False,
            "error": "md_front_missing",
            "latency_ms": None,
        }
        td_tcp = tcp_reachable(td[0], td[1], timeout_sec=timeout_sec) if td else {
            "ok": False,
            "error": "td_front_missing",
            "latency_ms": None,
        }
        sdk = detect_ctp_sdk()
        creds = bool(self.broker_id and self.user_id and self._password_set)
        report = {
            "adapter_id": self.adapter_id,
            "md_tcp": md_tcp,
            "td_tcp": td_tcp,
            "sdk": sdk,
            "broker_id_set": bool(self.broker_id),
            "user_id_set": bool(self.user_id),
            "password_set": self._password_set,
            "credentials_configured": creds,
            "live_submit": self._live_submit,
            "allow_real_orders": self._allow_real,
            "confirm_live_account": self._confirm_live,
            "session_injected": self._session is not None,
            "configured": bool(creds and self.td_front),
            "ts": _now_iso(),
        }
        self._last_probe = report
        return report

    def status(self) -> dict[str, Any]:
        probe = self._last_probe or self.probe_connection()
        td_ok = bool((probe.get("td_tcp") or {}).get("ok"))
        sdk_ok = bool((probe.get("sdk") or {}).get("installed"))
        creds = bool(probe.get("credentials_configured"))
        configured = bool(probe.get("configured"))
        live_ready = (
            self._live_submit and configured and td_ok and (sdk_ok if self._allow_real else True)
        )
        return {
            "adapter_id": self.adapter_id,
            "ready": bool(live_ready),
            "sim_ready": self.simulation_enabled,
            "simulation": self.simulation_enabled,
            "live_submit": self._live_submit,
            "allow_real_orders": self._allow_real,
            "confirm_live_account": self._confirm_live,
            "session_wired": self._session is not None,
            "phase": "P2",
            "near_term": "QMT",
            "contracts": True,
            "pending_sim_orders": len(self._book.orders),
            "credentials_configured": creds,
            "connection": {
                "td_ok": td_ok,
                "md_ok": bool((probe.get("md_tcp") or {}).get("ok")),
                "sdk_installed": sdk_ok,
                "td_latency_ms": (probe.get("td_tcp") or {}).get("latency_ms"),
                "session_injected": self._session is not None,
                "confirm_live_account": self._confirm_live,
            },
            "message": (
                "CTP live session ready (injected trader / FakeBrokerSession)"
                if self._live_submit and self._allow_real and self._session is not None
                else (
                    "CTP live dry-run / probe path (CN equity → QMT)"
                    if self._live_submit
                    else "CTP simulation accepts OrderRequest (CN equity → QMT)"
                )
            ),
        }

    def submit_order(self, request: OrderRequest) -> str:
        from app.modules.execution.services.risk_guard_factory import (
            get_risk_guard_service,
            risk_guard_enabled,
        )

        if self._live_submit:
            if risk_guard_enabled():
                get_risk_guard_service().ensure_order_allowed("ctp_live")
            if self._allow_real:
                return self._submit_real(request)
            oid = self._book.record(request, adapter_id=self.adapter_id, kind="live_dry_run")
            row = dict(self._book.orders[-1])
            row["mode"] = "live_dry_run"
            _persist_live_order("ctp_orders", row)
            return oid

        if not self._allow_simulation:
            raise AdapterNotReadyError("ctp_adapter_not_ready")
        if risk_guard_enabled():
            get_risk_guard_service().ensure_order_allowed("ctp_sim")
        return self._book.record(request, adapter_id=self.adapter_id, kind="sim")

    def _submit_real(self, request: OrderRequest) -> str:
        if not self._confirm_live:
            raise AdapterNotReadyError("ctp_live_account_not_confirmed")
        session = self._session
        if session is None:
            sdk = detect_ctp_sdk()
            if not sdk.get("installed"):
                raise AdapterNotReadyError("ctp_sdk_missing")
            raise AdapterNotReadyError(
                "ctp_trader_not_injected — pass session=/trader= or prefer QMT for CN equity"
            )
        try:
            session.connect()
            oid = session.place_order(request)
        except AdapterNotReadyError:
            raise
        except Exception as exc:
            raise AdapterNotReadyError(f"ctp_place_order_failed: {exc}") from exc
        row = {
            "order_id": oid,
            "adapter_id": self.adapter_id,
            "symbol": request.symbol,
            "market": request.market,
            "side": request.side,
            "quantity": float(request.quantity),
            "order_type": request.order_type,
            "price": request.price,
            "client_order_id": request.client_order_id,
            "simulation": False,
            "live_dry_run": False,
            "mode": "live_real",
            "ts": _now_iso(),
        }
        self._book.orders.append(row)
        _persist_live_order("ctp_orders", row)
        _notify_real_order("ctp", oid, request)
        return oid

    def get_positions(self) -> list[Position]:
        if self._live_submit and self._allow_real and self._session is not None:
            try:
                return self._session.list_positions()
            except Exception:
                logger.warning("ctp live positions failed", exc_info=True)
                return []
        if self._live_submit:
            return []
        if not self._allow_simulation:
            raise AdapterNotReadyError("ctp_adapter_not_ready")
        return []

    def list_sim_orders(self) -> list[dict[str, Any]]:
        return list(self._book.orders)


def _is_ibkr_live_port(port: int) -> bool:
    """TWS live=7496, IB Gateway live=4001 (paper is 7497 / 4002)."""
    return int(port) in {7496, 4001}


def _notify_real_order(adapter_id: str, order_id: str, request: OrderRequest) -> None:
    try:
        from app.infrastructure.notifications.telegram_alerter import TelegramAlerter

        TelegramAlerter().send(
            f"[QuantAtlas] {adapter_id} real order {order_id} "
            f"{request.side} {request.symbol} qty={request.quantity}"
        )
    except Exception:
        logger.warning("real-order telegram notify skipped", exc_info=True)


__all__ = ["AdapterNotReadyError", "CTPAdapter", "IBKRAdapter"]
