from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""研究闭环（数据→Qlib→RD→门禁→Agent）聚合快照，供 API 与 quant_tools 共用。"""


from pathlib import Path
from typing import Any


def _summarize_qlib_gate(g: dict[str, Any] | None) -> GenericResponseDTO | None:
    if not isinstance(g, dict) or not g:
        return None
    fe = g.get("factor_expression_gate")
    out: dict[str, Any] = {
        "overall_ok": bool(g.get("ok")),
        "skipped": bool(g.get("skipped")),
        "reference_symbol": g.get("reference_symbol"),
        "reference_kind": g.get("reference_kind"),
        "message": (str(g.get("message") or ""))[:300],
    }
    if isinstance(fe, dict):
        out["factor_expression"] = {
            "ok": fe.get("ok"),
            "skipped": fe.get("skipped"),
            "preview": (str(fe.get("formulation_preview") or ""))[:160],
            "message": (str(fe.get("message") or ""))[:200],
        }
    return out


def _qlib_gate_step_detail(gate_for_step: dict[str, Any] | None, *, enable_rd_agent: bool) -> str:
    if not gate_for_step or not isinstance(gate_for_step, dict):
        return "尚无门禁记录（或均为跳过）" if enable_rd_agent else "RD 未开启"
    if gate_for_step.get("skipped"):
        return str(gate_for_step.get("message") or "门禁跳过")[:400]
    parts: list[str] = []
    if gate_for_step.get("ok"):
        parts.append("总结果: 通过")
    else:
        parts.append("总结果: 未通过")
    fe = gate_for_step.get("factor_expression_gate")
    if isinstance(fe, dict) and not fe.get("skipped"):
        if fe.get("ok"):
            parts.append("因子表达式门: 通过")
        else:
            parts.append(f"因子表达式门: 未通过（{(fe.get('message') or '')[:120]}）")
    ref = gate_for_step.get("reference_symbol") or gate_for_step.get("reference_instrument")
    if ref:
        parts.append(f"参考标的: {ref}")
    return "；".join(parts)[:500]


def build_research_pipeline_snapshot(
    *,
    enable_qlib: bool,
    enable_rd_agent: bool,
    qlib_pipeline_service: Any,
    rdagent_run_service: Any,
) -> GenericResponseDTO:
    from app.modules.system.services.helpers.rdagent_access import create_rdagent_artifact_registry
    st: dict[str, Any] = qlib_pipeline_service.status() if enable_qlib and qlib_pipeline_service is not None else {}

    base = Path(qlib_pipeline_service.export_dir).resolve().parent.parent if enable_qlib and qlib_pipeline_service is not None else None

    reg = create_rdagent_artifact_registry(base) if base is not None else None

    rd_rows = rdagent_run_service.list_recent_runs(limit=12) if enable_rd_agent and rdagent_run_service is not None else []
    enriched: list[dict[str, Any]] = []
    for row in rd_rows:
        rid = row.get("run_id")
        if not rid:

            continue

        if reg is not None:

            b = reg.get_run_bundle(str(rid))

        else:

            b = None

        g = (b or {}).get("qlib_gate")
        enriched.append({**row, "qlib_gate": g})

    gate_for_step: dict[str, Any] | None = None
    for row in enriched:
        g = row.get("qlib_gate")
        if isinstance(g, dict) and not g.get("skipped"):
            gate_for_step = g
            break

    steps = [
        {
            "id": "data_csv",
            "label": "行情 → Qlib CSV",
            "ok": bool(enable_qlib and (st.get("csv_count") or 0) > 0),
            "detail": f"csv_count={st.get('csv_count', 0)}" if enable_qlib else "ENABLE_QLIB 关闭",
        },
        {
            "id": "qlib_bin",
            "label": "Dump qlib_bin",
            "ok": bool(enable_qlib and st.get("qlib_bin_ready")),
            "detail": ("qlib_bin 就绪" if st.get("qlib_bin_ready") else "qlib_bin 未就绪") if enable_qlib else "",
        },
        {
            "id": "rd_run",
            "label": "RD-Agent 因子实验",
            "ok": bool(enable_rd_agent and len(enriched) > 0),
            "detail": f"索引中最近 {len(enriched)} 条 run" if enable_rd_agent else "ENABLE_RD_AGENT 关闭",
        },
        {
            "id": "qlib_gate",
            "label": "注册后 Qlib 门禁",
            "ok": bool(gate_for_step and gate_for_step.get("ok")),
            "detail": _qlib_gate_step_detail(gate_for_step, enable_rd_agent=enable_rd_agent),
        },
        {
            "id": "agents",
            "label": "六分析师 + 平台回测",
            "ok": True,
            "detail": "AI 研究报告 / quant_tools（run_backtest、run_qlib_unified_backtest 等）",
        },
    ]

    return {
        "enable_qlib": enable_qlib,
        "enable_rd_agent": enable_rd_agent,
        "qlib_status": st,
        "rd_recent_runs": enriched,
        "recent_qlib_gate": _summarize_qlib_gate(gate_for_step),
        "steps": steps,
        "mermaid": (
            "flowchart LR\n"
            "  D[行情/ingest] --> B[qlib_bin]\n"
            "  B --> R[RD-Agent]\n"
            "  R --> G[Qlib门禁]\n"
            "  G --> A[六分析师/回测]\n"
        ),
    }
