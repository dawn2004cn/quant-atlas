from __future__ import annotations

"""Gate v2：从 RD bundle 抽取主因子任务，校验表达式非空与 IC 元数据（不执行 Qlib Dataset）。"""


import math
import re
from typing import Any

_IC_LAG_RE = re.compile(r"^ic[_\s]*lag[_\s]*(\d+)$", re.IGNORECASE)
_MAX_FORMULATION_LEN = 12_000


def _ic_lag1_from_metrics(metrics: dict[str, Any]) -> float | None:
    for k, v in metrics.items():
        m = _IC_LAG_RE.match(str(k).strip())
        if m and int(m.group(1)) == 1 and isinstance(v, (int, float)):
            return float(v)
    return None


def _pick_primary_factor_task(artifacts: list[Any]) -> dict[str, Any] | None:
    tasks = [a for a in artifacts if isinstance(a, dict) and a.get("kind") == "factor_task"]
    if not tasks:
        return None
    tasks.sort(key=lambda x: (-int(x.get("round_index") or 0), str(x.get("artifact_id") or "")))
    return tasks[0]


def evaluate_factor_expression_gate(bundle: dict[str, Any]) -> dict[str, Any]:
    """
    返回 ``factor_expression_gate`` 子结构，供 ``qlib_gate`` 合并。

    - 无 ``factor_task`` 或主任务无 ``factor_formulation``：``skipped=True``。
    - 否则检查：非空、长度上限、若 metrics 含 lag1 IC 则须为有限浮点。
    """
    arts = bundle.get("artifacts") or []
    if not isinstance(arts, list):
        return {
            "ok": True,
            "skipped": True,
            "message": "无 artifacts 列表",
        }
    primary = _pick_primary_factor_task(arts)
    if primary is None:
        return {
            "ok": True,
            "skipped": True,
            "message": "无 factor_task 产物",
        }
    formulation = str(primary.get("factor_formulation") or "").strip()
    metrics = primary.get("metrics") if isinstance(primary.get("metrics"), dict) else {}
    ic1 = _ic_lag1_from_metrics(metrics)

    checks = {
        "nonempty": len(formulation) > 0,
        "max_len_ok": len(formulation) <= _MAX_FORMULATION_LEN,
        "ic_lag1_finite": True if ic1 is None else (math.isfinite(ic1)),
    }
    ok = bool(checks["nonempty"] and checks["max_len_ok"] and checks["ic_lag1_finite"])
    out: dict[str, Any] = {
        "ok": ok,
        "skipped": False,
        "primary_artifact_id": primary.get("artifact_id"),
        "factor_name": primary.get("factor_name"),
        "formulation_len": len(formulation),
        "formulation_preview": formulation[:240],
        "checks": checks,
        "ic_lag1": ic1,
    }
    if not ok:
        reasons: list[str] = []
        if not checks["nonempty"]:
            reasons.append("factor_formulation 为空")
        if not checks["max_len_ok"]:
            reasons.append(f"表达式超过 {_MAX_FORMULATION_LEN} 字符")
        if not checks["ic_lag1_finite"]:
            reasons.append("ic_lag1 非有限数值")
        out["message"] = "; ".join(reasons)
    return out
