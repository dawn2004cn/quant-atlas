from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Trade plan service with typed DTOs."""


from datetime import datetime, timedelta
from math import floor
from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode

logger = get_logger(__name__)


def _to_dict(value: object) -> GenericResponseDTO:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {}


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


class TradePlanService:
    """Build executable trade plans with risk and scenario cards."""

    def __init__(
        self,
        *,
        market_service: object,
        risk_service: Any | None = None,
    ) -> None:
        self._market_service = market_service
        self._risk_service = risk_service

    def build_plan(
        self,
        *,
        symbol: str,
        market: MarketCode = MarketCode.CN,
        account_equity: float = 100000.0,
        cash_available: float | None = None,
        risk_per_trade_pct: float = 1.0,
        max_position_pct: float = 15.0,
        entry_price: float | None = None,
        timeline: dict[str, Any] | None = None,
    ) -> GenericResponseDTO:
        """Build a single-symbol buy plan and risk card."""
        clean_symbol = str(symbol or "").strip().upper()
        if not clean_symbol:
            raise ValueError("symbol_required")
        account_equity = max(_safe_float(account_equity, 100000.0), 1.0)
        cash_available = account_equity if cash_available is None else max(_safe_float(cash_available), 0.0)
        risk_per_trade_pct = max(0.1, min(_safe_float(risk_per_trade_pct, 1.0), 5.0))
        max_position_pct = max(1.0, min(_safe_float(max_position_pct, 15.0), 50.0))

        quote = self._load_quote(clean_symbol, market)
        history = self._load_history(clean_symbol, market)
        last_price = entry_price or _safe_float(quote.get("price")) or self._last_close(history)

        if last_price <= 0:
            logger.debug("price_unavailable for %s", clean_symbol)
            return {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": clean_symbol,
                "market": market.value,
                "name": quote.get("name") or clean_symbol,
                "status": "price_unavailable",
                "error": "Unable to fetch price for this symbol",
                "soft_warnings": [],
            }

        technical = self._technical_context(history, last_price)
        plan_prices = self._plan_prices(last_price, technical)
        sizing = self._position_sizing(
            price=plan_prices["entry_price"],
            stop_loss=plan_prices["stop_loss"],
            account_equity=account_equity,
            cash_available=cash_available,
            risk_per_trade_pct=risk_per_trade_pct,
            max_position_pct=max_position_pct,
            market=market,
        )
        risk_check = self._risk_check(
            symbol=clean_symbol,
            market=market,
            price=plan_prices["entry_price"],
            shares=sizing["recommended_shares"],
            account_equity=account_equity,
            cash_available=cash_available,
        )
        soft_warnings = self._decision_guardrails(
            history=history,
            entry_price=plan_prices["entry_price"],
            stop_loss=plan_prices["stop_loss"],
            technical=technical,
        )

        worst_30d = self._worst_30d_drawdown(history, plan_prices["entry_price"])

        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": clean_symbol,
            "market": market.value,
            "name": quote.get("name") or clean_symbol,
            "status": "generated",
            "entry_price": plan_prices.get("entry_price", 0),
            "stop_loss": plan_prices.get("stop_loss", 0),
            "take_profit": plan_prices.get("take_profit_1", 0),
            "recommended_shares": sizing.get("recommended_shares", 0),
            "quote": quote,
            "plan": {
                **plan_prices,
                **sizing,
                "buy_reason": self._buy_reasons(quote, technical)
                + self._timeline_reasons(timeline),
                "failure_conditions": self._failure_conditions(plan_prices, technical),
                "execution_notes": self._execution_notes(sizing, risk_check),
            },
            "risk_cards": self._risk_cards(quote, technical, sizing),
            "technical_context": technical,
            "risk_check": risk_check,
            "soft_warnings": soft_warnings,
            "worst_case_30d": worst_30d,
            "scenario_analysis": self._scenario_analysis(
                price=plan_prices["entry_price"],
                shares=sizing["recommended_shares"],
                account_equity=account_equity,
                worst_case_price=worst_30d.get("worst_price"),
            ),
        }

    def _load_quote(self, symbol: str, market: MarketCode) -> GenericResponseDTO:
        try:
            quotes = self._market_service.list_quotes(market, [symbol])
            if quotes:
                return _to_dict(quotes[0])
        except Exception as exc:
            logger.warning("trade plan quote unavailable for %s: %s", symbol, exc)
        return {"code": symbol, "name": symbol}

    def _decision_guardrails(
        self,
        *,
        history: list[dict[str, Any]],
        entry_price: float,
        stop_loss: float,
        technical: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Soft warnings at plan-build time (decision co-pilot, not hard block)."""
        from app.modules.market_data.services.watchlist_risk_service import (
            SupportResistanceCalculator,
        )

        warnings: list[dict[str, Any]] = []
        if entry_price <= 0 or stop_loss <= 0:
            return warnings

        levels = SupportResistanceCalculator.calculate_levels(history, entry_price)
        supports = sorted(
            [float(s) for s in (levels.get("support") or []) if float(s) > 0],
            reverse=True,
        )
        nearest_support = supports[0] if supports else _safe_float(technical.get("recent_low"))

        if nearest_support > 0 and stop_loss < nearest_support * 0.995:
            suggested = round(nearest_support * 1.01, 2)
            warnings.append(
                {
                    "code": "stop_below_support",
                    "level": "warning",
                    "message": (
                        f"止损 {stop_loss:.2f} 位于近期强支撑 {nearest_support:.2f} 下方"
                        f"建议上移至支撑位之上约 {suggested:.2f}"
                    ),
                    "suggested_stop_loss": suggested,
                    "nearest_support": nearest_support,
                }
            )

        risk_per_share = entry_price - stop_loss
        if risk_per_share > entry_price * 0.12:
            warnings.append(
                {
                    "code": "stop_too_wide",
                    "level": "info",
                    "message": (
                        f"止损距离约 {risk_per_share / entry_price * 100:.1f}%"
                        "偏大；可结合波动率或支撑位收缩"
                    ),
                }
            )

        recent_low = _safe_float(technical.get("recent_low"))
        if recent_low > 0 and entry_price < recent_low * 0.99:
            warnings.append(
                {
                    "code": "entry_below_recent_low",
                    "level": "warning",
                    "message": (
                        f"入场价 {entry_price:.2f} 低于 20 日低点 {recent_low:.2f}"
                        "需确认是否为有效突破而非接飞刀"
                    ),
                }
            )

        return warnings

    def _load_history(self, symbol: str, market: MarketCode) -> list[dict[str, Any]]:
        try:
            end = datetime.now()
            start = end - timedelta(days=280)
            history_data = self._market_service.get_history(
                symbol,
                market,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
            )
            items = history_data.history if hasattr(history_data, 'history') else history_data
            return [h.__dict__ if hasattr(h, '__dict__') else h for h in (items or [])]
        except Exception as exc:
            logger.warning("trade plan history unavailable for %s: %s", symbol, exc)
            return []


    def _last_close(self, history: list[dict[str, Any]]) -> float:
        for row in reversed(history):
            close = _safe_float(row.get("close") or row.get("Close"))
            if close > 0:
                return close
        return 0.0

    def _technical_context(self, history: list[dict[str, Any]], price: float) -> GenericResponseDTO:
        closes = [_safe_float(r.get("close") or r.get("Close")) for r in history]
        highs = [_safe_float(r.get("high") or r.get("High")) for r in history]
        lows = [_safe_float(r.get("low") or r.get("Low")) for r in history]
        closes = [v for v in closes if v > 0]
        highs = [v for v in highs if v > 0]
        lows = [v for v in lows if v > 0]
        recent_closes = closes[-20:]
        recent_high = max(highs[-20:] or [price])
        recent_low = min(lows[-20:] or [price])
        ma20 = sum(recent_closes) / len(recent_closes) if recent_closes else price
        volatility = self._realized_volatility(closes[-30:])
        trend = "强于 20 日均" if price >= ma20 else "弱于 20 日均"
        return {
            "ma20": round(ma20, 2),
            "recent_high": round(recent_high, 2),
            "recent_low": round(recent_low, 2),
            "realized_volatility": round(volatility, 4),
            "trend_label": trend,
            "history_points": len(history),
        }

    def _realized_volatility(self, closes: list[float]) -> float:
        if len(closes) < 3:
            return 0.03
        returns = []
        for prev, cur in zip(closes, closes[1:]):
            if prev > 0:
                returns.append((cur - prev) / prev)
        if not returns:
            return 0.03
        avg = sum(returns) / len(returns)
        variance = sum((r - avg) ** 2 for r in returns) / max(len(returns) - 1, 1)
        return max(0.015, min(variance ** 0.5, 0.12))

    def _plan_prices(self, price: float, technical: dict[str, Any]) -> GenericResponseDTO[str, float]:
        volatility = _safe_float(technical.get("realized_volatility"), 0.03)
        stop_pct = max(0.05, min(volatility * 2.2, 0.12))
        recent_low = _safe_float(technical.get("recent_low"))
        raw_stop = price * (1 - stop_pct)
        stop_loss = min(raw_stop, recent_low * 0.985) if recent_low > 0 and recent_low < price else raw_stop
        stop_loss = max(stop_loss, price * 0.84)
        risk_per_share = max(price - stop_loss, price * 0.03)
        target_price = price + risk_per_share * 2
        take_profit_1 = price + risk_per_share * 1.2
        return {
            "entry_price": round(price, 2),
            "stop_loss": round(stop_loss, 2),
            "take_profit_1": round(take_profit_1, 2),
            "target_price": round(target_price, 2),
            "risk_reward_ratio": round((target_price - price) / risk_per_share, 2),
        }

    def _position_sizing(
        self,
        *,
        price: float,
        stop_loss: float,
        account_equity: float,
        cash_available: float,
        risk_per_trade_pct: float,
        max_position_pct: float,
        market: MarketCode,
    ) -> GenericResponseDTO:
        risk_budget = account_equity * risk_per_trade_pct / 100
        risk_per_share = max(price - stop_loss, price * 0.01)
        risk_based_shares = int(risk_budget / risk_per_share)
        cap_value = min(account_equity * max_position_pct / 100, cash_available)
        cap_shares = int(cap_value / price)
        raw_shares = max(0, min(risk_based_shares, cap_shares))
        lot_size = 100 if market == MarketCode.CN else 1
        shares = int(floor(raw_shares / lot_size) * lot_size)
        position_value = shares * price
        max_loss = shares * risk_per_share
        return {
            "account_equity": round(account_equity, 2),
            "cash_available": round(cash_available, 2),
            "risk_per_trade_pct": risk_per_trade_pct,
            "max_position_pct": max_position_pct,
            "risk_budget": round(risk_budget, 2),
            "risk_per_share": round(risk_per_share, 2),
            "recommended_shares": shares,
            "position_value": round(position_value, 2),
            "position_weight_pct": round(position_value / account_equity * 100, 2),
            "max_loss_amount": round(max_loss, 2),
            "max_loss_pct": round(max_loss / account_equity * 100, 2),
            "lot_size": lot_size,
        }

    def _risk_check(
        self,
        *,
        symbol: str,
        market: MarketCode,
        price: float,
        shares: int,
        account_equity: float,
        cash_available: float,
    ) -> GenericResponseDTO:
        if self._risk_service is None or shares <= 0:
            return {"allowed": shares > 0, "reason": "shares_not_positive" if shares <= 0 else "risk_service_unavailable"}
        try:
            result = self._risk_service.check_order(
                symbol=symbol,
                side="buy",
                quantity=shares,
                price=price,
                account_id="plan",
                total_equity=account_equity,
                cash_available=cash_available,
                current_positions={},
                daily_pnl=0.0,
                market=market.value,
            )
            return {
                "allowed": result.allowed,
                "reason": result.reason,
                "blocked_rules": result.blocked_rules,
                "details": result.details,
            }
        except Exception as exc:
            logger.warning("trade plan risk check failed for %s: %s", symbol, exc)
            return {"allowed": True, "reason": f"risk_check_unavailable: {exc}"}

    def _timeline_reasons(self, timeline: dict[str, Any] | None) -> list[str]:
        if not timeline:
            return []
        markers = timeline.get("markers") or []
        reasons: list[str] = []
        seen = set()
        for m in markers[-10:]:
            mtype = str(m.get("type") or "")
            title = str(m.get("title") or "")[:80]
            if not title:
                continue
            if mtype == "price_move":
                pct = (m.get("payload") or {}).get("change_pct", 0)
                reasons.append(f"{title[:10]}期间触发{abs(pct):.0f}%以上波动（{m.get('date','')}）")
            elif mtype == "volume_spike":
                reasons.append(f"{title[:10]}期间出现巨量成交（{m.get('date','')}）")
            elif mtype == "news":
                reasons.append(f"近期舆情：{title[:40]}")
            elif mtype == "research_report":
                org = (m.get("payload") or {}).get("org_name", "")
                tag = f"（{org[:16]}）" if org else ""
                reasons.append(f"机构研报覆盖{tag}")
            elif mtype == "large_order":
                reasons.append(f"龙虎榜异动（{m.get('date','')}）")
            seen.add(mtype)
        reasons = reasons[:4]
        return reasons

    def _buy_reasons(self, quote: dict[str, Any], technical: dict[str, Any]) -> list[str]:
        reasons = [str(technical.get("trend_label") or "技术状态待确认")]
        change_pct = _safe_float(quote.get("change_pct"))
        volume_ratio = _safe_float(quote.get("volume_ratio"))
        if change_pct >= 2:
            reasons.append("当日涨幅偏强，短线资金关注度提升")
        elif change_pct <= -2:
            reasons.append("当日走弱，仅适合等待企稳后执行")
        if volume_ratio >= 1.8:
            reasons.append("量比放大，适合结合消息或板块确认")
        reasons.append("计划采用固定亏损预算，先定义失效条件再入场")
        return reasons[:4]

    def _failure_conditions(self, plan: dict[str, float], technical: dict[str, Any]) -> list[str]:
        return [
            f"收盘跌破止损 {plan['stop_loss']:.2f}，计划失效",
            f"跌破 20 日低点 {technical.get('recent_low', 0):.2f} 且无法收回，降低仓位或退出",
            "买入后两日内量能无法延续，且价格回到入场价下方，暂停加仓",
            "出现重大利空或市场系统性下跌时，优先执行风控而非补仓",
        ]

    def _execution_notes(self, sizing: dict[str, Any], risk_check: dict[str, Any]) -> list[str]:
        notes = []
        if sizing["recommended_shares"] <= 0:
            notes.append("按当前风险预算无法生成一手买入数量，需提高资金规模或降低价格或缩小风险距离")
        else:
            notes.append(f"建议首笔 {sizing['recommended_shares']} 股，仓位约 {sizing['position_weight_pct']}%")
        notes.append(f"单笔最大计划亏损约 {sizing['max_loss_amount']} 元，占账户 {sizing['max_loss_pct']}%")
        if not risk_check.get("allowed", True):
            reason = risk_check.get("reason", "")
            display = {"shares_not_positive": "买入数量不足1手", "risk_service_unavailable": "风控服务不可用"}.get(reason, reason)
            notes.append(f"风控预检未通过：{display}")
        return notes

    def _risk_cards(
        self,
        quote: dict[str, Any],
        technical: dict[str, Any],
        sizing: dict[str, Any],
    ) -> list[dict[str, Any]]:
        cards = [
            {
                "title": "亏损预算",
                "level": "high" if sizing["max_loss_pct"] > 1.5 else "medium",
                "content": f"本计划最大亏损 {sizing['max_loss_amount']} 元，占账户 {sizing['max_loss_pct']}%",
            },
            {
                "title": "技术失效",
                "level": "medium",
                "content": f"若跌破止损或 20 日低点 {technical.get('recent_low')}，说明买入逻辑失效",
            },
            {
                "title": "波动风险",
                "level": "high" if _safe_float(quote.get("amplitude")) >= 8 else "low",
                "content": f"当日振幅 {round(_safe_float(quote.get('amplitude')), 2)}%，高振幅时不追单入场",
            },
        ]
        return cards

    def _worst_30d_drawdown(
        self,
        history: list[dict[str, Any]],
        current_price: float,
    ) -> dict[str, Any]:
        closes = [
            float(r.get("close") or r.get("Close") or 0)
            for r in history
            if float(r.get("close") or r.get("Close") or 0) > 0
        ]
        if len(closes) < 35:
            return {
                "worst_drawdown_pct": 0.0,
                "worst_price": current_price * 0.7,
                "lookback_days_available": len(closes),
                "note": "历史数据不足 35 个交易日，无法计算 30 日最大回撤",
            }
        worst_dd = 0.0
        worst_end_idx = len(closes) - 1
        for i in range(len(closes) - 30):
            start_price = closes[i]
            end_price = closes[i + 30]
            actual_dd = (end_price - start_price) / start_price
            if actual_dd < worst_dd:
                worst_dd = actual_dd
                worst_end_idx = i + 30
        worst_price = round(current_price * (1 + worst_dd), 2)
        return {
            "worst_drawdown_pct": round(worst_dd * 100, 2),
            "worst_price": max(worst_price, 0.01),
            "occurred_at": worst_end_idx,
            "lookback_days_available": len(closes),
            "note": "如历史重演，30 日后价格可能触及此水平",
        }

    def _scenario_analysis(self, *, price: float, shares: int, account_equity: float, worst_case_price: float | None = None) -> list[dict[str, Any]]:
        scenarios = [
            ("大盘跌 2%，个股跌 5%", -0.05),
            ("个股回踩止损", -0.08),
            ("个股上涨 5%", 0.05),
            ("个股到达第一止盈", 0.10),
        ]
        out = []
        for name, pct in scenarios:
            pnl = price * shares * pct
            out.append(
                {
                    "name": name,
                    "price": round(price * (1 + pct), 2),
                    "pnl": round(pnl, 2),
                    "account_impact_pct": round(pnl / account_equity * 100, 2) if account_equity > 0 else 0,
                }
            )
        if worst_case_price is not None and worst_case_price > 0:
            worst_pnl = (worst_case_price - price) * shares
            out.append(
                {
                    "name": "历史最深 30 日回撤重现",
                    "price": worst_case_price,
                    "pnl": round(worst_pnl, 2),
                    "account_impact_pct": round(worst_pnl / account_equity * 100, 2) if account_equity > 0 else 0,
                    "is_worst_case": True,
                }
            )
        return out
