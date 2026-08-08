"""QMT × Risk Guard × persistence integration probe (ops / CI).

Runs checklist items without requiring live xtquant. Does not place live orders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime, get_runtime_bool

logger = get_logger(__name__)


@dataclass
class ProbeCheck:
    id: str
    title: str
    passed: bool
    required: bool = True
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "passed": self.passed,
            "required": self.required,
            "detail": self.detail,
        }


@dataclass
class ProbeReport:
    ok: bool
    checks: list[ProbeCheck] = field(default_factory=list)
    ts: str = ""
    mode: str = "simulation"

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "ts": self.ts,
            "mode": self.mode,
            "passed": sum(1 for c in self.checks if c.passed),
            "failed": sum(1 for c in self.checks if not c.passed and c.required),
            "checks": [c.as_dict() for c in self.checks],
        }


def _persist_dir() -> Path:
    root = Path(__file__).resolve().parents[4]
    return root / "instance" / "qmt_orders"


def persist_qmt_order_event(order: dict[str, Any]) -> str | None:
    """Append a simulation/live order event to instance/qmt_orders (file backend)."""
    mode = (get_runtime("QMT_ORDER_PERSISTENCE", "file") or "file").strip().lower()
    if mode in {"0", "off", "false", "none"}:
        return None
    try:
        from app.domain.trading.order_persistence import OrderPersistence

        out = _persist_dir()
        out.mkdir(parents=True, exist_ok=True)
        if mode == "redis":
            persistence = OrderPersistence(backend="redis")
        else:
            persistence = OrderPersistence(backend="file", path=str(out))
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in order.items()},
        }
        persistence.save_event(event)
        state = persistence.load_state() or {}
        orders = dict(state.get("orders") or {})
        oid = str(order.get("order_id") or "")
        if oid:
            orders[oid] = event
            state["orders"] = orders
            state["updated_at"] = event["ts"]
            persistence.save_state(state)
        return str(out)
    except Exception:
        logger.warning("qmt order persistence failed", exc_info=True)
        return None


def run_qmt_integration_probe(*, account_id: str | None = None) -> ProbeReport:
    """Execute automated checklist items for QMT simulation path."""
    checks: list[ProbeCheck] = []
    acc = (account_id or get_runtime("QMT_ACCOUNT_ID", "") or "qmt_probe").strip()
    live = get_runtime_bool("QMT_LIVE_SUBMIT", False)
    configured = bool((get_runtime("QMT_ACCOUNT_ID", "") or "").strip())
    path_set = bool((get_runtime("QMT_PATH", "") or "").strip())

    checks.append(
        ProbeCheck(
            id="config_simulation_default",
            title="QMT_LIVE_SUBMIT=0（仿真优先）",
            passed=not live,
            required=True,
            detail=f"live_submit={live}",
        )
    )
    checks.append(
        ProbeCheck(
            id="config_account",
            title="QMT_ACCOUNT_ID 已配置（运维建议）",
            passed=configured,
            required=False,
            detail="set" if configured else "empty (probe uses qmt_probe)",
        )
    )
    checks.append(
        ProbeCheck(
            id="config_path",
            title="QMT_PATH 已配置（运维建议）",
            passed=path_set,
            required=False,
            detail="set" if path_set else "empty",
        )
    )
    checks.append(
        ProbeCheck(
            id="risk_guard_enabled",
            title="RISK_GUARD_ENABLED",
            passed=get_runtime_bool("RISK_GUARD_ENABLED", True),
            required=True,
            detail=f"enabled={get_runtime_bool('RISK_GUARD_ENABLED', True)}",
        )
    )

    # Shared singleton
    from app.modules.execution.services.risk_guard_factory import get_risk_guard_service

    g1 = get_risk_guard_service()
    g2 = get_risk_guard_service()
    checks.append(
        ProbeCheck(
            id="risk_guard_singleton",
            title="Borderless/QMT 共用 Risk Guard 单例",
            passed=g1 is g2,
            required=True,
            detail="same" if g1 is g2 else "distinct",
        )
    )

    # Isolated drawdown / stop-out using temporary store swap via force_new=False but
    # operate on a dedicated probe account id without poisoning other accounts badly.
    from app.modules.execution.services.risk_guard_service import (
        AccountRiskSnapshot,
        RiskGuardBlockedError,
        RiskGuardService,
        InMemoryRiskGuardStore,
    )

    store = InMemoryRiskGuardStore()
    isolated = RiskGuardService(store=store)
    store.set_snapshot(
        acc,
        AccountRiskSnapshot(equity=90_000.0, day_start_equity=100_000.0),
    )
    blocked = False
    try:
        isolated.ensure_order_allowed(acc)
    except RiskGuardBlockedError:
        blocked = True
    checks.append(
        ProbeCheck(
            id="drawdown_gate",
            title="日回撤≥5% 阻断新单",
            passed=blocked,
            required=True,
            detail="blocked" if blocked else "allowed_unexpected",
        )
    )

    store2 = InMemoryRiskGuardStore()
    isolated2 = RiskGuardService(store=store2)
    store2.set_snapshot(acc, AccountRiskSnapshot(equity=100_000.0, day_start_equity=100_000.0))
    for _ in range(3):
        isolated2.record_stop_out(acc)
    suspended = False
    try:
        isolated2.ensure_order_allowed(acc)
    except RiskGuardBlockedError:
        suspended = True
    checks.append(
        ProbeCheck(
            id="stop_out_gate",
            title="连亏≥3 暂停执行",
            passed=suspended,
            required=True,
            detail="suspended" if suspended else "allowed_unexpected",
        )
    )

    # Redis snapshot roundtrip (optional if URL missing)
    redis_url = (
        get_runtime("RISK_GUARD_REDIS_URL", "")
        or get_runtime("TASK_MESSAGE_REDIS_URL", "")
        or get_runtime("REDIS_URL", "")
    ).strip()
    if redis_url:
        try:
            from app.infrastructure.trading.risk_guard_redis_store import RedisRiskGuardStore

            rstore = RedisRiskGuardStore(redis_url=redis_url, key_prefix="qa:risk_guard_probe:")
            probe_acc = f"{acc}_redis"
            snap = AccountRiskSnapshot(
                equity=88_000.0,
                day_start_equity=100_000.0,
                consecutive_stop_outs=2,
                execution_suspended=True,
            )
            rstore.set_snapshot(probe_acc, snap)
            loaded = rstore.get_snapshot(probe_acc)
            ok_redis = (
                loaded.execution_suspended
                and loaded.consecutive_stop_outs == 2
                and abs(loaded.equity - 88_000.0) < 1e-6
            )
            checks.append(
                ProbeCheck(
                    id="redis_snapshot",
                    title="Risk Guard Redis 快照可恢复",
                    passed=ok_redis,
                    required=False,
                    detail="ok" if ok_redis else f"loaded={loaded}",
                )
            )
        except Exception as exc:
            checks.append(
                ProbeCheck(
                    id="redis_snapshot",
                    title="Risk Guard Redis 快照可恢复",
                    passed=False,
                    required=False,
                    detail=str(exc),
                )
            )
    else:
        checks.append(
            ProbeCheck(
                id="redis_snapshot",
                title="Risk Guard Redis 快照可恢复",
                passed=False,
                required=False,
                detail="no_redis_url",
            )
        )

    # OrderRequest → execute_order_request simulation with patched guard (allow)
    from app.domain.trading.contracts import OrderRequest
    from app.infrastructure.execution.qmt_executor import QMTExecutor
    from app.modules.execution.services import risk_guard_factory as rgf

    allow_store = InMemoryRiskGuardStore()
    allow_store.set_snapshot(acc, AccountRiskSnapshot(equity=100_000.0, day_start_equity=100_000.0))
    allow_guard = RiskGuardService(store=allow_store)
    prev = rgf._guard
    rgf._guard = allow_guard
    order_id = ""
    persist_path: str | None = None
    try:
        ex = QMTExecutor(
            account_id=acc,
            qmt_path=get_runtime("QMT_PATH", "") or "/qmt-probe",
            live_submit=False,
        )
        order_id = ex.execute_order_request(
            OrderRequest(
                symbol="600519",
                market="CN",
                side="buy",
                quantity=100,
                order_type="limit",
                price=1800.0,
                client_order_id="qmt_probe",
            ),
            strategy_id="qmt_integration_probe",
        )
        pending = ex.get_pending_orders().get(order_id) or {}
        persist_path = persist_qmt_order_event(pending or {"order_id": order_id, "symbol": "600519"})
        checks.append(
            ProbeCheck(
                id="order_request_sim",
                title="OrderRequest → QMT 仿真下单",
                passed=bool(order_id.startswith("QMT_")) and bool(pending.get("simulation")),
                required=True,
                detail=f"order_id={order_id}",
            )
        )
    except Exception as exc:
        checks.append(
            ProbeCheck(
                id="order_request_sim",
                title="OrderRequest → QMT 仿真下单",
                passed=False,
                required=True,
                detail=str(exc),
            )
        )
    finally:
        rgf._guard = prev

    # Blocked path through real executor + patched blocking guard
    block_store = InMemoryRiskGuardStore()
    block_store.set_snapshot(acc, AccountRiskSnapshot(equity=90_000.0, day_start_equity=100_000.0))
    block_guard = RiskGuardService(store=block_store)
    prev = rgf._guard
    rgf._guard = block_guard
    try:
        ex2 = QMTExecutor(account_id=acc, qmt_path="/qmt-probe", live_submit=False)
        blocked_exec = False
        try:
            ex2.execute_order_request(
                OrderRequest(
                    symbol="600519",
                    market="CN",
                    side="buy",
                    quantity=100,
                    order_type="market",
                    price=None,
                )
            )
        except RiskGuardBlockedError:
            blocked_exec = True
        checks.append(
            ProbeCheck(
                id="executor_risk_gate",
                title="QMTExecutor 接入 Risk Guard 阻断",
                passed=blocked_exec,
                required=True,
                detail="blocked" if blocked_exec else "not_blocked",
            )
        )
    finally:
        rgf._guard = prev

    checks.append(
        ProbeCheck(
            id="order_persistence",
            title="仿真订单事件落盘（file/redis）",
            passed=persist_path is not None or (get_runtime("QMT_ORDER_PERSISTENCE", "file") or "").lower() in {"0", "off"},
            required=False,
            detail=persist_path or get_runtime("QMT_ORDER_PERSISTENCE", "file"),
        )
    )

    required_ok = all(c.passed for c in checks if c.required)
    return ProbeReport(
        ok=required_ok,
        checks=checks,
        ts=datetime.now(timezone.utc).isoformat(),
        mode="live" if live else "simulation",
    )
