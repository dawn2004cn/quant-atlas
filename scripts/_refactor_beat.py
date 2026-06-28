# -*- coding: utf-8 -*-
import re

with open(r"E:\project\workspace\myrepo\quant-atlas\app\celery_app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Step 1: Add BeatRegistry import after get_runtime_int
old_import = "from .core.runtime_config import get_runtime, get_runtime_bool, get_runtime_int"
new_import = "from .core.runtime_config import get_runtime, get_runtime_bool, get_runtime_int\nfrom .core.celery_ext import BeatRegistry"
content = content.replace(old_import, new_import, 1)

# Step 2: Check if already refactored
if "BeatRegistry.clear()" in content:
    print("Already refactored, skip.")
    exit(0)

start_marker = "def _build_beat_schedule() -> dict[str, Any]:"
end_marker = "    return beat"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)
if start_idx == -1 or end_idx == -1:
    print(f"ERROR: Could not find function markers. start={start_idx}, end={end_idx}")
    exit(1)

end_idx = end_idx + len(end_marker)

new_func = """def _build_beat_schedule() -> dict[str, Any]:
    \"\"\"Build beat schedule from BeatRegistry. All tasks register declaratively.\"\"\"
    assert crontab is not None

    BeatRegistry.clear()

    # -- BASIC_DATA_LONGHU_BEAT --
    if get_runtime("BASIC_DATA_LONGHU_BEAT", "1") == "1":
        BeatRegistry.register("basic-data-longhu-daily", "app.tasks.market_tasks.scheduled_longhu", crontab(hour=17, minute=5), description="longhu daily", queue="default")
        BeatRegistry.register("basic-data-indices-daily", "app.tasks.market_tasks.scheduled_indices_sync", crontab(hour=15, minute=40), description="indices sync", queue="default")

    # -- BASIC_DATA_YANBAO_BEAT --
    if get_runtime("BASIC_DATA_YANBAO_BEAT", "1") == "1":
        BeatRegistry.register("basic-data-yanbao-daily", "app.tasks.market_tasks.scheduled_yanbao", crontab(hour=6, minute=5), description="yanbao daily", queue="default")

    # -- NEWS_DAILY_BEAT --
    if get_runtime("NEWS_DAILY_BEAT", "1") == "1":
        BeatRegistry.register("news-archive-daily", "app.tasks.news_backfill_tasks.scheduled_news_daily", crontab(hour=6, minute=20), description="news archive daily", queue="default")

    # -- SCANNER_CELERY_BEAT --
    if get_runtime("SCANNER_CELERY_BEAT", "1") == "1":
        BeatRegistry.register("scanner-core-every-2min", "app.tasks.scanner_tasks.scanner_core_tick", crontab(minute="*/2"), description="scanner core tick", queue="default")
        BeatRegistry.register("scanner-rotation-every-15min", "app.tasks.scanner_tasks.scanner_rotation_tick", crontab(minute="*/15"), description="scanner rotation tick", queue="default")
        BeatRegistry.register("scanner-daily-sync", "app.tasks.market_tasks.refresh_basic_market_data", crontab(hour=16, minute=0), description="refresh basic market data", queue="default")

    # -- TDX_DAYK_CELERY_BEAT --
    tdx_dayk_beat_on = get_runtime("TDX_DAYK_CELERY_BEAT", "0") == "1"
    if tdx_dayk_beat_on:
        tdx_hour = max(0, min(get_runtime_int("TDX_DAYK_BEAT_HOUR", 16), 23))
        tdx_minute = max(0, min(get_runtime_int("TDX_DAYK_BEAT_MINUTE", 5), 59))
        bin_minute = max(0, min(get_runtime_int("TDX_DAYK_QLIB_BIN_BEAT_MINUTE", 25), 59))
        use_daily_chain = get_runtime("TDX_USE_SCHEDULED_DAILY_CHAIN", "1") == "1"
        if use_daily_chain:
            BeatRegistry.register("cn-history-daily-after-close", "app.tasks.data_backfill_tasks.scheduled_cn_history_daily", crontab(hour=tdx_hour, minute=tdx_minute), description="CN history after close", queue="low")
        else:
            BeatRegistry.register("tdx-dayk-incremental-after-close", "app.tasks.data_backfill_tasks.sync_incremental_tdx", crontab(hour=tdx_hour, minute=tdx_minute), description="TDX dayk incremental", queue="low", dump_qlib_bin=False)
            BeatRegistry.register("cn-history-mysql-to-qlib-after-tdx", "app.tasks.qlib_data_update.mysql_to_qlib_incremental_sync", crontab(hour=tdx_hour, minute=bin_minute), description="MySQL to qlib", queue="low")

    # -- QLIB_CELERY_BEAT --
    if get_runtime("QLIB_CELERY_BEAT", "0") == "1":
        if not tdx_dayk_beat_on:
            BeatRegistry.register("qlib-mysql-incremental-sync", "app.tasks.qlib_data_update.mysql_to_qlib_incremental_sync", crontab(hour=16, minute=10), description="qlib mysql sync", queue="low")
        BeatRegistry.register("qlib-tdx-incremental-nightly", "app.tasks.qlib_data_update.qlib_incremental_pipeline", crontab(hour=2, minute=40), description="qlib tdx nightly", queue="low")

    # -- DATA_BACKFILL_BEAT --
    if get_runtime("DATA_BACKFILL_BEAT", "0") == "1":
        BeatRegistry.register("backfill-financial-stash-if-empty", "app.tasks.data_backfill_tasks.backfill_financial_stash_if_empty", crontab(hour=2, minute=12), description="backfill financial stash", queue="low")
        BeatRegistry.register("backfill-longhu-if-empty", "app.tasks.data_backfill_tasks.backfill_longhu_if_empty", crontab(hour=2, minute=18), description="backfill longhu", queue="low")
        BeatRegistry.register("backfill-qlib-kline-if-empty", "app.tasks.data_backfill_tasks.backfill_qlib_kline_if_empty", crontab(hour=2, minute=28), description="backfill qlib kline", queue="low")

    # -- FINANCIAL_DAILY_BEAT --
    if get_runtime("FINANCIAL_DAILY_BEAT", "0") == "1":
        BeatRegistry.register("financial-stash-daily-refresh", "app.tasks.data_backfill_tasks.scheduled_financial_stash_refresh", crontab(hour=7, minute=30), description="financial stash daily", queue="low")

    # -- NEWS_ARCHIVE_BACKFILL_BEAT --
    if get_runtime("NEWS_ARCHIVE_BACKFILL_BEAT", "0") == "1":
        BeatRegistry.register("news-archive-backfill-weekly", "app.tasks.news_backfill_tasks.backfill_news_archive_for_codes", crontab(day_of_week=0, hour=3, minute=10), description="news archive weekly", queue="default")

    # -- RETAIL_PSYCHOLOGY_BEAT --
    if get_runtime("RETAIL_PSYCHOLOGY_BEAT", "1") == "1":
        BeatRegistry.register("retail-psychology-midday", "app.tasks.retail_psychology_tasks.psychology_guardian_tick", crontab(hour=11, minute=35), description="psychology midday", queue="default")
        BeatRegistry.register("retail-psychology-after-close", "app.tasks.retail_psychology_tasks.psychology_guardian_tick", crontab(hour=15, minute=12), description="psychology after close", queue="default")

    # -- RETAIL_META_LEARNING_BEAT --
    if get_runtime("RETAIL_META_LEARNING_BEAT", "1") == "1":
        BeatRegistry.register("retail-meta-learning-weekly", "app.tasks.retail_meta_learning_tasks.meta_learning_evolve_tick", crontab(day_of_week=6, hour=18, minute=50), description="meta learning weekly", queue="default")

    # -- QUESTDB_SYNC_BEAT --
    if get_runtime("QUESTDB_SYNC_BEAT", "1") == "1":
        BeatRegistry.register("questdb-ohlcv-after-close", "app.tasks.questdb_sync_tasks.questdb_ohlcv_sync_tick", crontab(hour=16, minute=35), description="questdb ohlcv sync", queue="default")

    # -- TIMESCALE_TDX_SYNC_BEAT --
    if get_runtime("TIMESCALE_TDX_SYNC_BEAT", "0") == "1":
        ts_hour = max(0, min(get_runtime_int("TIMESCALE_SYNC_BEAT_HOUR", 17), 23))
        ts_minute = max(0, min(get_runtime_int("TIMESCALE_SYNC_BEAT_MINUTE", 10), 59))
        BeatRegistry.register("tdx-timescale-after-close", "app.tasks.tdx_timescale_sync_tasks.tdx_timescale_sync_tick", crontab(hour=ts_hour, minute=ts_minute), description="TDX to TimescaleDB", queue="low")

    # -- OHLCV_RECONCILIATION_BEAT --
    if get_runtime("OHLCV_RECONCILIATION_BEAT", "0") == "1":
        BeatRegistry.register("ohlcv-reconciliation-weekly", "app.tasks.ohlcv_reconciliation_tasks.ohlcv_reconciliation_tick", crontab(day_of_week=6, hour=19, minute=0), description="OHLCV reconciliation", queue="low")

    # -- FACTOR_IC_CELERY_BEAT --
    if get_runtime("FACTOR_IC_CELERY_BEAT", "0") == "1":
        BeatRegistry.register("factor-ic-monitor-after-close", "app.tasks.factor_ic_alerts.factor_ic_monitor_tick", crontab(hour=18, minute=35), description="factor IC monitor", queue="default")

    # -- FACTOR_LIFECYCLE_CELERY_BEAT --
    if get_runtime("FACTOR_LIFECYCLE_CELERY_BEAT", "0") == "1":
        BeatRegistry.register("factor-lifecycle-daily-check", "factor.lifecycle_daily_check", crontab(hour=18, minute=40), description="factor lifecycle check", queue="default")
        BeatRegistry.register("factor-ic-calculation-daily", "factor.ic_calculation", crontab(hour=18, minute=45), description="factor IC calc", queue="default")
        BeatRegistry.register("factor-cleanup-archived-weekly", "factor.cleanup_archived", crontab(day_of_week=6, hour=3, minute=0), description="factor cleanup archived", queue="low")

    # -- MOMENTS_AFTER_CLOSE_BEAT --
    if get_runtime("MOMENTS_AFTER_CLOSE_BEAT", "0") == "1":
        BeatRegistry.register("moments-after-close", "app.tasks.moments_tasks.moments_after_close", crontab(hour=15, minute=20), description="moments after close", queue="default")

    # -- INVESTMENT_MANAGERS_CELERY_BEAT --
    if get_runtime("INVESTMENT_MANAGERS_CELERY_BEAT", "0") == "1":
        BeatRegistry.register("post-close-signal-then-managers", "app.tasks.investment_manager_tasks.post_close_signal_then_managers", crontab(hour=15, minute=50), description="post-close signal + managers", queue="high", pool_date=None, max_stocks=800, lookback_days=160, run_deploy_schedule=True, schedule_start_date="2020-01-01", schedule_batch_size=10, asof_date=None, nav_date=None, universe_limit=800)

    # -- TDX_GPCW_DAILY_BEAT --
    if get_runtime("TDX_GPCW_DAILY_BEAT", "0") == "1":
        BeatRegistry.register("tdx-gpcw-incremental-daily", "app.tasks.tdx_gpcw_tasks.import_tdx_gpcw_latest", crontab(hour=7, minute=45), description="TDX GPCW daily", queue="default")

    # -- ALERT_DISPATCH_CELERY_BEAT --
    if get_runtime("ALERT_DISPATCH_CELERY_BEAT", "0") == "1":
        beat_minutes = max(5, min(get_runtime_int("ALERT_DISPATCH_BEAT_MINUTES", 30), 59))
        BeatRegistry.register("alert-dispatch-periodic", "app.tasks.alert_dispatch_tasks.dispatch_alert_notifications", crontab(minute=f"*/{beat_minutes}"), description="alert dispatch", queue="default", min_level=get_runtime("ALERT_DISPATCH_MIN_LEVEL", "warning"), limit=get_runtime_int("ALERT_DISPATCH_LIMIT", 20), respect_dedup=True)

    # -- HEADLINE_SIGNAL_CELERY_BEAT --
    if get_runtime("HEADLINE_SIGNAL_CELERY_BEAT", "0") == "1":
        beat_minutes = max(10, min(get_runtime_int("HEADLINE_SIGNAL_BEAT_MINUTES", 30), 59))
        BeatRegistry.register("headline-signal-enrich-cn", "app.tasks.headline_signal_tasks.enrich_market_headlines", crontab(minute=f"*/{beat_minutes}"), description="headline signal enrich", queue="default", market="CN", limit=get_runtime_int("HEADLINE_SIGNAL_BATCH_LIMIT", 40))

    # -- FEDERATED_CLUSTER_BEAT --
    if get_runtime("FEDERATED_CLUSTER_BEAT", "0") == "1":
        beat_minutes = max(5, min(get_runtime_int("FEDERATED_CLUSTER_BEAT_MINUTES", 5), 59))
        BeatRegistry.register("federated-cluster-health-scan", "federated.cluster_health_scan", crontab(minute=f"*/{beat_minutes}"), description="federated health scan", queue="default")

    return BeatRegistry.build_schedule()
"""

content = content[:start_idx] + new_func + content[end_idx:]

with open(r"E:\project\workspace\myrepo\quant-atlas\app\celery_app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done!")
