from __future__ import annotations

"""Unified UX contract for the decision workflow."""

from typing import Any


class DecisionFlowContractService:
    """Describe the completed user decision path for API and frontend clients."""

    def build_contract(self, *, market: str = "CN", symbol: str = "{symbol}") -> dict[str, Any]:
        market = (market or "CN").upper()
        symbol = symbol or "{symbol}"
        return {
            "version": "2026-05-ux-decision-flow-v2",
            "goal": "reduce cross-page manual alignment for investment decisions",
            "entrypoints": [
                self._search_entry(market),
                self._stock_entry(market, symbol),
                self._strategy_entry(market, symbol),
                self._task_entry(),
                self._sector_entry(market),
            ],
            "component_types": [
                {
                    "type": "quote_strip",
                    "purpose": "compact quote and factual price label",
                    "source": "stock decision brief",
                },
                {
                    "type": "risk_banner",
                    "purpose": "data coverage and confidence warning",
                    "source": "stock decision brief",
                },
                {
                    "type": "evidence_timeline",
                    "purpose": "date-aligned news, reports, orders and price events",
                    "source": "attribution timeline",
                },
                {
                    "type": "action_bar",
                    "purpose": "contextual next actions for researcher or trader roles",
                    "source": "user decision context",
                },
            ],
            "role_profiles": {
                "researcher": {
                    "density": "deep",
                    "emphasis": ["raw_factors", "evidence_chain", "reports"],
                },
                "trader": {
                    "density": "compact",
                    "emphasis": ["signals", "risk_warnings", "action_items"],
                },
                "default": {
                    "density": "balanced",
                    "emphasis": ["summary", "evidence_chain", "signals"],
                },
            },
            "recommended_flow": [
                "discover candidates with /stocks/search?mode=discover",
                "open /stocks/{market}/{symbol}/decision-brief for renderable components",
                "overlay /stocks/{market}/{symbol}/attribution-timeline on the chart",
                "stress /strategy/copilot with sensitivity parameters before acting",
                "POST /trade-plan/adopt to persist plan into signal observations",
                "watch async jobs through /system/active-jobs and /system/tasks/{task_id}/feedback",
            ],
            "evidence_hubs": [
                self._yanbao_entry(),
                self._longhu_entry(market),
            ],
            "retail_assistant": self._retail_assistant_entry(market),
            "ui_surfaces": self._ui_surfaces(),
            "self_check_probes": self._self_check_probes(market, symbol),
        }

    @staticmethod
    def _search_entry(market: str) -> dict[str, Any]:
        return {
            "id": "search_discovery",
            "page": "stock_search",
            "problem": "users remember intent, not exact ticker code",
            "endpoint": f"/api/v1/stocks/search?market={market}&mode=discover&q={{query}}&tags={{tags}}",
            "returns": ["stocks", "discovery.intent", "discovery.filters", "rank_reasons"],
            "status": "implemented",
        }

    @staticmethod
    def _stock_entry(market: str, symbol: str) -> dict[str, Any]:
        return {
            "id": "stock_evidence",
            "page": "stock_detail",
            "problem": "users manually align news, reports and price action",
            "endpoints": {
                "brief": f"/api/v1/stocks/{market}/{symbol}/decision-brief?role={{role}}",
                "timeline": f"/api/v1/stocks/{market}/{symbol}/attribution-timeline",
                "coverage": f"/api/v1/stocks/{market}/{symbol}/data-coverage",
            },
            "returns": [
                "components",
                "warnings",
                "timeline_summary",
                "attribution_timeline",
                "sector_context",
            ],
            "status": "implemented",
        }

    @staticmethod
    def _strategy_entry(market: str, symbol: str) -> dict[str, Any]:
        return {
            "id": "strategy_sandbox",
            "page": "strategy_copilot",
            "problem": "users need fast stress testing without a heavy backtest",
            "endpoint": (
                f"/api/v1/strategy/copilot?symbol={symbol}&market={market}"
                "&market_shock_pct={shock}&volatility_threshold={vol}&stop_loss_pct={stop}"
            ),
            "returns": [
                "top_pick",
                "alternatives",
                "sensitivity_sandbox",
                "suggested_trade_plan",
                "trade_plan_action",
            ],
            "adopt_endpoint": "POST /api/v1/trade-plan/adopt",
            "status": "implemented",
        }

    @staticmethod
    def _task_entry() -> dict[str, Any]:
        return {
            "id": "phased_feedback",
            "page": "task_center",
            "problem": "long tasks look frozen without phase progress",
            "endpoints": {
                "active_jobs": "/api/v1/system/active-jobs",
                "feedback": "/api/v1/system/tasks/{task_id}/feedback?task_name={task_name}",
                "stream": "/api/v1/system/tasks/{task_id}/stream?task_name={task_name}",
                "phase_preview": "/api/v1/system/task-phase-plan?task_name={task_name}",
            },
            "returns": ["percent", "current_step", "next_step", "step_details", "phase_source"],
            "status": "implemented",
        }

    @staticmethod
    def _sector_entry(market: str) -> dict[str, Any]:
        return {
            "id": "predictive_preload",
            "page": "hot_sectors",
            "problem": "sector browsing repeatedly waits for the same next-detail calls",
            "endpoint": f"/api/v1/hot-sectors/{{sector_code}}/preload-plan?market={market}",
            "returns": ["candidates", "prefetch.urls", "policy"],
            "status": "implemented",
        }

    @staticmethod
    def _retail_assistant_entry(market: str) -> dict[str, Any]:
        return {
            "id": "retail_daily_top",
            "page": "daily_workbench",
            "problem": "retail users need actionable morning picks with chain context",
            "endpoints": {
                "daily_top_picks": f"/api/v1/retail-assistant/daily-top-picks?market={market}&top_n=3",
                "diagnosis": f"/api/v1/diagnosis/report?symbol={{symbol}}&market={market}",
                "psychology": "/api/v1/retail-assistant/psychology-guardian",
                "psychology_status": "/api/v1/retail-assistant/psychology-status",
                "shadow_mirror": "/api/v1/retail-assistant/shadow-mirror",
                "refactor_status": "/api/v1/retail-assistant/refactor-status",
                "psychology_scan": "POST /api/v1/retail-assistant/psychology-scan",
                "psychology_batch": "POST /api/v1/system/retail-psychology-scan",
                "meta_learning_status": "/api/v1/retail-assistant/meta-learning-status",
                "meta_learning_evolve": "POST /api/v1/system/retail-meta-learning-evolve",
            },
            "returns": [
                "one_line_verdict",
                "industry_position",
                "buy_zone",
                "stop_loss",
                "estimated_win_rate",
            ],
            "status": "implemented",
        }

    @staticmethod
    def _yanbao_entry() -> dict[str, Any]:
        return {
            "id": "yanbao_hub",
            "page": "yanbao_hub",
            "problem": "research reports are disconnected from stock decision context",
            "endpoints": {
                "feed": "/api/v1/market/yanbao?category={category}&limit=120",
                "refresh": "POST /api/v1/market/basic-data/refresh {\"kind\": \"yanbao\"}",
            },
            "returns": ["items", "data_timestamp", "is_realtime", "freshness"],
            "links": {"brief": "/stock/{symbol}?m=CN#decision-brief-strip"},
            "status": "implemented",
        }

    @staticmethod
    def _longhu_entry(market: str) -> dict[str, Any]:
        return {
            "id": "longhu_bang",
            "page": "longhu_bang",
            "problem": "dragon-tiger board data lacks freshness trust and decision handoff",
            "endpoints": {
                "list": "/api/v1/market/longhu?date={YYYY-MM-DD}&limit=400",
                "refresh": "POST /api/v1/market/basic-data/refresh {\"kind\": \"longhu\"}",
                "stock_band": f"/api/v1/stocks/{market}/{{symbol}}/longhu-band",
            },
            "returns": ["trade_date", "items", "data_timestamp", "is_realtime", "freshness"],
            "links": {"brief": "/stock/{symbol}?m=CN#decision-brief-strip"},
            "status": "implemented",
        }

    @staticmethod
    def _ui_surfaces() -> list[dict[str, Any]]:
        return [
            {"page": "daily_workbench", "path": "/", "features": ["freshness", "active_jobs", "decision_brief", "adopt_plan"]},
            {
                "page": "stock_detail",
                "path": "/stock/{symbol}",
                "features": [
                    "decision_brief",
                    "supporting_evidence",
                    "decision_snapshot",
                    "attribution_timeline",
                    "sector_context",
                    "adopt_plan",
                    "trade_plan_soft_warnings",
                ],
            },
            {
                "page": "strategy_snapshots",
                "path": "/strategy-snapshots",
                "features": ["deploy_snapshot", "decision_snapshot_list", "decision_snapshot_public_share"],
            },
            {"page": "decision_snapshot_public", "path": "/share/decision/{token}", "features": ["read_only_replay"]},
            {"page": "self_stocks", "path": "/self-stocks", "features": ["quote_freshness", "brief_link", "adopt_plan"]},
            {"page": "hot_sectors", "path": "/hot-sectors", "features": ["sector_freshness", "brief_link"]},
            {"page": "tdx_blocks", "path": "/tdx-blocks", "features": ["panorama_freshness", "brief_link"]},
            {"page": "integration_hub", "path": "/integration-hub", "features": ["active_jobs", "task_run", "task_messages"]},
            {"page": "task_center", "path": "/task-center", "features": ["estimated_steps", "task_feedback"]},
            {"page": "capabilities", "path": "/capabilities", "features": ["self_check", "panorama_freshness"]},
            {"page": "yanbao_hub", "path": "/yanbao-hub", "features": ["feed_freshness", "async_refresh"]},
            {"page": "longhu_bang", "path": "/longhu-bang", "features": ["feed_freshness", "async_refresh", "brief_link"]},
            {"page": "ai_research_report", "path": "/ai-research-report", "features": ["decision_brief_mini", "adopt_plan"]},
            {
                "page": "retail_assistant",
                "path": "/retail-assistant",
                "features": ["daily_top_picks", "psychology_guardian", "shadow_mirror", "refactor_status"],
            },
            {
                "page": "daily_workbench",
                "path": "/daily-workbench",
                "features": ["daily_top_3", "adopt_plan", "freshness"],
            },
            {
                "page": "message_center",
                "path": "/message-center",
                "features": ["task_messages", "psychology_filter", "category=retail_psychology"],
            },
        ]

    @staticmethod
    def _self_check_probes(market: str, symbol: str) -> list[dict[str, Any]]:
        sym = symbol if symbol and symbol != "{symbol}" else "600519"
        return [
            {
                "id": "ux_contract",
                "label": "决策流契约",
                "method": "GET",
                "url": f"/api/v1/ux/decision-flow?market={market}&symbol={sym}",
                "expect_keys": ["version", "entrypoints", "self_check_probes"],
            },
            {
                "id": "panorama_freshness",
                "label": "市场全景鲜度",
                "method": "GET",
                "url": f"/api/v1/markets/{market}/panorama",
                "expect_keys": ["data_timestamp"],
            },
            {
                "id": "active_jobs",
                "label": "活跃后台任务",
                "method": "GET",
                "url": "/api/v1/system/active-jobs?limit=5",
                "expect_keys": ["items"],
            },
            {
                "id": "decision_brief",
                "label": "决策简报",
                "method": "GET",
                "url": f"/api/v1/stocks/{market}/{sym}/decision-brief",
                "expect_keys": ["components", "header", "supporting_evidence"],
                "nested_keys": {"supporting_evidence": ["factors", "report_citations"]},
            },
            {
                "id": "decision_snapshot_list",
                "label": "决策快照列表",
                "method": "GET",
                "url": "/api/v1/decision/snapshots?limit=5",
                "expect_keys": ["data"],
            },
            {
                "id": "trade_plan_guardrails",
                "label": "买卖计划软警告",
                "method": "GET",
                "url": f"/api/v1/trade-plan?symbol={sym}&market={market}",
                "expect_keys": ["plan", "soft_warnings"],
            },
            {
                "id": "hot_sectors",
                "label": "热点板块鲜度",
                "method": "GET",
                "url": "/api/v1/hot-sectors?limit=5&source=auto",
                "expect_keys": ["sectors", "data_timestamp"],
            },
            {
                "id": "longhu_feed",
                "label": "龙虎榜鲜度",
                "method": "GET",
                "url": "/api/v1/market/longhu?limit=5",
                "expect_keys": ["items", "data_timestamp"],
            },
            {
                "id": "yanbao_feed",
                "label": "研报 feed 鲜度",
                "method": "GET",
                "url": "/api/v1/market/yanbao?limit=5",
                "expect_keys": ["items", "data_timestamp"],
            },
            {
                "id": "retail_daily_top",
                "label": "散户 Top3 推荐",
                "method": "GET",
                "url": f"/api/v1/retail-assistant/daily-top-picks?market={market}&top_n=3",
                "expect_keys": ["items", "top_n"],
            },
            {
                "id": "retail_refactor_status",
                "label": "refacter 四维对照",
                "method": "GET",
                "url": "/api/v1/retail-assistant/refactor-status",
                "expect_keys": ["pillars", "source_doc"],
            },
            {
                "id": "retail_psychology",
                "label": "心理卫士",
                "method": "GET",
                "url": "/api/v1/retail-assistant/psychology-guardian",
                "expect_keys": ["ok", "status", "alerts"],
            },
            {
                "id": "retail_shadow_mirror",
                "label": "影子操盘",
                "method": "GET",
                "url": f"/api/v1/retail-assistant/shadow-mirror?symbol={sym}",
                "expect_keys": ["mirrors", "ok"],
            },
            {
                "id": "retail_psychology_status",
                "label": "心理卫士摘要",
                "method": "GET",
                "url": "/api/v1/retail-assistant/psychology-status",
                "expect_keys": ["status", "alert_count", "history_samples"],
            },
            {
                "id": "retail_psychology_scan",
                "label": "心理卫士·用户巡检",
                "method": "POST",
                "url": "/api/v1/retail-assistant/psychology-scan",
                "expect_keys": ["ok", "status", "history_samples"],
            },
            {
                "id": "timeseries_health",
                "label": "QuestDB/时序健康",
                "method": "GET",
                "url": "/api/v1/data/timeseries-health",
                "expect_keys": ["ok", "questdb"],
            },
            {
                "id": "realtime_status",
                "label": "WebSocket 实时状态",
                "method": "GET",
                "url": "/api/v1/realtime/status",
                "expect_keys": ["socketio_enabled", "rooms", "base_subscriptions"],
            },
            {
                "id": "execution_manifest",
                "label": "执行网关清单 (QMT simulation)",
                "method": "GET",
                "url": "/api/v1/execution/manifest",
                "expect_keys": ["default_mode", "drivers", "qmt"],
                "nested_keys": {"qmt": ["execution_mode", "live_submit"]},
            },
            {
                "id": "integration_stack",
                "label": "集成栈状态",
                "method": "GET",
                "url": "/api/v1/integration/stack-status",
                "expect_keys": ["layers", "mysql_enabled"],
                "nested_keys": {
                    "layers": ["timeseries_ohlcv", "execution_gateway", "celery_tasks"],
                },
            },
            {
                "id": "timeseries_sync_history",
                "label": "Beat 同步历史",
                "method": "GET",
                "url": "/api/v1/data/timeseries-sync-history?limit=5&source=celery_beat",
                "expect_keys": ["runs", "count"],
            },
        ]


__all__ = ["DecisionFlowContractService"]
