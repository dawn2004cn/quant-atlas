"""Shared TCP / optional-SDK probes for IBKR / CTP live wiring."""

from __future__ import annotations

import socket
from typing import Any


def tcp_reachable(host: str, port: int, *, timeout_sec: float = 1.5) -> dict[str, Any]:
    """Best-effort TCP connect probe (no secrets)."""
    host = (host or "").strip()
    if not host or port <= 0:
        return {"ok": False, "error": "host_or_port_missing", "latency_ms": None}
    try:
        t0 = __import__("time").perf_counter()
        with socket.create_connection((host, int(port)), timeout=timeout_sec):
            ms = (__import__("time").perf_counter() - t0) * 1000.0
        return {"ok": True, "error": None, "latency_ms": round(ms, 3), "host": host, "port": int(port)}
    except OSError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "latency_ms": None,
            "host": host,
            "port": int(port),
        }


def detect_ib_insync() -> dict[str, Any]:
    try:
        import ib_insync  # noqa: F401

        return {"installed": True, "module": "ib_insync"}
    except ImportError:
        return {"installed": False, "module": "ib_insync", "hint": "pip install ib_insync"}


def detect_ctp_sdk() -> dict[str, Any]:
    """Detect common CTP Python bindings (optional)."""
    for name in ("openctp_ctp", "vnpy_ctp", "thosttraderapi"):
        try:
            __import__(name)
            return {"installed": True, "module": name}
        except ImportError:
            continue
    return {
        "installed": False,
        "module": None,
        "hint": "install openctp_ctp / vnpy_ctp (optional); CN equity prefer QMT",
    }
