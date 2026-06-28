from __future__ import annotations

"""Jarvis 5.0 — proactive opportunity scan from watchlist + user knowledge."""

from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.shared.symbol_normalizer import SymbolNormalizer

logger = get_logger(__name__)

_ELASTICITY_FACTORS = frozenset(
    {"momentum", "高弹性", "涨停", "放量", "breakout", "volatility", "change_pct"}
)
_MIN_CHANGE_PCT = 3.0


class JarvisProactiveService:
    """Surface buy-ready panels when watchlist movers match user preference patterns."""

    def __init__(
        self,
        *,
        watchlist_service: Any | None = None,
        market_service: Any | None = None,
        user_knowledge_service: Any | None = None,
        trade_plan_service: Any | None = None,
    ) -> None:
        self._watchlist = watchlist_service
        self._market = market_service
        self._knowledge = user_knowledge_service
        self._trade_plan = trade_plan_service

    def scan(
        self,
        user_id: int | str,
        *,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Return proactive signals with prefilled Jarvis / trade-plan actions."""
        uid = int(user_id) if str(user_id).isdigit() else 0
        profile = (
            self._knowledge.get_profile(user_id)
            if self._knowledge is not None
            else {}
        )
        prefers_elastic = self._user_prefers_elasticity(profile)
        symbols = self._watchlist_symbols(uid)
        if not symbols:
            return {"ok": True, "signals": [], "prefers_elasticity": prefers_elastic}

        quotes = self._fetch_quotes(symbols[:30])
        signals: list[dict[str, Any]] = []
        for q in quotes:
            sym = str(q.get("symbol") or q.get("code") or "")
            change_pct = float(q.get("change_pct") or 0)
            if change_pct < _MIN_CHANGE_PCT:
                continue
            if prefers_elastic and change_pct < 5.0:
                continue
            clean = SymbolNormalizer.to_db_code(sym)
            name = str(q.get("name") or clean)
            plan_body = self._prefill_trade_plan(clean, MarketCode.CN)
            signals.append(
                {
                    "symbol": clean,
                    "name": name,
                    "change_pct": round(change_pct, 2),
                    "price": q.get("price"),
                    "match_reason": (
                        "自选股重大利好 + 高弹性偏好匹配"
                        if prefers_elastic
                        else "自选股强势异动"
                    ),
                    "confidence": min(0.95, 0.55 + change_pct / 20),
                    "jarvis_command": f"分析 {SymbolNormalizer.normalize_code(clean)} 并生成买入计划",
                    "command_plan": {
                        "method": "POST",
                        "href": "/api/v1/command/plan",
                        "body": {
                            "command": f"分析 {SymbolNormalizer.normalize_code(clean)} 买入计划",
                        },
                    },
                    "trade_plan_action": {
                        "method": "POST",
                        "href": "/api/v1/trade-plan/adopt",
                        "body": {
                            "symbol": clean,
                            "market": "CN",
                            "source": "jarvis_proactive",
                            "reason": f"Jarvis 主动信号 · 涨幅 {change_pct:.1f}%",
                        },
                    },
                    "preview_href": f"/stock/{clean}?m=CN#live-research-lab",
                    "suggested_trade_plan": plan_body,
                }
            )
            if len(signals) >= limit:
                break

        return {
            "ok": True,
            "prefers_elasticity": prefers_elastic,
            "scanned_symbols": len(symbols),
            "signals": signals,
        }

    def _user_prefers_elasticity(self, profile: dict[str, Any]) -> bool:
        factors = profile.get("factor_attention") or {}
        for key in factors:
            if key.lower() in _ELASTICITY_FACTORS or "弹性" in key:
                return True
        for evt in profile.get("interaction_events") or []:
            for f in evt.get("factors") or []:
                if f.lower() in _ELASTICITY_FACTORS or "弹性" in str(f):
                    return True
        for pat in profile.get("decision_patterns") or []:
            if pat.get("outcome") in ("gain", "win", "profit"):
                for f in pat.get("factors") or []:
                    if f.lower() in _ELASTICITY_FACTORS:
                        return True
        return False

    def _watchlist_symbols(self, user_id: int) -> list[str]:
        if self._watchlist is None or user_id <= 0:
            return []
        try:
            return list(self._watchlist.list_symbols(user_id) or [])
        except Exception as exc:
            logger.warning("jarvis proactive watchlist: %s", exc)
            return []

    def _fetch_quotes(self, symbols: list[str]) -> list[dict[str, Any]]:
        if self._market is None or not symbols:
            return []
        try:
            rows = self._market.list_quotes(MarketCode.CN, symbols)
            out: list[dict[str, Any]] = []
            for row in rows or []:
                if hasattr(row, "model_dump"):
                    out.append(row.model_dump())
                elif isinstance(row, dict):
                    out.append(row)
            return out
        except Exception as exc:
            logger.warning("jarvis proactive quotes: %s", exc)
            return []

    def _prefill_trade_plan(self, symbol: str, market: MarketCode) -> dict[str, Any] | None:
        if self._trade_plan is None:
            return None
        try:
            plan = self._trade_plan.build_plan(
                symbol=symbol,
                market=market,
                account_equity=100_000.0,
            )
            if hasattr(plan, "model_dump"):
                return plan.model_dump()
            if isinstance(plan, dict):
                return plan
        except Exception as exc:
            logger.debug("jarvis proactive trade plan: %s", exc)
        return None
