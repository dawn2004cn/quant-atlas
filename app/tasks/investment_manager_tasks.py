from __future__ import annotations
"""投资经理：Celery 异步任务（历史回/ 单日模拟 / 快速预热）"""


from typing import Any

from ..modules.execution.services.investment_manager_service import InvestmentManagerService
from ..celery_app import celery as _celery
from ..config import get_settings
from ..core.logger import get_logger
from ..infrastructure.repositories.deps import (
    create_investment_manager_repository,
    create_signal_flag_pool_repository,
    create_stock_cache,
)
from .task_wiring import get_task_message_store

logger = get_logger(__name__)


def _svc() -> InvestmentManagerService:
    s = get_settings()
    repo = create_investment_manager_repository(s)
    sfp = create_signal_flag_pool_repository(s)
    return InvestmentManagerService(repo, stock_cache=create_stock_cache(), signal_flag_pool=sfp)


def _push_done(task_id: str, payload: dict[str, Any]) -> None:
    try:
        get_task_message_store().push(
            event="task_succeeded",
            task_id=task_id,
            task_name="app.tasks.investment_manager_tasks.investment_managers_backfill",
            detail=("投资经理历史回放完成" if payload.get("ok") else "投资经理历史回放失败")[:2000],
            meta={
                "start_date": payload.get("start_date"),
                "end_date": payload.get("end_date"),
                "days": payload.get("days"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("investment_managers_backfill message push skipped: %s", exc)


def _push_quick_warmup_done(task_id: str, payload: dict[str, Any]) -> None:
    sim = payload.get("simulate") or {}
    ok = bool(payload.get("ok")) and bool(sim.get("ok"))
    try:
        get_task_message_store().push(
            event="task_succeeded",
            task_id=task_id,
            task_name="app.tasks.investment_manager_tasks.investment_managers_quick_warmup",
            detail=(
                f"投资经理快速预热完成：nav_date={sim.get('nav_date')}, simulated={sim.get('simulated')}"
                if ok
                else "投资经理快速预热失败"
            )[:2000],
            meta={
                "nav_date": sim.get("nav_date"),
                "simulated": sim.get("simulated"),
                "universe": sim.get("universe"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("investment_managers_quick_warmup message push skipped: %s", exc)


def _push_simulate_done(task_id: str, payload: dict[str, Any]) -> None:
    ok = bool(payload.get("ok"))
    try:
        get_task_message_store().push(
            event="task_succeeded",
            task_id=task_id,
            task_name="app.tasks.investment_manager_tasks.investment_managers_simulate_day",
            detail=(
                f"投资经理单日模拟完成：{payload.get('nav_date')}，simulated={payload.get('simulated')}"
                if ok
                else "投资经理单日模拟失败"
            )[:2000],
            meta={
                "nav_date": payload.get("nav_date"),
                "simulated": payload.get("simulated"),
                "universe": payload.get("universe"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("investment_managers_simulate_day message push skipped: %s", exc)


def run_investment_managers_quick_warmup(
    *,
    run_deploy_schedule: bool = True,
    schedule_start_date: str = "2020-01-01",
    schedule_batch_size: int = 10,
    asof_date: str | None = None,
    nav_date: str | None = None,
    universe_limit: int = 800,
) -> dict[str, Any]:
    """Sync: optional deploy schedule + single-day simulation."""
    svc = _svc()
    schedule_out: dict[str, Any] | None = None
    if run_deploy_schedule:
        schedule_out = svc.apply_monthly_deploy_schedule(
            start_date=str(schedule_start_date)[:10],
            batch_size=int(schedule_batch_size),
            asof_date=(str(asof_date).strip()[:10] if asof_date else "") or None,
        )
    sim = svc.simulate_day(nav_date=nav_date, universe_limit=int(universe_limit))
    return {"ok": True, "schedule": schedule_out, "simulate": sim}


def run_investment_managers_simulate_day(
    *,
    nav_date: str | None = None,
    universe_limit: int = 800,
) -> dict[str, Any]:
    svc = _svc()
    return svc.simulate_day(nav_date=nav_date, universe_limit=int(universe_limit))


def run_post_close_signal_then_managers(
    *,
    pool_date: str | None = None,
    max_stocks: int = 800,
    lookback_days: int = 160,
    run_deploy_schedule: bool = True,
    schedule_start_date: str = "2020-01-01",
    schedule_batch_size: int = 10,
    asof_date: str | None = None,
    nav_date: str | None = None,
    universe_limit: int = 800,
) -> dict[str, Any]:
    """先同步跑信号旗落库，再跑投资经理排期+模拟（供 Beat 与运维同序调用，避免池未写出就模拟）"""
    from app.tasks.signal_flag_tasks import run_signal_flag_scan_sync

    scan = run_signal_flag_scan_sync(
        pool_date=pool_date,
        max_stocks=int(max_stocks),
        lookback_days=int(lookback_days),
    )
    warm = run_investment_managers_quick_warmup(
        run_deploy_schedule=bool(run_deploy_schedule),
        schedule_start_date=schedule_start_date,
        schedule_batch_size=int(schedule_batch_size),
        asof_date=asof_date,
        nav_date=nav_date,
        universe_limit=int(universe_limit),
    )
    sim_ok = bool((warm.get("simulate") or {}).get("ok"))
    return {
        "ok": bool(warm.get("ok")) and sim_ok,
        "signal_flag_scan": scan,
        "warmup": warm,
    }


def _push_pipeline_done(task_id: str, payload: dict[str, Any]) -> None:
    scan = payload.get("signal_flag_scan") or {}
    warm = payload.get("warmup") or {}
    sim = warm.get("simulate") or {}
    ok = bool(payload.get("ok"))
    try:
        get_task_message_store().push(
            event="task_succeeded",
            task_id=task_id,
            task_name="app.tasks.investment_manager_tasks.post_close_signal_then_managers",
            detail=(
                f"收盘链：信号旗写{scan.get('pool_date')} "
                f"hits={scan.get('hits')}；经理模nav={sim.get('nav_date')} simulated={sim.get('simulated')}"
                if ok
                else "收盘链：信号旗或经理模拟未全部成功"
            )[:2000],
            meta={
                "pool_date": scan.get("pool_date"),
                "signal_flag_hits": scan.get("hits"),
                "nav_date": sim.get("nav_date"),
                "signal_flag_codes": sim.get("signal_flag_codes"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("post_close_signal_then_managers message push skipped: %s", exc)


if _celery is not None:

    @_celery.task(name="app.tasks.investment_manager_tasks.investment_managers_backfill")
    def investment_managers_backfill(
        start_date: str = "2020-01-01",
        end_date: str | None = None,
        universe_limit: int = 800,
        schedule_start_date: str = "2020-01-01",
        schedule_batch_size: int = 10,
    ) -> dict[str, Any]:
        from celery import current_task

        req = getattr(current_task, "request", None)
        task_id = str(getattr(req, "id", "") or "investment-managers-backfill")
        try:
            svc = _svc()
            svc.apply_monthly_deploy_schedule(
                start_date=schedule_start_date,
                batch_size=int(schedule_batch_size),
                asof_date=end_date or "",
            )
            out = svc.backfill(start_date=start_date, end_date=end_date, universe_limit=int(universe_limit))
            _push_done(task_id, out)
            out["_suppress_default_task_message"] = True
            return out
        except Exception:
            logger.exception("investment_managers_backfill failed")
            raise

    @_celery.task(name="app.tasks.investment_manager_tasks.investment_managers_quick_warmup")
    def investment_managers_quick_warmup(
        run_deploy_schedule: bool = True,
        schedule_start_date: str = "2020-01-01",
        schedule_batch_size: int = 10,
        asof_date: str | None = None,
        nav_date: str | None = None,
        universe_limit: int = 800,
    ) -> dict[str, Any]:
        """入市排期（可选）+ 单日模拟，用于快速在收益榜看到成交与净值"""
        from celery import current_task

        req = getattr(current_task, "request", None)
        task_id = str(getattr(req, "id", "") or "investment-managers-quick-warmup")
        try:
            out = run_investment_managers_quick_warmup(
                run_deploy_schedule=bool(run_deploy_schedule),
                schedule_start_date=schedule_start_date,
                schedule_batch_size=int(schedule_batch_size),
                asof_date=asof_date,
                nav_date=nav_date,
                universe_limit=int(universe_limit),
            )
            _push_quick_warmup_done(task_id, out)
            out["_suppress_default_task_message"] = True
            return out
        except Exception:
            logger.exception("investment_managers_quick_warmup failed")
            raise

    @_celery.task(name="app.tasks.investment_manager_tasks.investment_managers_simulate_day")
    def investment_managers_simulate_day(
        nav_date: str | None = None,
        universe_limit: int = 800,
    ) -> dict[str, Any]:
        from celery import current_task

        req = getattr(current_task, "request", None)
        task_id = str(getattr(req, "id", "") or "investment-managers-simulate-day")
        try:
            out = run_investment_managers_simulate_day(nav_date=nav_date, universe_limit=int(universe_limit))
            _push_simulate_done(task_id, out)
            out["_suppress_default_task_message"] = True
            return out
        except Exception:
            logger.exception("investment_managers_simulate_day failed")
            raise

    @_celery.task(name="app.tasks.investment_manager_tasks.post_close_signal_then_managers")
    def post_close_signal_then_managers(
        pool_date: str | None = None,
        max_stocks: int = 800,
        lookback_days: int = 160,
        run_deploy_schedule: bool = True,
        schedule_start_date: str = "2020-01-01",
        schedule_batch_size: int = 10,
        asof_date: str | None = None,
        nav_date: str | None = None,
        universe_limit: int = 800,
    ) -> dict[str, Any]:
        """Beat：先信号旗全市场扫描落库，再入市排期+单日模拟"""
        from celery import current_task

        req = getattr(current_task, "request", None)
        task_id = str(getattr(req, "id", "") or "post-close-signal-then-managers")
        try:
            out = run_post_close_signal_then_managers(
                pool_date=pool_date,
                max_stocks=int(max_stocks),
                lookback_days=int(lookback_days),
                run_deploy_schedule=bool(run_deploy_schedule),
                schedule_start_date=schedule_start_date,
                schedule_batch_size=int(schedule_batch_size),
                asof_date=asof_date,
                nav_date=nav_date,
                universe_limit=int(universe_limit),
            )
            _push_pipeline_done(task_id, out)
            out["_suppress_default_task_message"] = True
            return out
        except Exception:
            logger.exception("post_close_signal_then_managers failed")
            raise

else:
    investment_managers_backfill = None  # type: ignore[misc, assignment]
    investment_managers_quick_warmup = None  # type: ignore[misc, assignment]
    investment_managers_simulate_day = None  # type: ignore[misc, assignment]
    post_close_signal_then_managers = None  # type: ignore[misc, assignment]
