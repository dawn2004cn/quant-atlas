from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Watchlist agent service.

The service turns raw watchlist quotes into an explainable portfolio watch
radar: health score, anomaly reasons, group radar and deep-analysis links.
"""


import dataclasses
from datetime import datetime
from enum import Enum
from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode
logger = get_logger(__name__)


def _to_dict(value: object) -> GenericResponseDTO:
    """Convert value to dict (Pydantic, dataclass, or plain object)."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        row = dataclasses.asdict(value)
        for key, val in list(row.items()):
            if isinstance(val, Enum):
                row[key] = val.value
        return row
    if hasattr(value, "__dict__"):
        row = {k: v for k, v in vars(value).items() if not str(k).startswith("_")}
        for key, val in list(row.items()):
            if isinstance(val, Enum):
                row[key] = val.value
        return row
    return {}


def _safe_float(value: object, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


class WatchlistAgentService:
    """Build an explainable watchlist health and group radar snapshot."""

    def __init__(
        self,
        *,
        market_service: object,
        stock_service: object,
        watchlist_service: object,
        stock_group_service: object,
    ) -> None:
        self._market_service = market_service
        self._stock_service = stock_service
        self._watchlist_service = watchlist_service
        self._stock_group_service = stock_group_service

    def subscribe_to_events(self) -> None:
        """Subscribe to WatchlistAnomalyDetectedEvent to auto-trigger analysis."""
        try:
            from app.core.event_bus import WatchlistAnomalyDetectedEvent, get_event_bus
            bus = get_event_bus()
            bus.subscribe(WatchlistAnomalyDetectedEvent, self._on_anomaly, priority=50)
        except Exception as exc:
            from app.core.logger import get_logger
            get_logger(__name__).warning("watchlist event subscribe: %s", exc)

    def _on_anomaly(self, event: WatchlistAnomalyDetectedEvent) -> None:
        """Handle watchlist anomaly event by logging and optionally triggering analysis."""
        from app.core.logger import get_logger

        logger = get_logger(__name__)
        logger.info(
            "Watchlist anomaly: symbol=%s type=%s severity=%s score=%.2f message=%s",
            event.symbol, event.anomaly_type, event.severity, event.score, event.message,
        )

    def build_snapshot(
        self,
        user_id: int = 1,
        *,
        market: MarketCode = MarketCode.CN,
        group_id: int | None = None,
        limit: int = 50,
        include_news: bool = False,
    ) -> GenericResponseDTO:
        """Return watchlist agent output for one group plus all-group radar."""
        limit = max(1, min(int(limit or 50), 100))
        groups = self._safe_groups(user_id)
        symbols = self._symbols_for_group(user_id, group_id)
        active_group = self._active_group_meta(groups, group_id)

        items = self._score_symbols(
            symbols[:limit],
            market=market,
            include_news=include_news,
        )
        group_radar = self._build_group_radar(groups, user_id=user_id, market=market)
        summary = self._build_summary(items, active_group)
        
        # New: Exposure calculation
        exposure = self._calculate_exposure(items)

        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market": market.value,
            "active_group": active_group,
            "summary": summary,
            "items": items,
            "exposure": exposure,
            "group_radar": group_radar,
            "coverage": {
                "symbols": len(symbols),
                "scored": len(items),
                "include_news": include_news,
            },
        }

    def _calculate_exposure(self, items: list[dict[str, Any]]) -> GenericResponseDTO:
        """计算分组在行业和风格上的暴露."""
        if not items:
            return {"industries": {}, "sentiment_map": {}}
        
        industries = {}
        sentiments = {"bullish": 0, "bearish": 0, "neutral": 0}
        
        for it in items:
            # Industry count
            ind = it.get("industry") or "其他"
            industries[ind] = industries.get(ind, 0) + 1
            # Sentiment from health
            score = it["health_score"]
            if score >= 70: sentiments["bullish"] += 1
            elif score < 50: sentiments["bearish"] += 1
            else: sentiments["neutral"] += 1
            
        return {
            "industries": dict(sorted(industries.items(), key=lambda x: x[1], reverse=True)[:5]),
            "sentiments": sentiments,
            "top_industry": max(industries, key=industries.get) if industries else "N/A"
        }

    def _safe_groups(self, user_id: int = 1) -> list[dict[str, Any]]:
        try:
            raw = list(self._stock_group_service.list_groups(user_id=user_id) or [])
            return [group for group in raw if isinstance(group, dict)]
        except Exception as exc:  # noqa: BLE001
            logger.warning("watchlist agent groups unavailable: %s", exc)
            return []

    def _symbols_for_group(self, user_id: int = 1, group_id: int | None = None) -> list[str]:
        if group_id is not None:
            try:
                return [str(s).strip() for s in self._stock_group_service.list_group_symbols(group_id, user_id=user_id) if str(s).strip()]
            except Exception as exc:  # noqa: BLE001
                logger.warning("watchlist agent group symbols unavailable: %s", exc)
                return []
        try:
            return [str(s).strip() for s in self._watchlist_service.list_symbols(user_id=user_id) if str(s).strip()]
        except Exception as exc:  # noqa: BLE001
            logger.warning("watchlist agent watchlist symbols unavailable: %s", exc)
            return []

    def _active_group_meta(self, groups: list[dict[str, Any]], group_id: int | None) -> GenericResponseDTO:
        if group_id is None:
            return {"id": None, "name": "全部自选股", "description": "跨分组汇总"}
        for group in groups:
            if int(group.get("id") or 0) == int(group_id):
                return {
                    "id": group.get("id"),
                    "name": group.get("name") or f"分组 {group_id}",
                    "description": group.get("description") or "",
                }
        return {"id": group_id, "name": f"分组 {group_id}", "description": ""}

    def _score_symbols(
        self,
        symbols: list[str],
        *,
        market: MarketCode,
        include_news: bool,
    ) -> list[dict[str, Any]]:
        if not symbols:
            return []
        try:
            quotes = [_to_dict(q) for q in self._market_service.list_quotes(market, symbols)]
        except Exception as exc:  # noqa: BLE001
            logger.warning("watchlist agent quotes unavailable: %s", exc)
            quotes = []

        by_code: dict[str, dict[str, Any]] = {}
        for q in quotes:
            code = str(q.get("code") or "").strip()
            if not code:
                continue
            by_code[code] = q
            code6 = "".join(ch for ch in code if ch.isdigit())[-6:].zfill(6)
            if code6:
                by_code[code6] = q
        out = []
        for symbol in symbols:
            sym = str(symbol).strip()
            code6 = "".join(ch for ch in sym if ch.isdigit())[-6:].zfill(6)
            quote = (
                by_code.get(sym)
                or by_code.get(code6)
                or by_code.get(sym.lower())
                or {"code": sym, "name": sym}
            )
            news_meta = self._news_meta(symbol, market) if include_news else {"count": 0, "headlines": [], "risk": "not_loaded"}
            out.append(self._score_quote(quote, news_meta=news_meta))
        out.sort(key=lambda item: (item["priority"], item["health_score"]), reverse=True)
        return out

    def _news_meta(self, symbol: str, market: MarketCode) -> GenericResponseDTO:
        try:
            snapshot = self._stock_service.get_news_snapshot(symbol, market)
            news = []
            if hasattr(snapshot, "model_dump"):
                data = snapshot.model_dump()
            else:
                data = _to_dict(snapshot)
            for item in (data.get("news") or [])[:3]:
                title = str(item.get("title") or "").strip()
                if title:
                    news.append(title)
            return {
                "count": len(data.get("news") or []),
                "headlines": news,
                "risk": "has_news" if news else "quiet",
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("watchlist agent news unavailable for %s: %s", symbol, exc)
            return {"count": 0, "headlines": [], "risk": "unavailable"}

    def _score_quote(self, quote: dict[str, Any], *, news_meta: dict[str, Any]) -> GenericResponseDTO:
        change_pct = _safe_float(quote.get("change_pct"))
        volume_ratio = _safe_float(quote.get("volume_ratio"))
        amplitude = _safe_float(quote.get("amplitude"))
        turnover = _safe_float(quote.get("turnover"))
        amount = _safe_float(quote.get("amount"))

        dimensions = {
            "trend": self._trend_score(change_pct),
            "volume": self._volume_score(volume_ratio, amount),
            "news": self._news_score(news_meta),
            "fundamental": self._fundamental_score(quote),
            "risk": self._risk_score(change_pct, amplitude, turnover),
        }
        health = round(
            dimensions["trend"] * 0.28
            + dimensions["volume"] * 0.20
            + dimensions["news"] * 0.12
            + dimensions["fundamental"] * 0.15
            + dimensions["risk"] * 0.25,
            1,
        )
        reasons = self._build_reasons(
            change_pct=change_pct,
            volume_ratio=volume_ratio,
            amplitude=amplitude,
            turnover=turnover,
            amount=amount,
            news_meta=news_meta,
        )
        risk_notes = self._build_risk_notes(change_pct, amplitude, turnover, dimensions["risk"])
        action = self._action_label(health, risk_notes)
        priority = self._priority(health, change_pct, volume_ratio, risk_notes)
        code = str(quote.get("code") or "")

        return {
            "code": code,
            "name": quote.get("name") or code,
            "industry": quote.get("industry") or "",
            "price": _safe_float(quote.get("price")),
            "change_pct": change_pct,
            "volume_ratio": volume_ratio,
            "amplitude": amplitude,
            "turnover": turnover,
            "amount": amount,
            "health_score": health,
            "dimensions": dimensions,
            "action": action,
            "priority": priority,
            "reasons": reasons,
            "risk_notes": risk_notes,
            "news": news_meta,
            "links": {
                "detail": f"/stock/{code}",
                "ai_analysis": f"/ai-analysis?symbol={code}&market=CN",
                "committee": f"/ai-committee?symbol={code}&market=CN",
                "backtest": f"/backtest?symbol={code}",
            },
        }

    def _trend_score(self, change_pct: float) -> float:
        if change_pct >= 6:
            return 88
        if change_pct >= 2:
            return 75
        if change_pct > -2:
            return 58
        if change_pct > -5:
            return 42
        return 25

    def _volume_score(self, volume_ratio: float, amount: float) -> float:
        score = 55
        if volume_ratio >= 2.5:
            score += 25
        elif volume_ratio >= 1.5:
            score += 15
        elif volume_ratio and volume_ratio < 0.7:
            score -= 10
        if amount >= 1_000_000_000:
            score += 10
        elif amount and amount < 50_000_000:
            score -= 10
        return max(0, min(score, 100))

    def _news_score(self, news_meta: dict[str, Any]) -> float:
        risk = news_meta.get("risk")
        if risk == "has_news":
            return 68
        if risk == "quiet":
            return 55
        if risk == "unavailable":
            return 45
        return 50

    def _fundamental_score(self, quote: dict[str, Any]) -> float:
        pe = _safe_float(quote.get("pe"))
        pb = _safe_float(quote.get("pb"))
        score = 55
        if 0 < pe <= 35:
            score += 10
        elif pe > 80:
            score -= 12
        if 0 < pb <= 5:
            score += 5
        elif pb > 12:
            score -= 8
        if not pe and not pb:
            score -= 3
        return max(0, min(score, 100))

    def _risk_score(self, change_pct: float, amplitude: float, turnover: float) -> float:
        score = 72
        if change_pct <= -5:
            score -= 24
        elif change_pct <= -2:
            score -= 12
        if amplitude >= 8:
            score -= 18
        elif amplitude >= 5:
            score -= 8
        if turnover >= 12:
            score -= 14
        elif turnover >= 8:
            score -= 8
        return max(0, min(score, 100))

    def _build_reasons(
        self,
        *,
        change_pct: float,
        volume_ratio: float,
        amplitude: float,
        turnover: float,
        amount: float,
        news_meta: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
        if change_pct >= 5:
            reasons.append("涨幅超过 5%，短线资金关注度高")
        elif change_pct >= 2:
            reasons.append("涨幅超过 2%，走势偏强")
        elif change_pct <= -5:
            reasons.append("跌幅超过 5%，优先检查止损条件")
        elif change_pct <= -2:
            reasons.append("跌幅超过 2%，短线转弱")
        if volume_ratio >= 2:
            reasons.append("量比明显放大，可能有事件或资金驱动")
        if amount >= 1_000_000_000:
            reasons.append("成交额超过 10 亿，流动性较好")
        if amplitude >= 7:
            reasons.append("振幅偏大，盘中分歧加剧")
        if turnover >= 8:
            reasons.append("换手偏高，留意短线筹码松动")
        for title in news_meta.get("headlines") or []:
            reasons.append(f"相关新闻：{title}")
        return reasons[:6] or ["暂无显著异动，保持常规观察"]

    def _build_risk_notes(
        self,
        change_pct: float,
        amplitude: float,
        turnover: float,
        risk_score: float,
    ) -> list[str]:
        notes: list[str] = []
        if change_pct <= -5:
            notes.append("跌幅较大，需确认是否触发卖出计划")
        if amplitude >= 8:
            notes.append("振幅过高，不适合情绪化追单")
        if turnover >= 12:
            notes.append("换手过热，警惕短线冲高回落")
        if risk_score < 45:
            notes.append("综合风险偏高，建议降低仓位或等待确认")
        return notes[:4]

    def _action_label(self, health: float, risk_notes: list[str]) -> str:
        if risk_notes and health < 55:
            return "优先风控"
        if health >= 75:
            return "重点跟踪"
        if health >= 60:
            return "保持观察"
        if health >= 45:
            return "降低预期"
        return "复盘/止损"

    def _priority(self, health: float, change_pct: float, volume_ratio: float, risk_notes: list[str]) -> int:
        priority = 0
        if health >= 70:
            priority += 3
        if abs(change_pct) >= 5:
            priority += 2
        if volume_ratio >= 2:
            priority += 2
        if risk_notes:
            priority += 1
        return priority

    def _build_group_radar(self, groups: list[dict[str, Any]], *, user_id: int, market: MarketCode) -> list[dict[str, Any]]:
        radar = []
        for group in groups:
            gid = int(group.get("id") or 0)
            symbols = self._symbols_for_group(user_id=user_id, group_id=gid)
            if not symbols:
                radar.append(
                    {
                        "id": gid,
                        "name": group.get("name") or f"分组 {gid}",
                        "count": 0,
                        "avg_score": 0,
                        "strong_count": 0,
                        "risk_count": 0,
                        "stance": "空分组",
                    }
                )
                continue
            items = self._score_symbols(symbols[:30], market=market, include_news=False)
            avg = round(sum(i["health_score"] for i in items) / max(len(items), 1), 1)
            strong = len([i for i in items if i["health_score"] >= 70])
            risk = len([i for i in items if i["risk_notes"] or i["health_score"] < 45])
            if avg >= 70:
                stance = "强势"
            elif risk >= max(2, len(items) // 3):
                stance = "需风控"
            elif avg >= 55:
                stance = "中性"
            else:
                stance = "偏弱"
            radar.append(
                {
                    "id": gid,
                    "name": group.get("name") or f"分组 {gid}",
                    "count": len(symbols),
                    "avg_score": avg,
                    "strong_count": strong,
                    "risk_count": risk,
                    "stance": stance,
                }
            )
        return radar

    def _build_summary(self, items: list[dict[str, Any]], active_group: dict[str, Any]) -> GenericResponseDTO:
        if not items:
            return {
                "text": f"{active_group.get('name', '当前分组')} 暂无可评分股票。",
                "avg_score": 0,
                "strong_count": 0,
                "risk_count": 0,
                "top_action": "先添加自选股",
            }
        avg = round(sum(i["health_score"] for i in items) / max(len(items), 1), 1)
        strong = len([i for i in items if i["health_score"] >= 70])
        risk = len([i for i in items if i["risk_notes"] or i["health_score"] < 45])
        if risk:
            top_action = "先处理风险票"
        elif strong:
            top_action = "跟踪强势票"
        else:
            top_action = "保持观察"
        return {
            "text": f"{active_group.get('name', '当前分组')} 健康均分 {avg}，强势 {strong} 只，风险 {risk} 只。",
            "avg_score": avg,
            "strong_count": strong,
            "risk_count": risk,
            "top_action": top_action,
        }
