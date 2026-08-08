"""IBKR / CTP × Risk Guard integration probe (ops / CI).

Does not place real broker orders. Live path uses dry-run persistence by default.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.runtime_config import get_runtime_bool
from app.domain.trading.contracts import OrderRequest
from app.infrastructure.adapters.broker_session import FakeBrokerSession
from app.infrastructure.adapters.ctp_adapter import CTPAdapter
from app.infrastructure.adapters.ibkr_adapter import AdapterNotReadyError, IBKRAdapter
from app.modules.execution.services.qmt_integration_probe import ProbeCheck, ProbeReport
from app.modules.execution.services.risk_guard_service import (
    AccountRiskSnapshot,
    InMemoryRiskGuardStore,
    RiskGuardBlockedError,
    RiskGuardService,
)

def _sample_us() -> OrderRequest:
    return OrderRequest(
        symbol="AAPL",
        market="US",
        side="buy",
        quantity=1.0,
        order_type="limit",
        price=100.0,
        client_order_id="ibkr_ctp_probe",
    )


def _sample_fut() -> OrderRequest:
    return OrderRequest(
        symbol="IF2509",
        market="FUT",
        side="buy",
        quantity=1.0,
        order_type="limit",
        price=4000.0,
        client_order_id="ibkr_ctp_probe",
    )


def run_ibkr_ctp_integration_probe() -> ProbeReport:
    checks: list[ProbeCheck] = []
    ibkr_live = get_runtime_bool("IBKR_LIVE_SUBMIT", False)
    ctp_live = get_runtime_bool("CTP_LIVE_SUBMIT", False)
    ibkr_real = get_runtime_bool("IBKR_ALLOW_REAL_ORDERS", False)
    ctp_real = get_runtime_bool("CTP_ALLOW_REAL_ORDERS", False)

    checks.append(
        ProbeCheck(
            id="ibkr_real_default_off",
            title="IBKR_ALLOW_REAL_ORDERS=0（默认禁止真单）",
            passed=not ibkr_real,
            required=True,
            detail=f"allow_real={ibkr_real}",
        )
    )
    checks.append(
        ProbeCheck(
            id="ctp_real_default_off",
            title="CTP_ALLOW_REAL_ORDERS=0（默认禁止真单）",
            passed=not ctp_real,
            required=True,
            detail=f"allow_real={ctp_real}",
        )
    )

    ibkr = IBKRAdapter(allow_simulation=True, live_submit=False, allow_real_orders=False)
    probe = ibkr.probe_connection()
    checks.append(
        ProbeCheck(
            id="ibkr_probe_shape",
            title="IBKR probe 返回 tcp/sdk 字段",
            passed=isinstance(probe.get("tcp"), dict) and isinstance(probe.get("sdk"), dict),
            required=True,
            detail=str({"tcp_ok": (probe.get("tcp") or {}).get("ok"), "sdk": probe.get("sdk")}),
        )
    )
    st = ibkr.status()
    checks.append(
        ProbeCheck(
            id="ibkr_sim_status",
            title="IBKR 仿真 sim_ready",
            passed=bool(st.get("sim_ready")) and st.get("ready") is False,
            required=True,
            detail=str({"sim_ready": st.get("sim_ready"), "ready": st.get("ready")}),
        )
    )

    oid = ibkr.submit_order(_sample_us())
    checks.append(
        ProbeCheck(
            id="ibkr_sim_order",
            title="IBKR 仿真 OrderRequest",
            passed=oid.startswith("IBKR_SIM_"),
            required=True,
            detail=oid,
        )
    )

    # live dry-run
    live = IBKRAdapter(allow_simulation=True, live_submit=True, allow_real_orders=False)
    live_oid = live.submit_order(_sample_us())
    checks.append(
        ProbeCheck(
            id="ibkr_live_dry_run",
            title="IBKR live dry-run 下单落盘",
            passed=live_oid.startswith("IBKR_LIVE_"),
            required=True,
            detail=live_oid,
        )
    )

    ctp = CTPAdapter(allow_simulation=True, live_submit=False)
    ctp.probe_connection()
    ctp_oid = ctp.submit_order(_sample_fut())
    checks.append(
        ProbeCheck(
            id="ctp_sim_order",
            title="CTP 仿真 OrderRequest",
            passed=ctp_oid.startswith("CTP_SIM_"),
            required=True,
            detail=ctp_oid,
        )
    )
    ctp_live_a = CTPAdapter(allow_simulation=True, live_submit=True, allow_real_orders=False)
    ctp_live_oid = ctp_live_a.submit_order(_sample_fut())
    checks.append(
        ProbeCheck(
            id="ctp_live_dry_run",
            title="CTP live dry-run 下单落盘",
            passed=ctp_live_oid.startswith("CTP_LIVE_"),
            required=True,
            detail=ctp_live_oid,
        )
    )

    # Risk Guard on live account
    from app.modules.execution.services import risk_guard_factory as rgf

    store = InMemoryRiskGuardStore()
    store.set_snapshot(
        "ibkr_live",
        AccountRiskSnapshot(equity=90_000.0, day_start_equity=100_000.0),
    )
    guard = RiskGuardService(store=store)
    prev = rgf._guard
    orig_enabled = rgf.risk_guard_enabled
    rgf._guard = guard
    rgf.risk_guard_enabled = lambda: True  # type: ignore[assignment]
    blocked = False
    try:
        blocked_adapter = IBKRAdapter(live_submit=True, allow_real_orders=False)
        try:
            blocked_adapter.submit_order(_sample_us())
        except RiskGuardBlockedError:
            blocked = True
    finally:
        rgf._guard = prev
        rgf.risk_guard_enabled = orig_enabled

    checks.append(
        ProbeCheck(
            id="ibkr_live_risk_gate",
            title="IBKR live 路径 Risk Guard 阻断",
            passed=blocked,
            required=True,
            detail="blocked" if blocked else "not_blocked",
        )
    )

    # registry
    from app.infrastructure.execution.adapter_registry import list_execution_adapters

    rows = {r["adapter_id"]: r for r in list_execution_adapters()}
    checks.append(
        ProbeCheck(
            id="registry_ibkr_ctp",
            title="execution-adapters 含 ibkr/ctp + sim_ready",
            passed=("ibkr" in rows and "ctp" in rows and "sim_ready" in rows["ibkr"]),
            required=True,
            detail=str({k: {"ready": rows[k].get("ready"), "sim_ready": rows[k].get("sim_ready")} for k in ("ibkr", "ctp") if k in rows}),
        )
    )

    fake = FakeBrokerSession(prefix="IBKR_TWS")
    wired = IBKRAdapter(
        live_submit=True,
        allow_real_orders=True,
        confirm_live_account=False,
        port=7497,
        session=fake,
    )
    wired_oid = wired.submit_order(_sample_us())
    checks.append(
        ProbeCheck(
            id="ibkr_session_place_order",
            title="IBKR 注入会话 placeOrder（paper 端口）",
            passed=wired_oid.startswith("IBKR_TWS_"),
            required=True,
            detail=wired_oid,
        )
    )

    live_port = IBKRAdapter(
        live_submit=True,
        allow_real_orders=True,
        confirm_live_account=False,
        port=7496,
        session=FakeBrokerSession(prefix="IBKR_TWS"),
    )
    confirm_blocked = False
    try:
        live_port.submit_order(_sample_us())
    except AdapterNotReadyError as exc:
        confirm_blocked = "live_account_not_confirmed" in str(exc)
    checks.append(
        ProbeCheck(
            id="ibkr_live_port_confirm",
            title="IBKR 实盘端口需 IBKR_CONFIRM_LIVE_ACCOUNT",
            passed=confirm_blocked,
            required=True,
            detail="blocked" if confirm_blocked else "allowed_unexpected",
        )
    )

    ctp_fake = FakeBrokerSession(prefix="CTP_TD")
    ctp_unconfirmed = CTPAdapter(
        live_submit=True,
        allow_real_orders=True,
        confirm_live_account=False,
        session=ctp_fake,
    )
    ctp_confirm_blocked = False
    try:
        ctp_unconfirmed.submit_order(_sample_fut())
    except AdapterNotReadyError as exc:
        ctp_confirm_blocked = "ctp_live_account_not_confirmed" in str(exc)
    ctp_wired = CTPAdapter(
        live_submit=True,
        allow_real_orders=True,
        confirm_live_account=True,
        session=ctp_fake,
    )
    ctp_real_oid = ctp_wired.submit_order(_sample_fut())
    checks.append(
        ProbeCheck(
            id="ctp_session_place_order",
            title="CTP 注入会话 + CONFIRM_LIVE 闸门",
            passed=ctp_confirm_blocked and ctp_real_oid.startswith("CTP_TD_"),
            required=True,
            detail=ctp_real_oid,
        )
    )

    checks.append(
        ProbeCheck(
            id="env_live_flags_info",
            title="当前 LIVE_SUBMIT 标志（信息项）",
            passed=True,
            required=False,
            detail=f"IBKR_LIVE_SUBMIT={ibkr_live} CTP_LIVE_SUBMIT={ctp_live}",
        )
    )

    required_ok = all(c.passed for c in checks if c.required)
    return ProbeReport(
        ok=required_ok,
        checks=checks,
        ts=datetime.now(timezone.utc).isoformat(),
        mode="live" if (ibkr_live or ctp_live) else "simulation",
    )


__all__ = ["run_ibkr_ctp_integration_probe"]
