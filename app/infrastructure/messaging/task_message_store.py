from __future__ import annotations
"""Celery 任务事件写入 Redis 列表（或内存回退），供消息中心 API 读取。"""


import json
from collections import deque
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import logging

from ...core.runtime_config import get_runtime


from app.core.logger import get_logger

logger = get_logger(__name__)

REDIS_KEY = "quant:task_messages"
MAX_MESSAGES = 500

_singleton: TaskMessageStore | None = None


def configure_task_message_store(url: str) -> TaskMessageStore:
    """在 Flask ``create_app`` 中调用，与 Celery worker 环境变量保持一致。"""
    global _singleton
    _singleton = TaskMessageStore(url)
    return _singleton


def get_task_message_store() -> TaskMessageStore:
    """Worker 信号与未显式 configure 时的默认入口。"""
    global _singleton
    if _singleton is None:
        url = (
            (get_runtime("TASK_MESSAGE_REDIS_URL", "") or "").strip()
            or (get_runtime("CELERY_BROKER_URL", "") or "").strip()
            or ""
        )
        _singleton = TaskMessageStore(url)
    return _singleton


def task_label(task_name: str) -> str:
    return _LABELS.get(task_name, task_name)


_LABELS: dict[str, str] = {
    "app.tasks.market_tasks.refresh_basic_market_data": "基础数据·手动刷新",
    "app.tasks.market_tasks.scheduled_longhu": "基础数据·龙虎榜定时",
    "app.tasks.market_tasks.scheduled_yanbao": "基础数据·研报定时",
    "inline.basic_data_refresh": "基础数据·同步刷新",
    "app.tasks.scanner_tasks.scanner_core_tick": "行情扫描·核心池",
    "app.tasks.scanner_tasks.scanner_rotation_tick": "行情扫描·全市场轮询",
    "app.tasks.qlib_data_update.qlib_incremental_pipeline": "Qlib·TDX多源→CSV→bin增量",
    "app.tasks.qlib_data_update.qlib_full_backfill_if_empty": "Qlib·无CSV时全量种子K线→bin",
    "inline.qlib_incremental_pipeline": "Qlib·管线同步执行",
    "app.tasks.data_backfill_tasks.backfill_longhu_if_empty": "存量回填·龙虎榜（无数据时）",
    "app.tasks.data_backfill_tasks.backfill_longhu_full": "全量回填·龙虎榜（强制分段）",
    "app.tasks.data_backfill_tasks.backfill_yanbao_full": "全量回填·研报（加深行数）",
    "app.tasks.data_backfill_tasks.backfill_financial_stash_if_empty": "存量回填·财报快照（空表时）",
    "app.tasks.data_backfill_tasks.backfill_qlib_kline_if_empty": "存量回填·通达信K线→CSV/bin（无CSV时）",
    "app.tasks.data_backfill_tasks.scheduled_financial_stash_refresh": "财报快照·每日刷新",
    "app.tasks.news_backfill_tasks.backfill_news_archive_for_codes": "全量回填·新闻归档（强制刷新）",
    "app.tasks.factor_ic_alerts.factor_ic_monitor_tick": "因子监控·IC 弱信号巡检",
    "app.tasks.signal_flag_tasks.signal_flag_pool_scan": "信号旗·全市场池扫描",
    "app.tasks.signal_flag_tasks.signal_flag_pool_backfill": "信号旗·历史回填",
    "inline.signal_flag_pool_scan": "信号旗·池扫描（同步）",
    "inline.celery_revoke": "Celery·任务撤销",
    "rdagent.run_factor_generation": "RD-Agent·因子挖掘循环",
    "app.tasks.investment_manager_tasks.investment_managers_backfill": "投资经理·历史回放",
    "app.tasks.investment_manager_tasks.investment_managers_quick_warmup": "投资经理·快速预热（排期+模拟）",
    "app.tasks.investment_manager_tasks.investment_managers_simulate_day": "投资经理·单日模拟",
    "app.tasks.tdx_gpcw_tasks.backfill_tdx_gpcw_full": "TDX gpcw·存量全量入库",
    "app.tasks.tdx_gpcw_tasks.import_tdx_gpcw_latest": "TDX gpcw·新增增量入库",
    "app.tasks.tdx_gpcw_tasks.import_tdx_gpcw_for_stock": "TDX gpcw·单股数据入库",
    "app.tasks.investment_manager_tasks.post_close_signal_then_managers": "收盘链·信号旗→投资经理",
    "retail.psychology_guardian": "心理卫士·行为提醒",
    "app.tasks.retail_psychology_tasks.psychology_guardian_tick": "心理卫士·定时巡检",
    "app.tasks.retail_meta_learning_tasks.meta_learning_evolve_tick": "元学习·Prompt 演化",
    "app.tasks.questdb_sync_tasks.questdb_ohlcv_sync_tick": "QuestDB·日K同步",
    "app.tasks.questdb_sync_tasks.timeseries_ohlcv_full_backfill": "QuestDB·全市场 OHLCV Backfill",
    "app.tasks.tdx_timescale_sync_tasks.tdx_timescale_sync_tick": "Timescale·TDX日K",
    "app.tasks.ohlcv_reconciliation_tasks.ohlcv_reconciliation_tick": "日K·多库对账抽检",
    "app.tasks.data_backfill_tasks.scheduled_cn_history_daily": "收盘链·TDX+qlib日更",
}


class TaskMessageStore:
    def __init__(self, redis_url: str) -> None:
        self._url = (redis_url or "").strip()
        self._redis: Any = None
        self._memory: deque[dict[str, Any]] = deque(maxlen=MAX_MESSAGES)
        self._use_memory = self._url in ("", "memory://", "disabled")
        if not self._use_memory:
            try:
                import redis

                self._redis = redis.Redis.from_url(
                    self._url,
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                    socket_timeout=2.0,
                )
                self._redis.ping()
            except Exception as exc:  # noqa: BLE001
                logger.warning("task message redis unavailable, using memory: %s", exc)
                self._redis = None
                self._use_memory = True

    @property
    def enabled_backend(self) -> str:
        if self._redis is not None:
            return "redis"
        return "memory"

    def push(
        self,
        *,
        event: str,
        task_id: str,
        task_name: str,
        detail: str = "",
        meta: dict[str, Any] | None = None,
    ) -> str:
        msg_id = str(uuid4())
        payload: dict[str, Any] = {
            "id": msg_id,
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event": event,
            "task_id": task_id,
            "task_name": task_name,
            "label": task_label(task_name),
            "detail": (detail or "")[:2000],
            "meta": meta or {},
        }
        line = json.dumps(payload, ensure_ascii=False)
        if self._redis is not None:
            try:
                pipe = self._redis.pipeline()
                pipe.lpush(REDIS_KEY, line)
                pipe.ltrim(REDIS_KEY, 0, MAX_MESSAGES - 1)
                pipe.execute()
            except Exception as exc:  # noqa: BLE001
                logger.warning("task message lpush failed: %s", exc)
                self._memory.appendleft(payload)
        else:
            self._memory.appendleft(payload)
        try:
            from app.infrastructure.messaging.task_event_hub import get_task_event_hub

            get_task_event_hub().publish(task_id, payload)
        except Exception as exc:  # noqa: BLE001
            logger.debug("task event hub publish skipped: %s", exc)
        return msg_id

    def list_recent(self, *, limit: int = 80) -> list[dict[str, Any]]:
        lim = min(max(1, limit), 200)
        if self._redis is not None:
            try:
                rows = self._redis.lrange(REDIS_KEY, 0, lim - 1)
                out: list[dict[str, Any]] = []
                for x in rows:
                    try:
                        out.append(json.loads(x))
                    except json.JSONDecodeError:
                        continue
                return out
            except Exception as exc:  # noqa: BLE001
                logger.warning("task message lrange failed: %s", exc)
        return list(self._memory)[:lim]
