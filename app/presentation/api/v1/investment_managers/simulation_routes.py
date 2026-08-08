from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flask import Blueprint, request
from flask_login import login_required

from app.core.logger import get_logger
from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_bool_param, parse_int_param

logger = get_logger(__name__)


def register_investment_manager_simulation_routes(
    blueprint: Blueprint,
    *,
    legacy: bool,
    enable_celery: bool,
    svc: Callable[[], Any],
    task_dispatcher: Any,
    task_message_store: Any,
) -> None:
    @blueprint.post("/investment-managers/simulate")
    @login_required
    def simulate_day():
        body = request.get_json(silent=True) or {}
        d = (body.get("date") or "").strip()[:10] or None
        lim = parse_int_param(body.get("universe_limit"), name="universe_limit", default=800, min_value=50)
        lim = min(lim, 800)
        want_async = parse_bool_param(body.get("async"), name="async", default=False)
        force_sync = parse_bool_param(request.args.get("sync"), name="sync", default=False)

        if enable_celery and want_async and not force_sync:
            try:
                from app.celery_app import celery as _celery
                from app.tasks.investment_manager_tasks import investment_managers_simulate_day

                if (
                    _celery is not None
                    and investment_managers_simulate_day is not None
                    and hasattr(investment_managers_simulate_day, "delay")
                ):
                    _, task_id, enqueued = task_dispatcher.dispatch(
                        investment_managers_simulate_day,
                        task_name="app.tasks.investment_manager_tasks.investment_managers_simulate_day",
                        kwargs={"nav_date": d, "universe_limit": int(lim)},
                        bucket_seconds=60,
                        ttl_seconds=900,
                    )
                    if not enqueued:
                        return ok_response(
                            data={
                                "mode": "async",
                                "task_id": task_id,
                                "deduplicated": True,
                                "label": task_dispatcher.get_task_label(
                                    "app.tasks.investment_manager_tasks.investment_managers_simulate_day"
                                ),
                            },
                            legacy_alias_key=None,
                            enable_legacy_alias=legacy,
                        )
                    task_message_store.push(
                        event="task_queued",
                        task_id=task_id,
                        task_name="app.tasks.investment_manager_tasks.investment_managers_simulate_day",
                        detail=f"已投递投资经理单日模拟（date={d or 'today'}）",
                        meta={"nav_date": d or "", "universe_limit": int(lim)},
                    )
                    return ok_response(
                        data={
                            "mode": "async",
                            "task_id": task_id,
                            "label": task_dispatcher.get_task_label(
                                "app.tasks.investment_manager_tasks.investment_managers_simulate_day"
                            ),
                            "message": "任务已提交，完成后请刷新收益榜或看消息中心。",
                        },
                        legacy_alias_key=None,
                        enable_legacy_alias=legacy,
                    )
                raise RuntimeError("celery_not_available")
            except Exception as e:
                logger.warning("investment_manager simulate_day async: %s", e)

        out = svc().simulate_day(nav_date=d, universe_limit=lim)
        return ok_response(data={**out, "mode": "sync"}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/investment-managers/quick-warmup")
    @login_required
    def quick_warmup():
        body = request.get_json(silent=True) or {}
        lim = parse_int_param(body.get("universe_limit"), name="universe_limit", default=800, min_value=50)
        lim = min(lim, 800)
        run_sched = parse_bool_param(body.get("run_deploy_schedule"), name="run_deploy_schedule", default=True)
        start = (body.get("schedule_start_date") or "2020-01-01").strip()[:10]
        bs = parse_int_param(body.get("schedule_batch_size"), name="schedule_batch_size", default=10, min_value=1)
        bs = min(bs, 50)
        asof = (body.get("asof_date") or "").strip()[:10] or None
        nav_d = (body.get("date") or "").strip()[:10] or None
        sync = parse_bool_param(request.args.get("sync"), name="sync", default=False)

        if enable_celery and not sync:
            try:
                from app.celery_app import celery as _celery
                from app.tasks.investment_manager_tasks import investment_managers_quick_warmup

                if (
                    _celery is not None
                    and investment_managers_quick_warmup is not None
                    and hasattr(investment_managers_quick_warmup, "delay")
                ):
                    _, task_id, enqueued = task_dispatcher.dispatch(
                        investment_managers_quick_warmup,
                        task_name="app.tasks.investment_manager_tasks.investment_managers_quick_warmup",
                        kwargs={
                            "run_deploy_schedule": run_sched,
                            "schedule_start_date": start,
                            "schedule_batch_size": int(bs),
                            "asof_date": asof,
                            "nav_date": nav_d,
                            "universe_limit": int(lim),
                        },
                        bucket_seconds=120,
                        ttl_seconds=1200,
                    )
                    if not enqueued:
                        return ok_response(
                            data={
                                "mode": "async",
                                "task_id": task_id,
                                "deduplicated": True,
                                "label": task_dispatcher.get_task_label(
                                    "app.tasks.investment_manager_tasks.investment_managers_quick_warmup"
                                ),
                            },
                            legacy_alias_key=None,
                            enable_legacy_alias=legacy,
                        )
                    task_message_store.push(
                        event="task_queued",
                        task_id=task_id,
                        task_name="app.tasks.investment_manager_tasks.investment_managers_quick_warmup",
                        detail="已投递投资经理快速预热（排期+单日模拟）",
                        meta={
                            "run_deploy_schedule": run_sched,
                            "universe_limit": int(lim),
                            "date": nav_d or "",
                        },
                    )
                    return ok_response(
                        data={
                            "mode": "async",
                            "task_id": task_id,
                            "label": task_dispatcher.get_task_label(
                                "app.tasks.investment_manager_tasks.investment_managers_quick_warmup"
                            ),
                            "message": "任务已提交；Worker 执行完后刷新收益榜查看成交笔数。",
                        },
                        legacy_alias_key=None,
                        enable_legacy_alias=legacy,
                    )
                raise RuntimeError("celery_not_available")
            except Exception as e:
                logger.warning("investment_manager quick_warmup async: %s", e)

        from app.tasks.investment_manager_tasks import run_investment_managers_quick_warmup

        out = run_investment_managers_quick_warmup(
            run_deploy_schedule=run_sched,
            schedule_start_date=start,
            schedule_batch_size=int(bs),
            asof_date=asof,
            nav_date=nav_d,
            universe_limit=int(lim),
        )
        return ok_response(data={**out, "mode": "sync"}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/investment-managers/deploy-schedule")
    @login_required
    def deploy_schedule():
        body = request.get_json(silent=True) or {}
        start = (body.get("start_date") or "2020-01-01").strip()[:10]
        bs = parse_int_param(body.get("batch_size"), name="batch_size", default=10, min_value=1)
        bs = min(bs, 50)
        asof = (body.get("asof_date") or "").strip()[:10] or None
        out = svc().apply_monthly_deploy_schedule(start_date=start, batch_size=bs, asof_date=asof)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/investment-managers/backfill")
    @login_required
    def backfill():
        body = request.get_json(silent=True) or {}
        start = (body.get("start_date") or "2020-01-01").strip()[:10]
        end = (body.get("end_date") or "").strip()[:10] or None
        lim = parse_int_param(body.get("universe_limit"), name="universe_limit", default=800, min_value=50)
        lim = min(lim, 800)
        sync = parse_bool_param(request.args.get("sync"), name="sync", default=False)

        if enable_celery and not sync:
            try:
                from app.celery_app import celery as _celery
                from app.tasks.investment_manager_tasks import investment_managers_backfill

                if (
                    _celery is not None
                    and investment_managers_backfill is not None
                    and hasattr(investment_managers_backfill, "delay")
                ):
                    _, task_id, enqueued = task_dispatcher.dispatch(
                        investment_managers_backfill,
                        task_name="app.tasks.investment_manager_tasks.investment_managers_backfill",
                        kwargs={
                            "start_date": start,
                            "end_date": end,
                            "universe_limit": int(lim),
                            "schedule_start_date": "2020-01-01",
                            "schedule_batch_size": 10,
                        },
                        bucket_seconds=300,
                        ttl_seconds=1800,
                    )
                    if not enqueued:
                        return ok_response(
                            data={
                                "mode": "async",
                                "task_id": task_id,
                                "deduplicated": True,
                                "label": task_dispatcher.get_task_label(
                                    "app.tasks.investment_manager_tasks.investment_managers_backfill"
                                ),
                            },
                            legacy_alias_key=None,
                            enable_legacy_alias=legacy,
                        )
                    task_message_store.push(
                        event="task_queued",
                        task_id=task_id,
                        task_name="app.tasks.investment_manager_tasks.investment_managers_backfill",
                        detail=f"已投递投资经理历史回放（{start} → {end or 'today'}）",
                        meta={"start_date": start, "end_date": end or "", "universe_limit": int(lim)},
                    )
                    return ok_response(
                        data={
                            "mode": "async",
                            "task_id": task_id,
                            "label": task_dispatcher.get_task_label(
                                "app.tasks.investment_manager_tasks.investment_managers_backfill"
                            ),
                            "message": "任务已提交，完成后可在消息中心查看，并刷新收益榜。",
                        },
                        legacy_alias_key=None,
                        enable_legacy_alias=legacy,
                    )
                raise RuntimeError("celery_not_available")
            except Exception as e:
                logger.warning("investment_manager backfill async: %s", e)

        out = svc().backfill(start_date=start, end_date=end, universe_limit=lim)
        return ok_response(data={**out, "mode": "sync"}, legacy_alias_key=None, enable_legacy_alias=legacy)
