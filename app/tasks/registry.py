from __future__ import annotations

"""Task registry - Centralized task definitions and metadata."""

from collections.abc import Callable
from typing import Any

TASK_REGISTRY: dict[str, dict[str, Any]] = {}


def register_task(
    task_name: str,
    task_func: Callable,
    description: str,
    category: str = "general",
    params: dict[str, Any] | None = None,
    default_params: dict[str, Any] | None = None,
    estimated_steps: list[str] | None = None,
) -> None:
    """Register a task with its metadata."""
    TASK_REGISTRY[task_name] = {
        "func": task_func,
        "description": description,
        "category": category,
        "params": params or {},
        "default_params": default_params or {},
        "estimated_steps": estimated_steps or ["排队", "执行", "持久化", "完成"],
    }


def get_task_registry() -> dict[str, dict[str, Any]]:
    """Get all registered tasks."""
    return TASK_REGISTRY


def get_task_info(task_name: str) -> dict[str, Any] | None:
    """Get task info by name."""
    return TASK_REGISTRY.get(task_name)


def get_tasks_by_category() -> dict[str, list[dict[str, Any]]]:
    """Get tasks grouped by category."""
    result: dict[str, list[dict[str, Any]]] = {}
    for name, info in TASK_REGISTRY.items():
        cat = info.get("category", "general")
        if cat not in result:
            result[cat] = []
        result[cat].append(
            {
                "name": name,
                "description": info.get("description", ""),
                "category": info.get("category", cat),
                "params": info.get("params") or {},
                "default_params": info.get("default_params") or {},
                "estimated_steps": info.get("estimated_steps") or [],
            }
        )
    return result


def _register_all_tasks() -> None:
    """Auto-register all tasks."""
    from app.tasks import (
        data_backfill_tasks,
        investment_manager_tasks,
        market_history_tasks,
        market_tasks,
        moments_tasks,
        news_backfill_tasks,
        knowledge_crawl_tasks,
        qlib_data_update,
        questdb_sync_tasks,
        scanner_tasks,
        signal_flag_tasks,
        tdx_dayk_tasks,
    )

    register_task(
        "app.tasks.data_backfill_tasks.backfill_all_history_tdx",
        data_backfill_tasks.backfill_all_history_tdx,
        "全量TDX日K同步：TDX日K目录 → MySQL + CSV",
        category="数据同步",
        default_params={"limit": None},
    )

    register_task(
        "app.tasks.data_backfill_tasks.sync_today_history_tdx",
        data_backfill_tasks.sync_today_history_tdx,
        "当日TDX日K同步：当日新增bar同步到MySQL/CSV",
        category="数据同步",
        default_params={"trade_date": None, "limit": None},
    )

    register_task(
        "app.tasks.data_backfill_tasks.sync_incremental_tdx",
        data_backfill_tasks.sync_incremental_tdx,
        "【推荐】增量 TDX 日 K：MySQL 最新日 → TDX → MySQL/CSV（可选 qlib_bin）",
        category="数据同步",
        default_params={"limit": None, "dump_qlib_bin": False},
    )

    register_task(
        "app.tasks.data_backfill_tasks.scheduled_cn_history_daily",
        data_backfill_tasks.scheduled_cn_history_daily,
        "【推荐】收盘日更：TDX 增量 + MySQL → qlib_bin",
        category="数据同步",
        default_params={"limit": None, "dump_max_workers": 8},
        estimated_steps=["TDX 增量写 MySQL/CSV", "MySQL 导出 qlib_bin", "完成"],
    )

    register_task(
        "app.tasks.data_backfill_tasks.backfill_longhu_if_empty",
        data_backfill_tasks.backfill_longhu_if_empty,
        "龙虎榜数据回填：仅空时执行",
        category="数据同步",
        default_params={"max_rows": 1000},
        estimated_steps=["校验空表", "拉取龙虎榜", "写入本地库", "完成"],
    )

    register_task(
        "app.tasks.data_backfill_tasks.backfill_yanbao_full",
        data_backfill_tasks.backfill_yanbao_full,
        "研报全量回填：从东方财富抓取研报",
        category="数据同步",
        default_params={"max_rows_per_category": 200},
    )

    register_task(
        "app.tasks.data_backfill_tasks.backfill_financial_stash_if_empty",
        data_backfill_tasks.backfill_financial_stash_if_empty,
        "财务快照回填：仅空时执行",
        category="数据同步",
        default_params={},
    )

    register_task(
        "app.tasks.qlib_data_update.qlib_full_backfill_if_empty",
        qlib_data_update.qlib_full_backfill_if_empty,
        "Qlib全量导出：CSV → qlib_bin，仅空时执行",
        category="数据同步",
        default_params={"period": "5y", "max_workers": 8},
    )

    register_task(
        "app.tasks.qlib_data_update.qlib_incremental_pipeline",
        qlib_data_update.qlib_incremental_pipeline,
        "Qlib增量管道：MultiSourceMarketProvider + dump_to_qlib_bin",
        category="数据同步",
        default_params={"period": "2y", "max_workers": 8, "dump_incremental": True},
        estimated_steps=["拉取 K 线", "写入 CSV", "dump qlib_bin", "完成"],
    )

    register_task(
        "app.tasks.qlib_data_update.csv_to_qlib_incremental_sync",
        qlib_data_update.csv_to_qlib_incremental_sync,
        "CSV→qlib_bin（历史入库推荐，替代 mysql_to_qlib）",
        category="数据同步",
        default_params={"max_workers": 8, "dump_incremental": True},
    )

    register_task(
        "app.tasks.tdx_dayk_tasks.tdx_dayk_full_sync",
        tdx_dayk_tasks.tdx_dayk_full_sync,
        "[别名] TDX 日 K 全量 → 请优先 backfill_all_history_tdx",
        category="数据同步",
        default_params={"limit": None, "dump_qlib_bin": True, "dump_max_workers": 8},
    )

    register_task(
        "app.tasks.tdx_dayk_tasks.tdx_dayk_incremental_sync",
        tdx_dayk_tasks.tdx_dayk_incremental_sync,
        "[别名] TDX 日 K 增量 → 请优先 sync_incremental_tdx",
        category="数据同步",
        default_params={"start_date": None, "dump_qlib_bin": True, "dump_max_workers": 8},
    )

    register_task(
        "app.tasks.market_tasks.refresh_basic_market_data",
        market_tasks.refresh_basic_market_data,
        "刷新基础市场数据：龙虎榜与研报",
        category="市场数据",
        default_params={"kind": "all"},
        estimated_steps=["龙虎榜入库", "研报入库", "完成"],
    )

    register_task(
        "app.tasks.market_tasks.scheduled_longhu",
        market_tasks.scheduled_longhu,
        "定时龙虎榜数据更新",
        category="市场数据",
        default_params={},
    )

    register_task(
        "app.tasks.market_history_tasks.fetch_all_market_history",
        market_history_tasks.fetch_all_market_history,
        "全市场历史数据拉取：港股/美股/加密",
        category="市场数据",
        default_params={},
    )

    register_task(
        "app.tasks.news_backfill_tasks.scheduled_news_daily",
        news_backfill_tasks.scheduled_news_daily,
        "每日新闻归档更新",
        category="新闻",
        default_params={},
    )

    register_task(
        "app.tasks.knowledge_crawl_tasks.crawl_knowledge_bundle",
        knowledge_crawl_tasks.crawl_knowledge_bundle,
        "基础知识库爬取：研报/新闻/财报/产业链 → 本地分类落库",
        category="知识库",
        default_params={
            "codes": ["600519", "000001", "300750"],
            "sources": ["yanbao", "news", "financial", "industry_chain", "corpus"],
            "run_remote": True,
        },
        estimated_steps=["远程爬取", "本地分类落库", "完成"],
    )

    register_task(
        "app.tasks.scanner_tasks.scanner_core_tick",
        scanner_tasks.scanner_core_tick,
        "选股扫描核心 ticking",
        category="信号",
        default_params={"force": False},
    )

    register_task(
        "app.tasks.questdb_sync_tasks.questdb_ohlcv_sync_tick",
        questdb_sync_tasks.questdb_ohlcv_sync_tick,
        "QuestDB·收盘后增量日K同步",
        category="数据同步",
        default_params={},
    )
    register_task(
        "app.tasks.questdb_sync_tasks.timeseries_ohlcv_full_backfill",
        questdb_sync_tasks.timeseries_ohlcv_full_backfill,
        "QuestDB·全市场 OHLCV Backfill（TDX→时序库）",
        category="数据同步",
        default_params={
            "batch_size": None,
            "max_batches": None,
            "offset": 0,
            "truncate_first": False,
        },
    )

    register_task(
        "app.tasks.signal_flag_tasks.signal_flag_pool_scan",
        signal_flag_tasks.signal_flag_pool_scan,
        "信号Flag股票池扫描",
        category="信号",
        default_params={"force": False},
    )

    register_task(
        "app.tasks.investment_manager_tasks.investment_managers_backfill",
        investment_manager_tasks.investment_managers_backfill,
        "投资经理历史数据回填",
        category="投资经理",
        default_params={},
    )

    register_task(
        "app.tasks.investment_manager_tasks.investment_managers_simulate_day",
        investment_manager_tasks.investment_managers_simulate_day,
        "投资经理每日模拟交易",
        category="投资经理",
        default_params={"trade_date": None},
    )

    register_task(
        "app.tasks.moments_tasks.moments_after_close",
        moments_tasks.moments_after_close,
        "收盘后moments生成",
        category="社交",
        default_params={},
    )


def ensure_task_registry() -> dict[str, dict[str, Any]]:
    """Ensure tasks are registered and return registry."""
    global TASK_REGISTRY
    if not TASK_REGISTRY:
        _register_all_tasks()
    return TASK_REGISTRY
