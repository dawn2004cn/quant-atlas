from __future__ import annotations

"""Retail assistant hub: quick actions, overview cards, refacter.md status probes."""

from datetime import datetime, timezone
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime, get_runtime_bool

logger = get_logger(__name__)


class RetailAssistantHubService:
    """Aggregates retail-assistant hub endpoints for /retail-assistant and /capabilities."""

    def quick_actions(self) -> dict[str, Any]:
        return {
            "actions": [
                {
                    "label": "操盘台",
                    "href": "/daily-workbench",
                    "description": "今日 AI Top 3 与晨会卡片",
                },
                {
                    "label": "散户助手",
                    "href": "/retail-assistant",
                    "description": "心理卫士、影子操盘、四维对照",
                },
                {
                    "label": "集成中枢",
                    "href": "/integration-hub",
                    "description": "QuestDB / WebSocket / 数据新鲜度",
                },
                {
                    "label": "数据湖健康",
                    "href": "/data-lake-health",
                    "description": "时序同步进度与探针",
                },
                {
                    "label": "消息中心",
                    "href": "/message-center?filter=psychology",
                    "description": "心理提醒与系统通知",
                },
            ]
        }

    def overview(self) -> dict[str, Any]:
        infra = self._infrastructure_probe()
        ws_partial = infra.get("websocket_partial", True)
        ts_partial = infra.get("timeseries_partial", True)
        return {
            "modules": [
                {
                    "id": "daily_top_picks",
                    "title": "每日 AI Top 3",
                    "status": "implemented",
                    "value": "产业链推荐、买卖区间与胜率回溯",
                    "next_steps": ["操盘台", "采纳计划"],
                    "entry": "/daily-workbench",
                },
                {
                    "id": "psychology_guardian",
                    "title": "心理卫士",
                    "status": "implemented",
                    "value": "自选/观察单行为样本 + 巡检推送",
                    "next_steps": ["psychology-scan", "消息中心"],
                    "entry": "/retail-assistant#psychologyBox",
                },
                {
                    "id": "shadow_mirror",
                    "title": "影子操盘",
                    "status": "implemented",
                    "value": "投研画像 + 持仓权重模拟建议",
                    "next_steps": ["shadow-mirror API"],
                    "entry": "/retail-assistant#shadowMirrorBox",
                },
                {
                    "id": "portfolio_risk",
                    "title": "组合风险",
                    "status": "partial",
                    "value": "持仓集中度与止损确认（需自选/组合数据）",
                    "next_steps": ["自选股", "trade-plan"],
                    "entry": "/retail-assistant#portfolio-risk",
                },
                {
                    "id": "knowledge_qa",
                    "title": "可追问知识",
                    "status": "implemented",
                    "value": "研报中心联动的问题建议",
                    "next_steps": ["yanbao-hub"],
                    "entry": "/yanbao-hub",
                },
                {
                    "id": "infrastructure",
                    "title": "基础设施",
                    "status": "partial" if (ws_partial or ts_partial) else "implemented",
                    "value": infra.get("summary", "QuestDB 与时序/WebSocket 探针"),
                    "next_steps": infra.get("next_steps", []),
                    "entry": "/integration-hub",
                },
            ]
        }

    def knowledge_suggestions(self, *, symbol: str | None = None) -> dict[str, Any]:
        sym = (symbol or "").strip() or "标的"
        return {
            "symbol": symbol,
            "questions": [
                f"{sym} 当前产业链上下游景气度如何？",
                f"{sym} 近期研报一致预期与估值分位？",
                f"{sym} 若市场风格切换，哪些因子最敏感？",
            ],
        }

    def portfolio_risk(self) -> dict[str, Any]:
        return {
            "summary": "组合风险摘要需登录用户持仓或自选股；以下为占位引导。",
            "cards": [],
            "hint": "添加自选股或导入组合后重新加载",
        }

    def refactor_status(self) -> dict[str, Any]:
        infra = self._infrastructure_probe()
        ths_status = self._ths_probe_status()
        qmt = infra.get("qmt") or {}
        return {
            "available": True,
            "source_doc": "docs/refacter.md",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "probes": {
                "websocket": infra.get("websocket", {}),
                "timeseries": infra.get("timeseries", {}),
                "ths": infra.get("ths", {}),
                "qmt": qmt,
            },
            "pillars": [
                {
                    "title": "1. AI 智能体进化",
                    "items": [
                        {"name": "证据驱动路由 / 黑板 / AutoValidator", "status": "implemented"},
                        {"name": "分级模型调度 TieredLLM", "status": "implemented"},
                        {"name": "元学习权重自动调参", "status": "implemented"},
                    ],
                },
                {
                    "title": "2. 散户 AI 炒股助手",
                    "items": [
                        {"name": "每日 AI Top 3", "status": "implemented"},
                        {"name": "标准化诊股报告", "status": "implemented"},
                        {"name": "产业链智能图谱", "status": "implemented"},
                        {"name": "心理卫士 / 影子操盘", "status": "implemented"},
                        {"name": "证据链溯源 / 决策快照", "status": "implemented"},
                    ],
                },
                {
                    "title": "3. 高性能基础设施",
                    "items": [
                        {"name": "Rust 指标引擎", "status": "partial"},
                        {"name": "Redis / 鲜度条", "status": "partial"},
                        {
                            "name": "QuestDB / ClickHouse 海量 K 线",
                            "status": infra.get("timeseries_status", "partial"),
                            "detail": infra.get("timeseries_detail"),
                        },
                        {
                            "name": "WebSocket 实时行情 (quote_update)",
                            "status": infra.get("websocket_status", "partial"),
                            "detail": infra.get("websocket_detail"),
                        },
                        {
                            "name": "同花顺板块 THS 会话",
                            "status": ths_status,
                        },
                        {
                            "name": "QMT 执行网关 (simulation/live)",
                            "status": "partial"
                            if qmt.get("execution_mode") == "simulation"
                            else (
                                "implemented"
                                if qmt.get("execution_mode") == "live"
                                else "partial"
                            ),
                            "detail": qmt.get("warning") or qmt.get("execution_mode"),
                        },
                    ],
                },
                {
                    "title": "4. 多资产与全球化",
                    "items": [
                        {"name": "A 股 / 港股 / 美股 / Crypto", "status": "implemented"},
                        {"name": "期货 / 外汇统一 MarketCode", "status": "planned"},
                        {"name": "全球联动（美股映射 A 股）", "status": "partial"},
                        {"name": "前端 i18n", "status": "planned"},
                    ],
                },
            ],
        }

    def _ths_probe_status(self) -> str:
        try:
            from app.config import get_settings

            if get_settings().ths.has_credentials:
                return "partial"
        except Exception:
            logger.debug("THS settings probe failed", exc_info=True)
        return "partial"

    def _infrastructure_probe(self) -> dict[str, Any]:
        socketio_on = get_runtime_bool("ENABLE_SOCKETIO", False)
        origins = (get_runtime("SOCKETIO_ALLOWED_ORIGINS", "") or "").strip()
        quote_on = get_runtime_bool("ENABLE_QUOTE_WS_BROADCAST", True)
        ws_ready = socketio_on and bool(origins)
        ws_status = "implemented" if ws_ready and quote_on else "partial"
        ws_detail_parts: list[str] = []
        if not socketio_on:
            ws_detail_parts.append("ENABLE_SOCKETIO=0")
        elif not origins:
            ws_detail_parts.append("SOCKETIO_ALLOWED_ORIGINS 未配置")
        if not quote_on:
            ws_detail_parts.append("ENABLE_QUOTE_WS_BROADCAST=0")
        if ws_ready:
            ws_detail_parts.append("base_app 订阅 market+alerts")

        ts_status = "partial"
        ts_detail = ""
        ts_payload: dict[str, Any] = {}
        try:
            from app.infrastructure.timeseries.timeseries_factory import timeseries_health_probe

            ts_payload = timeseries_health_probe()
            q = ts_payload.get("questdb") or {}
            if q.get("enabled") and q.get("connected"):
                rows = int((ts_payload.get("ohlcv_tables") or {}).get("questdb_rows") or 0)
                if rows >= 1_000_000:
                    ts_status = "implemented"
                    ts_detail = f"QuestDB 已连通 · {rows:,} 行"
                else:
                    ts_detail = f"QuestDB 已连通 · {rows:,} 行（建议 backfill）"
            elif q.get("enabled"):
                ts_detail = "QuestDB 已启用但未连通"
            else:
                ts_detail = str(q.get("reason") or "QuestDB 未启用")
            warnings = ts_payload.get("warnings") or []
            if warnings:
                ts_detail += f" · warnings={','.join(warnings)}"
        except Exception as exc:
            logger.debug("timeseries health probe failed: %s", exc)
            ts_detail = "探针不可用"

        beat_meta: dict[str, Any] = {}
        try:
            from app.infrastructure.timeseries.sync_snapshot import get_timeseries_sync_history

            beat = (ts_payload.get("celery_beat") or {}) if ts_payload else {}
            beat_meta = {
                "enabled": beat.get("enabled"),
                "schedule_label": beat.get("schedule_label"),
                "last_beat_run_at": beat.get("last_beat_run_at"),
                "last_beat_run_ok": beat.get("last_beat_run_ok"),
                "sync_in_progress": beat.get("sync_in_progress"),
                "beat_history_count": len(
                    get_timeseries_sync_history(limit=100, source="celery_beat")
                ),
            }
        except Exception:
            logger.debug("beat history probe failed", exc_info=True)

        ths: dict[str, Any] = {"configured": False}
        try:
            from app.config import get_settings

            ths_cfg = get_settings().ths
            ths = {
                "configured": ths_cfg.has_credentials,
                "username_set": bool(ths_cfg.username),
            }
        except Exception:
            logger.debug("THS settings probe failed", exc_info=True)

        qmt: dict[str, Any] = {}
        try:
            from app.config import get_settings
            from app.infrastructure.execution.qmt_executor import qmt_executor_status

            qmt_cfg = get_settings().qmt
            qmt = qmt_executor_status(
                account_id=qmt_cfg.account_id or "",
                qmt_path=qmt_cfg.qmt_path or "",
            )
        except Exception:
            qmt = {"execution_mode": "disabled"}

        next_steps: list[str] = []
        if ws_status == "partial":
            next_steps.append("配置 SOCKETIO + origins")
        if ts_status == "partial":
            next_steps.append("QuestDB 同步 / data-lake-health")

        return {
            "summary": f"WebSocket {ws_status} · 时序 {ts_status}",
            "websocket_partial": ws_status != "implemented",
            "timeseries_partial": ts_status != "implemented",
            "websocket_status": ws_status,
            "websocket_detail": "; ".join(ws_detail_parts) or "就绪",
            "timeseries_status": ts_status,
            "timeseries_detail": ts_detail,
            "next_steps": next_steps,
            "websocket": {
                "socketio_enabled": socketio_on,
                "origins_configured": bool(origins),
                "quote_broadcast": quote_on,
                "client_rooms": ["market", "alerts"],
            },
            "timeseries": {
                "status": ts_status,
                "detail": ts_detail,
                "probe": ts_payload,
                "beat": beat_meta,
            },
            "ths": ths,
            "qmt": qmt,
        }
