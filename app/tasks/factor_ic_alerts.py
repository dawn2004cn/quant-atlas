from __future__ import annotations
"""RD 注册因子 IC 巡检：定时扫描弱信号并写入消息中心（与 Celery Beat 配合）。"""


import uuid
from typing import Any

import logging

from ..application.services.factor.factor_catalog_service import FactorCatalogService
from ..config import BASE_DIR
from ..core.logger import get_logger
from ..core.runtime_config import get_runtime_bool, get_runtime_float
from .task_wiring import get_task_message_store



logger = get_logger(__name__)


def run_factor_ic_monitor() -> dict[str, Any]:
    """同步执行 IC 摘要；弱信号时推送 ``factor_ic_alert`` 并返回 ``_suppress_default_task_message`` 避免重复条。"""
    if not get_runtime_bool("ENABLE_RD_AGENT", False):
        return {
            "ok": True,
            "skipped": True,
            "reason": "ENABLE_RD_AGENT 未开启",
            "weak_ic_lag1_count": 0,
        }
    ic_thr = get_runtime_float("FACTOR_IC_WARN", 0.05)
    svc = FactorCatalogService(base_dir=BASE_DIR)
    summary = svc.monitor_summary(ic_warn_threshold=ic_thr, limit_runs=40, limit_factors=600)
    weak = int(summary.get("weak_ic_lag1_count") or 0)
    mean_ic = summary.get("mean_abs_ic_lag1")
    alerts = summary.get("alerts") or []
    out: dict[str, Any] = {
        "ok": True,
        "ic_warn_threshold": ic_thr,
        "weak_ic_lag1_count": weak,
        "mean_abs_ic_lag1": mean_ic,
        "factors_with_ic_decay": summary.get("factors_with_ic_decay"),
        "alerts_preview": alerts[:5],
        "autopublish_tail_merged": summary.get("autopublish_tail_merged", 0),
    }
    if weak > 0:
        try:
            lines = [a.get("message", "") for a in alerts[:8] if isinstance(a, dict)]
            detail = f"弱 |IC| 因子 {weak} 个（阈值={ic_thr}）。\n" + "\n".join(lines)[:1800]
            get_task_message_store().push(
                event="factor_ic_alert",
                task_id=f"ic-{uuid.uuid4().hex[:12]}",
                task_name="app.tasks.factor_ic_alerts.factor_ic_monitor_tick",
                detail=detail,
                meta={
                    "weak_ic_lag1_count": weak,
                    "mean_abs_ic_lag1": mean_ic,
                    "ic_warn_threshold": ic_thr,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("factor_ic alert push failed: %s", exc)
        out["_suppress_default_task_message"] = True
    else:
        out["skipped"] = True
        out["reason"] = "未发现低于阈值的弱 IC 因子"
    return out


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(name="app.tasks.factor_ic_alerts.factor_ic_monitor_tick")
    def factor_ic_monitor_tick() -> dict[str, Any]:
        return run_factor_ic_monitor()

else:
    factor_ic_monitor_tick = None  # type: ignore[misc, assignment]
