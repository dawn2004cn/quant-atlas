from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""RD-Agent 注册因子目录：供 `/api/factor/list` 与量化实验室前端消费。"""


import json
import re
from pathlib import Path
from typing import Any

from app.modules.system.services.helpers.rdagent_access import create_rdagent_artifact_registry
from app.config import BASE_DIR
from app.core.runtime_config import get_runtime_int


_IC_LAG_RE = re.compile(r"^ic[_\s]*lag[_\s]*(\d+)$", re.IGNORECASE)


class FactorCatalogService:
    def __init__(self, *, base_dir: Path | None = None) -> None:
        self._base = Path(base_dir or BASE_DIR).resolve()
        self._registry = create_rdagent_artifact_registry(self._base)

    def list_autopublish_tail(self, *, limit: int = 120) -> GenericResponseDTO:
        """读取 ``config/factor_catalog/autopublish.jsonl`` 末尾若干行（RD 成功注册后追加）。"""
        path = self._base / "config" / "factor_catalog" / "autopublish.jsonl"
        lim = max(1, min(int(limit), 500))
        if not path.is_file():
            return {"records": [], "total": 0, "path": str(path)}
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return {"records": [], "total": 0, "path": str(path)}
        tail = [ln for ln in lines[-lim:] if ln.strip()]
        rows: list[dict[str, Any]] = []
        for ln in tail:
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
        return {"records": rows, "total": len(rows), "path": str(path.resolve())}

    def _merge_autopublish_factors_for_monitor(
        self,
        factors: list[dict[str, Any]],
        *,
        tail_n: int,
        limit_factors: int,
    ) -> list[dict[str, Any]]:
        """把 ``autopublish.jsonl`` 尾部记录并入 IC 巡检列表（按 ``artifact_id`` 去重）。"""
        if tail_n <= 0:
            return factors[:limit_factors]
        ap = self.list_autopublish_tail(limit=min(tail_n, 500)).get("records") or []
        seen = {str(f.get("artifact_id") or "").strip() for f in factors if f.get("artifact_id")}
        out = list(factors)
        for row in ap:
            if len(out) >= limit_factors:
                break
            if not isinstance(row, dict):
                continue
            aid = str(row.get("artifact_id") or "").strip()
            if not aid or aid in seen:
                continue
            metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
            out.append(
                {
                    "artifact_id": aid,
                    "run_id": row.get("run_id"),
                    "kind": "factor_task",
                    "version": 1,
                    "round_index": row.get("round_index"),
                    "factor_name": row.get("factor_name"),
                    "factor_formulation": row.get("factor_formulation"),
                    "factor_description": row.get("factor_description"),
                    "ic_decay": self._ic_decay_from_metrics(metrics),
                    "factor_importance": self._importance_from_metrics(metrics),
                    "metrics": metrics,
                    "source": "autopublish_jsonl",
                },
            )
            seen.add(aid)
        return out[:limit_factors]

    @staticmethod
    def _ic_decay_from_metrics(metrics: dict[str, Any]) -> list[dict[str, float]]:
        decay: list[dict[str, float]] = []
        for k, v in metrics.items():
            m = _IC_LAG_RE.match(str(k).strip())
            if m and isinstance(v, (int, float)):
                decay.append({"lag": int(m.group(1)), "ic": float(v)})
        decay.sort(key=lambda x: x["lag"])
        return decay

    @staticmethod
    def _importance_from_metrics(metrics: dict[str, Any], *, top_n: int = 20) -> list[dict[str, Any]]:
        items: list[tuple[str, float]] = []
        for k, v in metrics.items():
            if isinstance(v, (int, float)) and str(k).strip() and not str(k).startswith("_"):
                items.append((str(k), abs(float(v))))
        items.sort(key=lambda x: -x[1])
        return [{"feature": a, "importance": round(b, 6)} for a, b in items[:top_n]]

    def list_factors(
        self,
        *,
        run_id: str | None = None,
        limit_runs: int = 30,
        limit_factors: int = 800,
    ) -> GenericResponseDTO:
        """扁平化 registry 中的因子任务与代码片段，附 IC 衰减与指标重要性（来自 ``qlib_metrics_series``）。"""
        runs: list[dict[str, Any]] = []
        if run_id:
            bundle = self._registry.get_run_bundle(run_id.strip())
            if bundle:
                runs = [bundle]
        else:
            idx = self._registry.list_registry_index(limit=limit_runs)
            for row in idx:
                rid = str(row.get("run_id") or "").strip()
                if not rid:
                    continue
                b = self._registry.get_run_bundle(rid)
                if b:
                    runs.append(b)

        factors: list[dict[str, Any]] = []
        for bundle in runs:
            rid = str(bundle.get("run_id") or "")
            for a in bundle.get("artifacts") or []:
                kind = a.get("kind")
                if kind not in ("factor_task", "factor_code"):
                    continue
                metrics = a.get("metrics") if isinstance(a.get("metrics"), dict) else {}
                entry: dict[str, Any] = {
                    "artifact_id": a.get("artifact_id"),
                    "run_id": rid,
                    "kind": kind,
                    "version": a.get("version"),
                    "round_index": a.get("round_index"),
                    "factor_name": a.get("factor_name"),
                    "factor_formulation": a.get("factor_formulation"),
                    "factor_description": a.get("factor_description"),
                    "file": a.get("file"),
                    "ic_decay": self._ic_decay_from_metrics(metrics),
                    "factor_importance": self._importance_from_metrics(metrics),
                    "metrics": metrics,
                }
                if kind == "factor_code":
                    preview = a.get("code_preview")
                    if isinstance(preview, str):
                        entry["code_preview"] = preview[:2000]
                factors.append(entry)
                if len(factors) >= limit_factors:
                    break
            if len(factors) >= limit_factors:
                break

        index = self._registry.list_registry_index(limit=limit_runs)
        return {
            "factors": factors,
            "runs_index": index,
            "total": len(factors),
        }

    def monitor_summary(
        self,
        *,
        ic_warn_threshold: float = 0.05,
        limit_runs: int = 30,
        limit_factors: int = 500,
        autopublish_tail: int | None = None,
    ) -> GenericResponseDTO:
        """聚合最近注册因子上的 IC 衰减，给出弱 IC 计数与可读警报（供仪表盘 / 消息联动）。

        若 ``autopublish_tail`` 未传，则读环境变量 ``FACTOR_IC_AUTOPUBLISH_TAIL``（默认 0）：
        >0 时把 ``config/factor_catalog/autopublish.jsonl`` 尾部若干行并入巡检（去重），
        避免 ``limit_runs`` 截断导致「已导出因子」不参与弱 IC 扫描。
        """
        bundle = self.list_factors(run_id=None, limit_runs=limit_runs, limit_factors=limit_factors)
        factors: list[dict[str, Any]] = list(bundle.get("factors") or [])
        tail_n = autopublish_tail
        if tail_n is None:
            tail_n = get_runtime_int("FACTOR_IC_AUTOPUBLISH_TAIL", 0)
        tail_n = max(0, min(int(tail_n), 500))
        if tail_n > 0:
            factors = self._merge_autopublish_factors_for_monitor(
                factors,
                tail_n=tail_n,
                limit_factors=limit_factors,
            )
        alerts: list[dict[str, Any]] = []
        weak_ic = 0
        lag1_values: list[float] = []

        for f in factors:
            if f.get("kind") != "factor_task":
                continue
            decay = f.get("ic_decay") or []
            if not decay:
                continue
            lag_ic: float | None = None
            for row in decay:
                if int(row.get("lag", -1)) == 1:
                    lag_ic = float(row.get("ic") or 0.0)
                    break
            if lag_ic is None:
                lag_ic = float(decay[0].get("ic") or 0.0)
            lag1_values.append(lag_ic)
            if abs(lag_ic) < ic_warn_threshold:
                weak_ic += 1
                alerts.append(
                    {
                        "level": "warning",
                        "code": "low_ic_lag1",
                        "message": (
                            f"因子 {f.get('factor_name') or f.get('artifact_id')} "
                            f"|IC|={abs(lag_ic):.4f} < {ic_warn_threshold}"
                        ),
                        "run_id": f.get("run_id"),
                        "artifact_id": f.get("artifact_id"),
                    }
                )

        mean_abs_ic = (
            sum(abs(v) for v in lag1_values) / len(lag1_values) if lag1_values else None
        )
        return {
            "ic_warn_threshold": ic_warn_threshold,
            "factor_task_rows": len([x for x in factors if x.get("kind") == "factor_task"]),
            "factors_with_ic_decay": len(lag1_values),
            "weak_ic_lag1_count": weak_ic,
            "mean_abs_ic_lag1": round(mean_abs_ic, 6) if mean_abs_ic is not None else None,
            "alerts": alerts[:50],
            "runs_index": bundle.get("runs_index") or [],
            "autopublish_tail_merged": tail_n,
        }
