from __future__ import annotations
"""RD-Agent 产物注册后的轻量 Qlib 门禁：参考买入持有可跑通即写入 bundle.qlib_gate。"""


from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, TYPE_CHECKING


from ...domain.enums import MarketCode
from ...domain.ports import QlibDataProviderPort
from ...infrastructure.qlib.symbol_map import cn_to_qlib_instrument, qlib_instrument_to_symbol
from .artifact_registry import RDAgentArtifactRegistry
from .factor_expression_gate import evaluate_factor_expression_gate

if TYPE_CHECKING:
    pass



from app.core.logger import get_logger

logger = get_logger(__name__)


def _merge_factor_gate(gate: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    fe = evaluate_factor_expression_gate(bundle)
    gate["factor_expression_gate"] = fe
    if fe.get("skipped"):
        return gate
    buy_ok = bool(gate.get("ok"))
    fe_ok = bool(fe.get("ok"))
    gate["ok"] = buy_ok and fe_ok
    if not fe_ok and buy_ok:
        gate["message"] = (str(gate.get("message") or "").strip() + "；因子表达式门禁未通过").strip("；")
    return gate


def execute_rdagent_qlib_gate(
    job_id: str,
    *,
    qlib_service: QlibDataProviderPort | None = None,
    base_dir: Path,
) -> dict[str, Any]:
    """对已成功注册的 run bundle 跑一次统一买入持有；结果合并进 ``qlib_gate``。"""
    reg = RDAgentArtifactRegistry(base_dir)
    bundle = reg.get_run_bundle(job_id)
    if not bundle:
        return {"ok": False, "skipped": True, "message": "无产物 bundle，跳过门禁"}

    if qlib_service is None:
        from app.infrastructure.repositories.deps import create_default_qlib_pipeline_service

        qlib_service = create_default_qlib_pipeline_service()

    st = qlib_service.status()
    meta = st.get("last_meta") or {}
    instruments: list[str] = list(meta.get("instruments") or [])
    if not instruments:
        instruments = list(st.get("instruments_on_disk") or [])

    bench_raw = str(bundle.get("benchmark") or "").strip()
    reference_kind = "benchmark"
    first = ""
    if bench_raw and len(bench_raw) >= 8 and bench_raw.upper()[:2] in ("SH", "SZ"):
        first = bench_raw.upper()
    elif bench_raw:
        u = bench_raw.upper()
        if u.isdigit() and len(u) == 6:
            first = cn_to_qlib_instrument(u)
        else:
            first = bench_raw

    if not first and instruments:
        first = str(instruments[0]).strip()
        reference_kind = "first_meta_instrument"

    if not first:
        gate = {
            "ok": False,
            "skipped": True,
            "message": "无 Qlib 标的（bundle 无 benchmark 且 meta/磁盘为空），跳过门禁",
        }
        _merge_factor_gate(gate, bundle)
        reg.merge_qlib_gate(job_id, gate)
        return gate

    if len(first) >= 8 and first.upper().startswith(("SH", "SZ")):
        sym = qlib_instrument_to_symbol(first, MarketCode.CN)
    else:
        sym = first

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    try:
        bt = qlib_service.unified_buy_hold_backtest(sym, MarketCode.CN, start=start, end=end)
    except Exception as exc:  # noqa: BLE001
        logger.warning("qlib gate backtest failed run_id=%s: %s", job_id, exc)
        gate = {
            "ok": False,
            "skipped": False,
            "message": str(exc),
            "reference_symbol": sym,
        }
        _merge_factor_gate(gate, bundle)
        reg.merge_qlib_gate(job_id, gate)
        return gate

    err = bt.get("error")
    m = bt.get("metrics") or {}
    ok = err is None and m.get("total_return") is not None
    gate = {
        "ok": bool(ok),
        "skipped": False,
        "reference_symbol": sym,
        "reference_instrument": first,
        "reference_kind": reference_kind,
        "bundle_benchmark": bundle.get("benchmark"),
        "period": {"start": start, "end": end},
        "backtest_engine": bt.get("backtest_engine"),
        "source": bt.get("source"),
        "error": err,
        "metrics_summary": {
            "total_return": m.get("total_return"),
            "max_drawdown": m.get("max_drawdown"),
            "sharpe_ratio": m.get("sharpe_ratio"),
        },
    }
    _merge_factor_gate(gate, bundle)
    reg.merge_qlib_gate(job_id, gate)
    return gate
