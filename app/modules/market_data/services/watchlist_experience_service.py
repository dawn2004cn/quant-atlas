from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""High-level watchlist experience service."""


from datetime import datetime
from typing import Any

from app.domain.enums import MarketCode
def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


class WatchlistExperienceService:
    """Build sticky watchlist views: sorting, alerts and batch actions."""

    def __init__(
        self,
        *,
        watchlist_agent_service: object,
        review_tracking_service: Any | None = None,
    ) -> None:
        self._agent = watchlist_agent_service
        self._review = review_tracking_service

    def dashboard(
        self,
        user_id: int = 1,
        *,
        market: MarketCode = MarketCode.CN,
        group_id: int | None = None,
        sort_by: str = "priority",
        include_news: bool = False,
    ) -> GenericResponseDTO:
        snapshot = self._agent.build_snapshot(
            user_id=user_id,
            market=market,
            group_id=group_id,
            limit=100,
            include_news=include_news,
        )
        items = self._sort_items(list(snapshot.get("items") or []), sort_by=sort_by)
        alerts = self._alerts(items)
        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market": market.value,
            "active_group": snapshot.get("active_group") or {},
            "sort_by": sort_by,
            "summary": snapshot.get("summary") or {},
            "items": items,
            "exposure": snapshot.get("exposure") or {},
            "group_radar": snapshot.get("group_radar") or [],
            "alerts": alerts,
            "batch_actions": self._batch_actions(items),
            "review": self._weekly_review(),
            "share_card": self.share_card(items=items, group=snapshot.get("active_group") or {}),
            "export": {
                "available": True,
                "format": "json",
                "hint": "MVP 阶段通过 API 返回结构化数据，后续接 Excel 导出。",
            },
            "evidence": ["watchlist_agent", "signal_observations"],
            "confidence": 0.78,
        }

    def share_card(self, *, items: list[dict[str, Any]], group: dict[str, Any] | None = None) -> GenericResponseDTO:
        top = items[:3]
        title = f"{(group or {}).get('name') or '自选股'}观察卡"
        highlights = [
            f"{it.get('name') or it.get('code')}：健康分 {int(_safe_float(it.get('health_score')))}，{it.get('action') or '观察'}"
            for it in top
        ]
        return {
            "title": title,
            "highlights": highlights,
            "watermark": "Quant Atlas · 仅供研究复盘，不构成投资建议",
            "disclaimer": "分享内容基于自选股行情、信号和模拟观察生成，需自行决策。",
        }

    def _sort_items(self, items: list[dict[str, Any]], *, sort_by: str) -> list[dict[str, Any]]:
        key = str(sort_by or "priority").lower()
        if key == "risk":
            return sorted(items, key=lambda x: len(x.get("risk_notes") or []), reverse=True)
        if key == "change":
            return sorted(items, key=lambda x: _safe_float(x.get("change_pct")), reverse=True)
        if key == "health":
            return sorted(items, key=lambda x: _safe_float(x.get("health_score")), reverse=True)
        if key == "amount":
            return sorted(items, key=lambda x: _safe_float(x.get("amount")), reverse=True)
        return sorted(items, key=lambda x: (_safe_float(x.get("priority")), _safe_float(x.get("health_score"))), reverse=True)

    def _alerts(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        for item in items:
            change = _safe_float(item.get("change_pct"))
            risks = item.get("risk_notes") or []
            if change >= 5:
                alerts.append(self._alert(item, "price_breakout", "high", f"涨幅 {change:.2f}%，关注止盈和追高风险"))
            if change <= -5:
                alerts.append(self._alert(item, "drawdown", "high", f"跌幅 {change:.2f}%，检查止损线"))
            if risks:
                alerts.append(self._alert(item, "risk_change", "medium", "；".join(str(x) for x in risks[:2])))
        return alerts[:12]

    def _alert(self, item: dict[str, Any], kind: str, level: str, content: str) -> GenericResponseDTO:
        return {
            "kind": kind,
            "level": level,
            "symbol": item.get("code"),
            "name": item.get("name") or item.get("code"),
            "content": content,
            "links": item.get("links") or {},
        }

    def _batch_actions(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        codes = [str(x.get("code") or "") for x in items if x.get("code")]
        return [
            {
                "id": "batch_diagnosis",
                "title": "AI 批量诊股",
                "enabled": bool(codes),
                "symbols": codes[:20],
                "description": "逐只打开诊股报告，后续接异步批量任务。",
            },
            {
                "id": "weekly_review",
                "title": "自选股周复盘",
                "enabled": True,
                "description": "基于观察单和自选股健康分生成复盘摘要。",
            },
            {
                "id": "share_card",
                "title": "生成分享卡片",
                "enabled": bool(codes),
                "description": "生成带水印和免责声明的朋友圈分享摘要。",
            },
        ]

    def _weekly_review(self) -> GenericResponseDTO:
        if self._review is None:
            return {"available": False, "summary": "复盘服务未接入"}
        try:
            return self._review.weekly_review()
        except Exception:
            return {"available": False, "summary": "复盘数据暂不可用"}
