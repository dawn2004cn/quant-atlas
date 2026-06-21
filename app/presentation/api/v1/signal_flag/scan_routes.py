"""Signal-flag market scan route."""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_bool_param, parse_int_param
from app.presentation.api.v1.signal_flag._helpers import parse_signal_flag_max_stocks
from app.presentation.api.v1.signal_flag.runtime import SignalFlagRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


def register_signal_flag_scan_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: SignalFlagRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.post("/signal-flag/scan")
    @login_required
    def signal_flag_scan():
        """全市场信号扫描：异步（Celery）优先，否则同步回退。"""
        body = request.get_json(silent=True) or {}
        pool_raw = (body.get("pool_date") or request.args.get("pool_date") or "").strip()[:10]
        pool_date = pool_raw or datetime.now().strftime("%Y-%m-%d")
        max_stocks = parse_signal_flag_max_stocks(body)
        lookback = parse_int_param(body.get("lookback_days"), name="lookback_days", default=160, min_value=40)
        lookback = min(lookback, 500)
        sync = parse_bool_param(request.args.get("sync"), name="sync", default=False)
        pool_hint = pool_date

        td = runtime.task_dispatcher
        tms = runtime.task_message_store

        if runtime.enable_celery and not sync and td is not None:
            try:
                from app.celery_app import celery as _celery
                from app.tasks.signal_flag_tasks import signal_flag_pool_scan

                if (
                    _celery is not None
                    and signal_flag_pool_scan is not None
                    and hasattr(signal_flag_pool_scan, "delay")
                ):
                    _, task_id, enqueued = td.dispatch(
                        signal_flag_pool_scan,
                        task_name="app.tasks.signal_flag_tasks.signal_flag_pool_scan",
                        kwargs={
                            "pool_date": pool_date,
                            "max_stocks": max_stocks,
                            "lookback_days": lookback,
                        },
                        bucket_seconds=60,
                        ttl_seconds=900,
                    )
                    if not enqueued:
                        return ok_response(
                            data={
                                "mode": "async",
                                "task_id": task_id,
                                "deduplicated": True,
                                "label": td.get_task_label("app.tasks.signal_flag_tasks.signal_flag_pool_scan"),
                                "pool_date": pool_hint,
                            },
                            legacy_alias_key=None,
                            enable_legacy_alias=legacy,
                        )
                    meta: dict = {
                        "pool_date": pool_hint,
                        "max_stocks": max_stocks,
                        "lookback_days": lookback,
                    }
                    if getattr(current_user, "is_authenticated", False):
                        meta["user_id"] = getattr(current_user, "id", None)
                    if tms is not None:
                        tms.push(
                            event="task_queued",
                            task_id=task_id,
                            task_name="app.tasks.signal_flag_tasks.signal_flag_pool_scan",
                            detail=(
                                f"已投递信号旗扫描（{pool_hint}，"
                                + ("全市场(缓存上限)" if max_stocks == 0 else f"最多 {max_stocks} 只")
                                + "）"
                            ),
                            meta=meta,
                        )
                    return ok_response(
                        data={
                            "mode": "async",
                            "task_id": task_id,
                            "label": td.get_task_label("app.tasks.signal_flag_tasks.signal_flag_pool_scan"),
                            "message": "任务已提交，Worker 执行完成后可在消息中心查看结果，并刷新当日股票池。",
                            "pool_date": pool_hint,
                        },
                        legacy_alias_key=None,
                        enable_legacy_alias=legacy,
                    )
                raise RuntimeError("celery_not_available")
            except Exception as exc:  # noqa: BLE001
                logger.warning("signal_flag scan celery enqueue failed, sync fallback: %s", exc)

        summary = runtime.require_service().run_scan(
            market=MarketCode.CN,
            pool_date=pool_date,
            max_stocks=max_stocks,
            lookback_days=lookback,
        )
        payload = asdict(summary)
        tid = f"sync-{uuid.uuid4().hex[:12]}"
        if tms is not None:
            tms.push(
                event="task_succeeded",
                task_id=tid,
                task_name="inline.signal_flag_pool_scan",
                detail=(payload.get("message") or "同步扫描完成")[:2000],
                meta={**payload, "mode": "sync"},
            )
        return ok_response(
            data={**payload, "mode": "sync", "task_id": tid},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
