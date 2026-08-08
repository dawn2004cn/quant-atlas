"""Unified status listing for execution adapters (QMT / CCXT / IBKR / CTP)."""

from __future__ import annotations

from typing import Any

from app.core.runtime_config import get_runtime, get_runtime_bool
from app.infrastructure.execution.qmt_executor import qmt_executor_status


def list_execution_adapters() -> list[dict[str, Any]]:
    """Return adapter readiness rows for ops / SPA observability."""
    rows: list[dict[str, Any]] = []

    qmt = qmt_executor_status(
        account_id=get_runtime("QMT_ACCOUNT_ID", ""),
        qmt_path=get_runtime("QMT_PATH", ""),
        live_submit=get_runtime_bool("QMT_LIVE_SUBMIT", False),
    )
    rows.append(
        {
            "adapter_id": "qmt",
            "market": "CN",
            "phase": "near_term",
            "ready": bool(qmt.get("configured")),
            "contracts": True,
            "detail": qmt,
        }
    )

    rows.append(
        {
            "adapter_id": "ccxt",
            "market": "CRYPTO",
            "phase": "available",
            "ready": True,
            "contracts": True,
            "detail": {
                "note": "CCXTExchangeAdapter + create_order_from_request; withdraw forbidden by policy",
            },
        }
    )

    try:
        from app.infrastructure.adapters.ibkr_adapter import IBKRAdapter

        ibkr = IBKRAdapter().status()
        rows.append(
            {
                "adapter_id": "ibkr",
                "market": "US",
                "phase": ibkr.get("phase", "P2"),
                "ready": bool(ibkr.get("ready")),
                "sim_ready": bool(ibkr.get("sim_ready")),
                "session_wired": bool(ibkr.get("session_wired")),
                "contracts": True,
                "detail": ibkr,
            }
        )
    except Exception as exc:
        rows.append(
            {
                "adapter_id": "ibkr",
                "market": "US",
                "phase": "P2",
                "ready": False,
                "contracts": True,
                "detail": {"error": str(exc)},
            }
        )

    try:
        from app.infrastructure.adapters.ctp_adapter import CTPAdapter

        ctp = CTPAdapter().status()
        rows.append(
            {
                "adapter_id": "ctp",
                "market": "FUT",
                "phase": ctp.get("phase", "P2"),
                "ready": bool(ctp.get("ready")),
                "sim_ready": bool(ctp.get("sim_ready")),
                "session_wired": bool(ctp.get("session_wired")),
                "contracts": True,
                "detail": ctp,
            }
        )
    except Exception as exc:
        rows.append(
            {
                "adapter_id": "ctp",
                "market": "FUT",
                "phase": "P2",
                "ready": False,
                "contracts": True,
                "detail": {"error": str(exc)},
            }
        )

    return rows
