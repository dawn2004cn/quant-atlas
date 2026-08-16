from __future__ import annotations

"""Celery application bootstrap for Quant Atlas."""


from typing import Any

# Ensure .env is loaded BEFORE any get_runtime() calls so that
# CELERY_BROKER_URL / CELERY_RESULT_BACKEND / REDIS_URL etc. are available.
from .core.runtime_config import _load_dotenv_if_present

_load_dotenv_if_present()

from .core.celery_ext import BeatRegistry
from .core.logger import get_logger
from .core.runtime_config import get_runtime, get_runtime_bool, get_runtime_int

logger = get_logger(__name__)

try:
    from celery import Celery
    from celery.schedules import crontab
    from celery.signals import task_failure, task_postrun, task_prerun, worker_process_init
except ImportError:
    Celery = None  # type: ignore[misc, assignment]
    crontab = None  # type: ignore[misc, assignment]
    task_failure = None  # type: ignore[misc, assignment]
    task_postrun = None  # type: ignore[misc, assignment]
    task_prerun = None  # type: ignore[misc, assignment]
    worker_process_init = None  # type: ignore[misc, assignment]
    logger.warning("celery not installed; async tasks are unavailable.")


def _broker_url() -> str:
    url = get_runtime("CELERY_BROKER_URL", "")
    if not url:
        raise RuntimeError(
            "CELERY_BROKER_URL not set. "
            "Configure CELERY_BROKER_URL in .env or environment (e.g. redis://host:6379/0)"
        )
    return url


def _result_backend() -> str:
    return get_runtime("CELERY_RESULT_BACKEND", "") or _broker_url()


def _build_beat_schedule() -> dict[str, Any]:
    """Build beat schedule from BeatRegistry. All tasks register declaratively."""
    assert crontab is not None

    BeatRegistry.clear()

    # -- BASIC_DATA_LONGHU_BEAT --
    if get_runtime("BASIC_DATA_LONGHU_BEAT", "1") == "1":
        BeatRegistry.register("basic-data-longhu-daily", "app.tasks.market_tasks.scheduled_longhu", crontab(hour=17, minute=5), description="longhu data update", queue="default")
        BeatRegistry.register("basic-data-indices-daily", "app.tasks.market_tasks.scheduled_indices_sync", crontab(hour=15, minute=40), description="indices sync", queue="default")

    # -- BASIC_DATA_YANBAO_BEAT --
    if get_runtime("BASIC_DATA_YANBAO_BEAT", "1") == "1":
        BeatRegistry.register("basic-data-yanbao-daily", "app.tasks.market_tasks.scheduled_yanbao", crontab(hour=6, minute=5), description="yanbao data update", queue="default")

    # -- NEWS_DAILY_BEAT --
    if get_runtime("NEWS_DAILY_BEAT", "1") == "1":
        BeatRegistry.register("news-archive-daily", "app.tasks.news_backfill_tasks.scheduled_news_daily", crontab(hour=6, minute=20), description="daily news archive", queue="default")

    # -- KNOWLEDGE_CRAWL_BEAT (unify + localize after yanbao/news) --
    if get_runtime("KNOWLEDGE_CRAWL_BEAT", "1") == "1":
        BeatRegistry.register(
            "knowledge-crawl-daily",
            "app.tasks.knowledge_crawl_tasks.scheduled_knowledge_crawl",
            crontab(hour=6, minute=40),
            description="crawl+localize knowledge base",
            queue="default",
        )

    # -- SCANNER_CELERY_BEAT --
    if get_runtime("SCANNER_CELERY_BEAT", "1") == "1":
        BeatRegistry.register("scanner-core-every-2min", "app.tasks.scanner_tasks.scanner_core_tick", crontab(minute="*/2"), description="scanner core tick", queue="default")
        BeatRegistry.register("scanner-rotation-every-15min", "app.tasks.scanner_tasks.scanner_rotation_tick", crontab(minute="*/15"), description="scanner rotation tick", queue="default")
        BeatRegistry.register("scanner-daily-sync", "app.tasks.market_tasks.refresh_basic_market_data", crontab(hour=16, minute=0), description="refresh basic market data", queue="default")

    # -- TDX_DAYK_CELERY_BEAT --
    # 历史入库主链：TDX → Timescale + CSV + qlib_bin（无 MySQL / QuestDB / ClickHouse）
    tdx_dayk_beat_on = get_runtime("TDX_DAYK_CELERY_BEAT", "0") == "1"
    if tdx_dayk_beat_on:
        tdx_hour = max(0, min(get_runtime_int("TDX_DAYK_BEAT_HOUR", 16), 23))
        tdx_minute = max(0, min(get_runtime_int("TDX_DAYK_BEAT_MINUTE", 5), 59))
        bin_minute = max(0, min(get_runtime_int("TDX_DAYK_QLIB_BIN_BEAT_MINUTE", 25), 59))
        use_daily_chain = get_runtime("TDX_USE_SCHEDULED_DAILY_CHAIN", "1") == "1"
        if use_daily_chain:
            BeatRegistry.register(
                "cn-history-daily-after-close",
                "app.tasks.data_backfill_tasks.scheduled_cn_history_daily",
                crontab(hour=tdx_hour, minute=tdx_minute),
                description="CN history daily: TDX→Timescale/CSV/qlib",
                queue="low",
            )
        else:
            BeatRegistry.register(
                "tdx-dayk-incremental-after-close",
                "app.tasks.data_backfill_tasks.sync_incremental_tdx",
                crontab(hour=tdx_hour, minute=tdx_minute),
                description="TDX→Timescale/CSV incremental",
                queue="low",
                dump_qlib_bin=False,
            )
            BeatRegistry.register(
                "cn-history-csv-to-qlib-after-tdx",
                "app.tasks.qlib_data_update.csv_to_qlib_incremental_sync",
                crontab(hour=tdx_hour, minute=bin_minute),
                description="CSV→qlib_bin after TDX",
                queue="low",
            )

    # -- QLIB_CELERY_BEAT --
    if get_runtime("QLIB_CELERY_BEAT", "0") == "1":
        if not tdx_dayk_beat_on:
            BeatRegistry.register(
                "qlib-csv-incremental-sync",
                "app.tasks.qlib_data_update.csv_to_qlib_incremental_sync",
                crontab(hour=16, minute=10),
                description="qlib csv→bin incremental sync",
                queue="low",
            )
        BeatRegistry.register("qlib-tdx-incremental-nightly", "app.tasks.qlib_data_update.qlib_incremental_pipeline", crontab(hour=2, minute=40), description="qlib tdx nightly", queue="low")

    # -- DATA_BACKFILL_BEAT --
    if get_runtime("DATA_BACKFILL_BEAT", "0") == "1":
        BeatRegistry.register("backfill-financial-stash-if-empty", "app.tasks.data_backfill_tasks.backfill_financial_stash_if_empty", crontab(hour=2, minute=12), description="backfill financial stash", queue="low")
        BeatRegistry.register("backfill-longhu-if-empty", "app.tasks.data_backfill_tasks.backfill_longhu_if_empty", crontab(hour=2, minute=18), description="backfill longhu", queue="low")
        BeatRegistry.register("backfill-qlib-kline-if-empty", "app.tasks.data_backfill_tasks.backfill_qlib_kline_if_empty", crontab(hour=2, minute=28), description="backfill qlib kline", queue="low")

    # -- FINANCIAL_DAILY_BEAT --
    if get_runtime("FINANCIAL_DAILY_BEAT", "0") == "1":
        BeatRegistry.register("financial-stash-daily-refresh", "app.tasks.data_backfill_tasks.scheduled_financial_stash_refresh", crontab(hour=7, minute=30), description="financial stash daily refresh", queue="low")

    # -- NEWS_ARCHIVE_BACKFILL_BEAT --
    if get_runtime("NEWS_ARCHIVE_BACKFILL_BEAT", "0") == "1":
        BeatRegistry.register("news-archive-backfill-weekly", "app.tasks.news_backfill_tasks.backfill_news_archive_for_codes", crontab(day_of_week=0, hour=3, minute=10), description="news archive weekly backfill", queue="default")

    # -- RETAIL_PSYCHOLOGY_BEAT --
    if get_runtime("RETAIL_PSYCHOLOGY_BEAT", "1") == "1":
        BeatRegistry.register("retail-psychology-midday", "app.tasks.retail_psychology_tasks.psychology_guardian_tick", crontab(hour=11, minute=35), description="psychology midday scan", queue="default")
        BeatRegistry.register("retail-psychology-after-close", "app.tasks.retail_psychology_tasks.psychology_guardian_tick", crontab(hour=15, minute=12), description="psychology after-close scan", queue="default")

    # -- RETAIL_META_LEARNING_BEAT --
    if get_runtime("RETAIL_META_LEARNING_BEAT", "1") == "1":
        BeatRegistry.register("retail-meta-learning-weekly", "app.tasks.retail_meta_learning_tasks.meta_learning_evolve_tick", crontab(day_of_week=6, hour=18, minute=50), description="meta learning weekly evolve", queue="default")

    # -- QUESTDB/ClickHouse 入库已下线：Beat 不再注册（保留任务入口返回 skipped）

    # -- TIMESCALE_TDX_SYNC_BEAT --
    # 日更主链已含 Timescale 时不再重复注册独立 Beat
    if get_runtime("TIMESCALE_TDX_SYNC_BEAT", "0") == "1" and not tdx_dayk_beat_on:
        ts_hour = max(0, min(get_runtime_int("TIMESCALE_SYNC_BEAT_HOUR", 17), 23))
        ts_minute = max(0, min(get_runtime_int("TIMESCALE_SYNC_BEAT_MINUTE", 10), 59))
        BeatRegistry.register("tdx-timescale-after-close", "app.tasks.tdx_timescale_sync_tasks.tdx_timescale_sync_tick", crontab(hour=ts_hour, minute=ts_minute), description="TDX to TimescaleDB sync", queue="low")

    # -- OHLCV_RECONCILIATION_BEAT --
    if get_runtime("OHLCV_RECONCILIATION_BEAT", "0") == "1":
        BeatRegistry.register("ohlcv-reconciliation-weekly", "app.tasks.ohlcv_reconciliation_tasks.ohlcv_reconciliation_tick", crontab(day_of_week=6, hour=19, minute=0), description="OHLCV weekly reconciliation", queue="low")

    # -- FACTOR_IC_CELERY_BEAT --
    if get_runtime("FACTOR_IC_CELERY_BEAT", "0") == "1":
        BeatRegistry.register("factor-ic-monitor-after-close", "app.tasks.factor_ic_alerts.factor_ic_monitor_tick", crontab(hour=18, minute=35), description="factor IC monitor", queue="default")

    # -- FACTOR_LIFECYCLE_CELERY_BEAT --
    if get_runtime("FACTOR_LIFECYCLE_CELERY_BEAT", "0") == "1":
        BeatRegistry.register("factor-lifecycle-daily-check", "factor.lifecycle_daily_check", crontab(hour=18, minute=40), description="factor lifecycle daily check", queue="default")
        BeatRegistry.register("factor-ic-calculation-daily", "factor.ic_calculation", crontab(hour=18, minute=45), description="factor IC daily calc", queue="default")
        BeatRegistry.register("factor-cleanup-archived-weekly", "factor.cleanup_archived", crontab(day_of_week=6, hour=3, minute=0), description="factor cleanup archived", queue="low")

    # -- MOMENTS_AFTER_CLOSE_BEAT --
    if get_runtime("MOMENTS_AFTER_CLOSE_BEAT", "0") == "1":
        BeatRegistry.register("moments-after-close", "app.tasks.moments_tasks.moments_after_close", crontab(hour=15, minute=20), description="moments after close", queue="default")

    # -- INVESTMENT_MANAGERS_CELERY_BEAT --
    if get_runtime("INVESTMENT_MANAGERS_CELERY_BEAT", "0") == "1":
        BeatRegistry.register(
            "post-close-signal-then-managers",
            "app.tasks.investment_manager_tasks.post_close_signal_then_managers",
            crontab(hour=15, minute=50),
            description="post-close signal + managers",
            queue="high",
            pool_date=None,
            max_stocks=800,
            lookback_days=160,
            run_deploy_schedule=True,
            schedule_start_date="2020-01-01",
            schedule_batch_size=10,
            asof_date=None,
            nav_date=None,
            universe_limit=800,
        )

    # -- TDX_GPCW_DAILY_BEAT --
    if get_runtime("TDX_GPCW_DAILY_BEAT", "0") == "1":
        BeatRegistry.register("tdx-gpcw-incremental-daily", "app.tasks.tdx_gpcw_tasks.import_tdx_gpcw_latest", crontab(hour=7, minute=45), description="TDX GPCW daily import", queue="default")

    # -- ALERT_DISPATCH_CELERY_BEAT --
    if get_runtime("ALERT_DISPATCH_CELERY_BEAT", "0") == "1":
        beat_minutes = max(5, min(get_runtime_int("ALERT_DISPATCH_BEAT_MINUTES", 30), 59))
        BeatRegistry.register(
            "alert-dispatch-periodic",
            "app.tasks.alert_dispatch_tasks.dispatch_alert_notifications",
            crontab(minute=f"*/{beat_minutes}"),
            description="alert dispatch periodic",
            queue="default",
            min_level=get_runtime("ALERT_DISPATCH_MIN_LEVEL", "warning"),
            limit=get_runtime_int("ALERT_DISPATCH_LIMIT", 20),
            respect_dedup=True,
        )

    # -- QUOTES_DUMP_MONITOR_CELERY_BEAT --
    if get_runtime("QUOTES_DUMP_MONITOR_CELERY_BEAT", "0") == "1":
        dump_minutes = max(5, min(get_runtime_int("QUOTES_DUMP_MONITOR_BEAT_MINUTES", 30), 59))
        BeatRegistry.register(
            "quotes-dump-monitor-periodic",
            "app.tasks.quotes_dump_monitor_tasks.quotes_dump_monitor_tick",
            crontab(minute=f"*/{dump_minutes}"),
            description="quotes full-dump pressure monitor",
            queue="default",
        )

    # -- HEADLINE_SIGNAL_CELERY_BEAT --
    if get_runtime("HEADLINE_SIGNAL_CELERY_BEAT", "0") == "1":
        beat_minutes = max(10, min(get_runtime_int("HEADLINE_SIGNAL_BEAT_MINUTES", 30), 59))
        BeatRegistry.register(
            "headline-signal-enrich-cn",
            "app.tasks.headline_signal_tasks.enrich_market_headlines",
            crontab(minute=f"*/{beat_minutes}"),
            description="headline signal enrich",
            queue="default",
            market="CN",
            limit=get_runtime_int("HEADLINE_SIGNAL_BATCH_LIMIT", 40),
        )

    # -- FEDERATED_CLUSTER_BEAT --
    if get_runtime("FEDERATED_CLUSTER_BEAT", "0") == "1":
        beat_minutes = max(5, min(get_runtime_int("FEDERATED_CLUSTER_BEAT_MINUTES", 5), 59))
        BeatRegistry.register("federated-cluster-health-scan", "federated.cluster_health_scan", crontab(minute=f"*/{beat_minutes}"), description="federated cluster health scan", queue="default")

    # -- STRATEGY_TOURNAMENT_CELERY_BEAT (non-trading / evening) --
    if get_runtime("STRATEGY_TOURNAMENT_CELERY_BEAT", "0") == "1":
        t_hour = max(0, min(get_runtime_int("STRATEGY_TOURNAMENT_BEAT_HOUR", 20), 23))
        t_minute = max(0, min(get_runtime_int("STRATEGY_TOURNAMENT_BEAT_MINUTE", 30), 59))
        BeatRegistry.register(
            "strategy-tournament-evening",
            "app.tasks.strategy_tournament_tasks.strategy_tournament_tick",
            crontab(hour=t_hour, minute=t_minute),
            description="offline strategy tournament hard gates → paper pool",
            queue="low",
            limit=get_runtime_int("STRATEGY_TOURNAMENT_LIMIT", 200),
        )

    # -- FEATURE_PIPELINE_CELERY_BEAT (optional daily heuristic train) --
    if get_runtime("FEATURE_PIPELINE_CELERY_BEAT", "0") == "1":
        fp_hour = max(0, min(get_runtime_int("FEATURE_PIPELINE_BEAT_HOUR", 21), 23))
        fp_minute = max(0, min(get_runtime_int("FEATURE_PIPELINE_BEAT_MINUTE", 0), 59))
        BeatRegistry.register(
            "feature-pipeline-daily",
            "app.tasks.feature_pipeline_tasks.feature_pipeline_tick",
            crontab(hour=fp_hour, minute=fp_minute),
            description="Feature Pipeline train (auto→LightGBM|heuristic) → instance/feature_models",
            queue="low",
            spec_name=get_runtime("FEATURE_PIPELINE_SPEC_NAME", "cn_day_v0") or "cn_day_v0",
            model_backend=get_runtime("FEATURE_PIPELINE_MODEL", "auto") or "auto",
            symbol=get_runtime("FEATURE_PIPELINE_SYMBOL", "600519") or "600519",
        )

    # -- RL_RESEARCH_CELERY_BEAT (offline only; never live) --
    if get_runtime("RL_RESEARCH_CELERY_BEAT", "0") == "1":
        rl_hour = max(0, min(get_runtime_int("RL_RESEARCH_BEAT_HOUR", 22), 23))
        rl_minute = max(0, min(get_runtime_int("RL_RESEARCH_BEAT_MINUTE", 0), 59))
        BeatRegistry.register(
            "rl-research-daily",
            "app.tasks.rl_research_tasks.rl_research_tick",
            crontab(hour=rl_hour, minute=rl_minute),
            description="offline tabular Q research → instance/rl_research (never live)",
            queue="low",
            spec_name=get_runtime("RL_RESEARCH_SPEC", "cn_day_v0") or "cn_day_v0",
            symbol=get_runtime("FEATURE_PIPELINE_SYMBOL", "600519") or "600519",
        )

    return BeatRegistry.build_schedule()



_SKIP_TASK_MODULES = frozenset({"task_wiring", "worker_db_cleanup", "registry"})


def discover_task_modules() -> None:
    """Import ``app.tasks.*`` so ``@celery.task`` decorators register on the app instance."""
    import importlib
    import pkgutil

    import app.tasks as tasks_pkg

    for _finder, name, _ispkg in pkgutil.iter_modules(tasks_pkg.__path__):
        if name.startswith("_") or name in _SKIP_TASK_MODULES:
            continue
        module_name = f"{tasks_pkg.__name__}.{name}"
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            logger.warning("celery task module skipped (%s): %s", module_name, exc)

if Celery is None:
    celery = None  # type: ignore[assignment]
    celery_app = None  # type: ignore[assignment]
else:
    try:
        _broker = _broker_url()
        _backend = _result_backend()
    except RuntimeError as exc:
        logger.warning("Celery disabled: %s", exc)
        # Still create Celery app with memory broker so task decorators work
        _broker = "memory://"
        _backend = _broker

    celery = Celery("quant_atlas", broker=_broker, backend=_backend)
    celery_app = celery
    try:
        import pymysql.err as _pymysql_err
    except Exception:
        _pymysql_err = None

    _retry_for: tuple[type[BaseException], ...] = (
        TimeoutError,
        ConnectionError,
    )
    if _pymysql_err is not None:
        _retry_for = _retry_for + (_pymysql_err.OperationalError, _pymysql_err.InterfaceError)

    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        result_expires=3600,
        timezone="Asia/Shanghai",
        enable_utc=False,
        beat_schedule=_build_beat_schedule(),
        # Queue Priority Routing
        task_queues={
            "high": {"exchange": "high"},
            "default": {"exchange": "default"},
            "low": {"exchange": "low"},
        },
        task_routes={
            "app.tasks.trading_tasks.*": {"queue": "high"},
            "app.tasks.market_tasks.*": {"queue": "default"},
            "app.tasks.data_backfill_tasks.*": {"queue": "low"},
            "app.tasks.qlib_data_update.*": {"queue": "low"},
        },
        # Reliability baseline
        task_acks_late=get_runtime_bool("CELERY_TASK_ACKS_LATE", True),
        task_reject_on_worker_lost=get_runtime_bool("CELERY_TASK_REJECT_ON_WORKER_LOST", True),
        task_acks_on_failure_or_timeout=get_runtime_bool("CELERY_TASK_ACKS_ON_FAILURE_OR_TIMEOUT", False),
        worker_prefetch_multiplier=get_runtime_int("CELERY_WORKER_PREFETCH_MULTIPLIER", 1),
        worker_max_tasks_per_child=get_runtime_int("CELERY_WORKER_MAX_TASKS_PER_CHILD", 500),
        task_track_started=get_runtime_bool("CELERY_TASK_TRACK_STARTED", True),
        broker_connection_retry_on_startup=get_runtime_bool("CELERY_BROKER_RETRY_ON_STARTUP", True),
        task_default_queue=get_runtime("CELERY_DEFAULT_QUEUE", "default"),
        task_soft_time_limit=get_runtime_int("CELERY_TASK_SOFT_TIME_LIMIT", 1800),
        task_time_limit=get_runtime_int("CELERY_TASK_TIME_LIMIT", 2100),
        task_annotations={
            "*": {
                "autoretry_for": _retry_for,
                "retry_backoff": get_runtime_bool("CELERY_TASK_RETRY_BACKOFF", True),
                "retry_backoff_max": get_runtime_int("CELERY_TASK_RETRY_BACKOFF_MAX", 300),
                "retry_jitter": get_runtime_bool("CELERY_TASK_RETRY_JITTER", True),
                "retry_kwargs": {"max_retries": get_runtime_int("CELERY_TASK_MAX_RETRIES", 3)},
            }
        },
    )

    def _push_safe(**kwargs: Any) -> None:
        try:
            from app.tasks.task_wiring import get_task_message_store

            get_task_message_store().push(**kwargs)
        except Exception as exc:
            logger.debug("task message push skipped: %s", exc)

    def _cleanup_worker_db_safely() -> None:
        try:
            from app.tasks.worker_db_cleanup import cleanup_worker_db_resources

            cleanup_worker_db_resources()
        except Exception as exc:
            logger.debug("worker db cleanup skipped: %s", exc)

    @worker_process_init.connect
    def _on_worker_process_init(**_: Any) -> None:
        try:
            discover_task_modules()
        except Exception as exc:
            logger.warning("celery discover_task_modules skipped: %s", exc)
        try:
            from app.tasks.task_wiring import ensure_task_bindings

            ensure_task_bindings()
        except Exception as exc:
            logger.warning("worker infrastructure bind skipped: %s", exc)
        try:
            from app.bootstrap_components.runtime_config_validator import (
                validate_worker_runtime_config,
            )

            validate_worker_runtime_config()
        except Exception as exc:
            logger.error("worker runtime config validation failed: %s", exc)
            raise

    @task_prerun.connect
    def _on_task_prerun(
        sender: Any = None,
        task_id: str | None = None,
        task: Any = None,
        args: Any = None,
        kwargs: Any = None,
        **extra: Any,
    ) -> None:
        if not task_id or not task:
            return
        name = getattr(task, "name", None) or (sender.__name__ if sender else "unknown")
        _push_safe(
            event="task_started",
            task_id=task_id,
            task_name=name,
            detail="worker started",
            meta={"args_preview": str(args)[:200] if args is not None else ""},
        )
        try:
            from app.tasks.task_wiring import report_task_progress

            report_task_progress(task_id, step_index=1, message="Worker 已开始执行")
        except Exception as exc:
            logger.debug("task progress prerun skipped: %s", exc)
        try:
            from app.domain.workflow_hub.models import WorkflowInstance, WorkflowStatus, WorkflowType
            from app.infrastructure.workflow_hub.factory import get_workflow_repository

            wf = WorkflowInstance(
                workflow_id=task_id,
                type=WorkflowType.SIGNAL_SCAN,
                status=WorkflowStatus.RUNNING,
                params={"task_name": name},
            )
            get_workflow_repository().save(wf)
        except Exception as exc:
            logger.debug("workflow hub prerun skipped: %s", exc)

    @task_postrun.connect
    def _on_task_postrun(
        sender: Any = None,
        task_id: str | None = None,
        task: Any = None,
        retval: Any = None,
        **extra: Any,
    ) -> None:
        _cleanup_worker_db_safely()
        if not task_id or not task:
            return
        if isinstance(retval, dict) and retval.get("_suppress_default_task_message"):
            return
        name = getattr(task, "name", None) or "unknown"
        detail = "completed"
        meta: dict[str, Any] = {}
        if isinstance(retval, dict):
            meta["result_keys"] = list(retval.keys())[:20]
            if retval.get("skipped"):
                detail = f"skipped: {retval.get('reason', retval.get('message', 'skipped'))}"[:500]
            elif "rows" in retval:
                detail = f"completed rows={retval.get('rows')}"
            elif retval.get("ok") is False:
                detail = f"ok=false: {retval.get('error', '')}"[:500]
        _push_safe(event="task_succeeded", task_id=task_id, task_name=name, detail=detail, meta=meta)
        try:
            from app.tasks.task_wiring import finalize_task_progress

            successful = not (isinstance(retval, dict) and retval.get("ok") is False)
            finalize_task_progress(task_id, successful=successful, message=detail[:500])
        except Exception as exc:
            logger.debug("task progress postrun skipped: %s", exc)
        try:
            from app.domain.workflow_hub.models import WorkflowStatus
            from app.infrastructure.workflow_hub.factory import get_workflow_repository

            repo = get_workflow_repository()
            wf = repo.get(task_id)
            if wf is not None:
                repo.update_status(
                    task_id,
                    WorkflowStatus.COMPLETED,
                    progress=100,
                )
        except Exception as exc:
            logger.debug("workflow hub postrun skipped: %s", exc)

    @task_failure.connect
    def _on_task_failure(
        sender: Any = None,
        task_id: str | None = None,
        exception: BaseException | None = None,
        traceback: Any = None,
        **extra: Any,
    ) -> None:
        _cleanup_worker_db_safely()
        if not task_id:
            return
        name = getattr(sender, "name", None) or "unknown"
        _push_safe(
            event="task_failed",
            task_id=task_id,
            task_name=name,
            detail=str(exception)[:1500] if exception else "failed",
            meta={},
        )
        try:
            from app.tasks.task_wiring import finalize_task_progress

            finalize_task_progress(
                task_id,
                successful=False,
                message=str(exception)[:500] if exception else "任务失败",
            )
        except Exception as exc:
            logger.debug("task progress failure skipped: %s", exc)
        try:
            from app.domain.workflow_hub.models import WorkflowStatus
            from app.infrastructure.workflow_hub.factory import get_workflow_repository

            repo = get_workflow_repository()
            wf = repo.get(task_id)
            if wf is not None:
                repo.update_status(
                    task_id,
                    WorkflowStatus.FAILED,
                    error=str(exception)[:500] if exception else "failed",
                )
        except Exception as exc:
            logger.debug("workflow hub failure skipped: %s", exc)

# discover_task_modules() is module-level; called from worker_process_init and warm_runtime_extensions.
