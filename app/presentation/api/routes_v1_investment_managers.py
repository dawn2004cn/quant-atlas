from __future__ import annotations
"""API v1：投资经理（100 策略一一映射）模拟与排行榜。"""


from datetime import datetime

from flask import Blueprint, Response, request
from flask_login import login_required


from ...application.errors import NotFoundError
from ...core.middleware.request_context import require_authenticated_user_id
from .common import ok_response
from .route_deps import SocialRouteDeps, build_social_route_deps, require_investment_manager_service
from .request_parsers import parse_bool_param, parse_int_param
from .v1_context import ApiV1Context


from app.core.logger import get_logger
from app.core.registry import register_routes

logger = get_logger(__name__)


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="investment_manager", context="misc", description="投资经理（100 策略一一映射）模拟与排行榜")
def register_investment_manager_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None = None,
    *,
    deps: SocialRouteDeps | None = None,
) -> None:
    route_deps = deps or build_social_route_deps(ctx)

    def _svc():
        return require_investment_manager_service(route_deps)

    legacy = route_deps.enable_legacy_response_fields
    enable_celery = route_deps.enable_celery
    task_dispatcher = route_deps.task_dispatcher
    task_message_store = route_deps.task_message_store

    @blueprint.post("/investment-managers/seed")
    @login_required
    def seed_managers():
        out = _svc().ensure_seed_managers()
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/investment-managers/deploy")
    @login_required
    def deploy_batch():
        body = request.get_json(silent=True) or {}
        bs = parse_int_param(body.get("batch_size"), name="batch_size", default=10, min_value=1)
        bs = min(bs, 30)
        out = _svc().deploy_next_batch(batch_size=bs)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/investment-managers")
    @login_required
    def list_managers():
        items = _svc().list_managers()
        return ok_response(
            data={"items": items, "count": len(items)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/investment-managers/leaderboard")
    @login_required
    def leaderboard():
        period = (request.args.get("period") or "day").strip().lower()
        items = _svc().leaderboard(period=period)

        # Calculate aggregate stats
        total_trades = 0
        managers_with_trades = 0
        try:
            stats = _svc().trade_stats_by_manager()
            stat_rows = stats.values() if isinstance(stats, dict) else stats
            total_trades = sum((s.get("trade_count", 0) if isinstance(s, dict) else int(s[1])) for s in stat_rows)
            managers_with_trades = len([s for s in stat_rows if (s.get("trade_count", 0) if isinstance(s, dict) else int(s[1])) > 0])
        except Exception as exc:
            logger.warning("leaderboard trade_stats aggregate failed: %s", exc)

        return ok_response(
            data={"items": items, "count": len(items), "aggregate": {"total_trades": total_trades, "managers_with_trades": managers_with_trades}},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/investment-managers/me")
    @login_required
    def my_manager():
        try:
            items = _svc().list_managers()
            for m in items:
                if str(m.get("user_id")) == str(_uid()):
                    return ok_response(data=m, legacy_alias_key=None, enable_legacy_alias=legacy)
        except Exception as exc:
            logger.warning("my_manager list_managers failed: %s", exc)
        return ok_response(data={"id": "me", "name": "My Manager", "user_id": str(_uid())}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/investment-managers/<manager_id>")
    @login_required
    def manager_detail(manager_id: str):
        d = (request.args.get("date") or "").strip()[:10] or datetime.now().strftime("%Y-%m-%d")
        out = _svc().manager_detail(manager_id, date=d)
        if out is None:
            raise NotFoundError(
                "investment_manager_not_found",
                details={"manager_id": manager_id},
            )
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/investment-managers/<manager_id>/trades.csv")
    @login_required
    def export_manager_trades(manager_id: str):
        filename, data = _svc().export_manager_trades_csv(manager_id)
        return Response(
            data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

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
                                "label": task_dispatcher.get_task_label("app.tasks.investment_manager_tasks.investment_managers_simulate_day"),
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
                            "label": task_dispatcher.get_task_label("app.tasks.investment_manager_tasks.investment_managers_simulate_day"),
                            "message": "任务已提交，完成后请刷新收益榜或看消息中心。",
                        },
                        legacy_alias_key=None,
                        enable_legacy_alias=legacy,
                    )
                raise RuntimeError("celery_not_available")
            except Exception as e:
                logger.warning("routes_v1_investment_managers.py.register_investment_manager_routes: %s", e)

        out = _svc().simulate_day(nav_date=d, universe_limit=lim)
        return ok_response(data={**out, "mode": "sync"}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/investment-managers/quick-warmup")
    @login_required
    def quick_warmup():
        """入市排期（可选）+ 单日模拟：默认走 Celery，尽快出成交/净值。"""
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
                                "label": task_dispatcher.get_task_label("app.tasks.investment_manager_tasks.investment_managers_quick_warmup"),
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
                            "label": task_dispatcher.get_task_label("app.tasks.investment_manager_tasks.investment_managers_quick_warmup"),
                            "message": "任务已提交；Worker 执行完后刷新收益榜查看成交笔数。",
                        },
                        legacy_alias_key=None,
                        enable_legacy_alias=legacy,
                    )
                raise RuntimeError("celery_not_available")
            except Exception as e:
                logger.warning("routes_v1_investment_managers.py.register_investment_manager_routes: %s", e)

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
        out = _svc().apply_monthly_deploy_schedule(start_date=start, batch_size=bs, asof_date=asof)
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
                                "label": task_dispatcher.get_task_label("app.tasks.investment_manager_tasks.investment_managers_backfill"),
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
                            "label": task_dispatcher.get_task_label("app.tasks.investment_manager_tasks.investment_managers_backfill"),
                            "message": "任务已提交，完成后可在消息中心查看，并刷新收益榜。",
                        },
                        legacy_alias_key=None,
                        enable_legacy_alias=legacy,
                    )
                raise RuntimeError("celery_not_available")
            except Exception as e:
                # 异步不可用则回退同步
                logger.warning("routes_v1_investment_managers.py.register_investment_manager_routes: %s", e)

        out = _svc().backfill(start_date=start, end_date=end, universe_limit=lim)
        return ok_response(data={**out, "mode": "sync"}, legacy_alias_key=None, enable_legacy_alias=legacy)

    # -------------------------
    # 用户赛跑（预留接口）
    # -------------------------
    @blueprint.post("/investment-managers/user/set-cash")
    @login_required
    def user_set_cash():
        body = request.get_json(silent=True) or {}
        account_id = (body.get("account_id") or "USER").strip()
        name = (body.get("name") or "我的账户").strip()
        cash = float(body.get("cash") or 0)
        out = _svc().user_set_cash(account_id=account_id, name=name, cash=cash)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/investment-managers/user/import-trades")
    @login_required
    def user_import_trades():
        body = request.get_json(silent=True) or {}
        account_id = (body.get("account_id") or "USER").strip()
        name = (body.get("name") or "我的账户").strip()
        cash = float(body.get("cash") or 10_000_000)
        trades = body.get("trades") or []
        out = _svc().user_import_trades(account_id=account_id, name=name, cash=cash, trades=trades)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/investment-managers/user/<account_id>/trades.csv")
    @login_required
    def export_user_trades(account_id: str):
        filename, data = _svc().export_user_trades_csv(account_id)
        return Response(
            data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

