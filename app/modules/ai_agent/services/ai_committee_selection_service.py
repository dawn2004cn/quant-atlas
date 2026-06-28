from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""AI committee short-term stock selection service."""


import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.registry import register_service
from app.domain.dto.decision_context_dto import DecisionContextDTO, EvidenceNoteDTO
from app.domain.enums import MarketCode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommitteeAgent:
    id: str
    name: str
    role: str
    focus: str
    weight: float


@dataclass(frozen=True)
class StrategyWeapon:
    id: str
    name: str
    class_name: str
    regime_bucket: str
    description: str


class InMemoryAICommitteeSelectionRepository:
    def __init__(self) -> None:
        self._runs: list[dict[str, Any]] = []
        self._trades: list[dict[str, Any]] = []

    def save_run(self, payload: dict[str, Any]) -> None:
        self._runs.insert(0, payload.copy())

    def save_trades(self, run_id: str, user_id: int | None, trades: list[dict[str, Any]]) -> None:
        for idx, item in enumerate(trades, start=1):
            row = item.copy()
            row.setdefault("id", len(self._trades) + idx)
            row["run_id"] = run_id
            row["user_id"] = user_id
            row.setdefault("opened_at", datetime.now().isoformat())
            row.setdefault("updated_at", datetime.now().isoformat())
            self._trades.insert(0, row)

    def list_runs(self, user_id: int | None = None, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._runs if user_id is None else [r for r in self._runs if r.get("user_id") == user_id]
        return rows[:limit]

    def list_trades(self, user_id: int | None = None, only_open: bool = False, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._trades
        if user_id is not None:
            rows = [r for r in rows if r.get("user_id") == user_id]
        if only_open:
            rows = [r for r in rows if r.get("status") == "open"]
        return rows[:limit]

    def update_trade_tracking(self, trade_id: int, current_price: float, status: str, pnl_pct: float) -> None:
        for row in self._trades:
            if row.get("id") == trade_id:
                row["current_price"] = current_price
                row["status"] = status
                row["pnl_pct"] = pnl_pct
                row["updated_at"] = datetime.now().isoformat()
                break


@register_service(name="ai_committee_selection_service")
class AICommitteeSelectionService:
    INITIAL_CAPITAL = 500000.0

    def __init__(self, market_service: object = None, repository: object = None) -> None:
        self._market_service = market_service
        self._repository = repository or InMemoryAICommitteeSelectionRepository()

    def get_config(self) -> GenericResponseDTO:
        return {
            "agents": [agent.__dict__ for agent in self._agents()],
            "strategy_array": [weapon.__dict__ for weapon in self._weapons()],
            "capital": self.INITIAL_CAPITAL,
            "markets": self._index_universe(),
        }

    def get_status(self, user_id: int | None = None) -> GenericResponseDTO:
        trades = self._repository.list_trades(user_id=user_id, only_open=False, limit=80)
        runs = self._repository.list_runs(user_id=user_id, limit=10)
        open_trades = [t for t in trades if t.get("status") in {"open", "stop_loss_watch", "take_profit_watch"}]
        used = sum(float(t.get("capital_used") or 0) for t in open_trades)
        pnl = sum(float(t.get("capital_used") or 0) * float(t.get("pnl_pct") or 0) / 100 for t in open_trades)
        return {
            "capital": self.INITIAL_CAPITAL,
            "available_cash": max(0.0, self.INITIAL_CAPITAL - used),
            "position_count": len(open_trades),
            "open_trades": open_trades,
            "trade_history": trades,
            "runs": runs,
            "floating_pnl": round(pnl, 2),
        }

    def run_selection(
        self,
        *,
        user_id: int | None = None,
        capital: float | None = None,
        min_positions: int = 3,
        max_positions: int = 5,
    ) -> GenericResponseDTO:
        capital = float(capital or self.INITIAL_CAPITAL)
        min_positions = max(1, min_positions)
        max_positions = max(min_positions, max_positions)
        indexes = self._analyze_indexes()
        overall_regime = self._overall_regime(indexes)
        risk_level = self._risk_level(indexes, overall_regime)
        strategy_array = self._active_weapons(overall_regime)
        candidates = self._select_candidates(
            strategy_array=strategy_array,
            overall_regime=overall_regime,
            min_positions=min_positions,
            max_positions=max_positions,
        )
        trades = self._build_paper_trades(candidates, capital)
        run_id = f"aics-{uuid.uuid4().hex[:12]}"
        payload = {
            "id": run_id,
            "user_id": user_id,
            "status": "completed",
            "capital": capital,
            "overall_regime": overall_regime,
            "risk_level": risk_level,
            "indexes": indexes,
            "agents": [agent.__dict__ for agent in self._agents()],
            "strategy_array": [weapon.__dict__ for weapon in strategy_array],
            "selected_stocks": trades,
            "reasoning": self._build_reasoning(overall_regime, risk_level, strategy_array, trades),
            "created_at": datetime.now().isoformat(),
        }
        self._repository.save_run(payload)
        self._repository.save_trades(run_id, user_id, trades)
        decision = self._build_decision_context(payload)
        payload["decision_id"] = decision.decision_id
        payload["decision"] = decision.model_dump()
        try:
            from app.modules.system.services.ui.decision_trace_service import get_decision_trace_service

            get_decision_trace_service().record(decision)
        except Exception as exc:
            logger.warning("ai_committee_selection run_selection trace: %s", exc)
        return payload

    def track_positions(self, user_id: int | None = None) -> GenericResponseDTO:
        open_trades = self._repository.list_trades(user_id=user_id, only_open=True, limit=100)
        tracked = []
        for item in open_trades:
            price = self._latest_price(item.get("symbol") or "") or float(item.get("current_price") or item.get("entry_price") or 0)
            entry = float(item.get("entry_price") or 0)
            stop = float(item.get("stop_loss") or 0)
            take = float(item.get("take_profit") or 0)
            status = "open"
            if price and stop and price <= stop:
                status = "stop_loss_watch"
            elif price and take and price >= take:
                status = "take_profit_watch"
            pnl_pct = self._pnl_pct(entry, price)
            if hasattr(self._repository, "update_trade_tracking") and item.get("id") is not None:
                self._repository.update_trade_tracking(int(item["id"]), price, status, pnl_pct)
            tracked.append({**item, "current_price": price, "status": status, "pnl_pct": pnl_pct})
        return {"items": tracked, "count": len(tracked), "tracked_at": datetime.now().isoformat()}

    def _agents(self) -> list[CommitteeAgent]:
        return [
            CommitteeAgent("commander", "总指挥", "委员会主席", "汇总各 Agent 输出并给出最终仓位与行动", 0.18),
            CommitteeAgent("macro", "宏观 Agent", "宏观环境", "利率、政策、流动性与指数环境", 0.12),
            CommitteeAgent("industry", "行业 Agent", "行业景气", "赛道热度、产业趋势与板块扩散", 0.12),
            CommitteeAgent("finance", "财务 Agent", "财务质量", "盈利质量、估值、现金流与风险暴露", 0.12),
            CommitteeAgent("technical", "技术 Agent", "短线形态", "量价、突破、均线、缺口、形态确认", 0.14),
            CommitteeAgent("sentiment", "市场情绪 Agent", "资金与情绪", "成交热度、资金流向、题材情绪", 0.12),
            CommitteeAgent("risk", "风险 Agent", "风控门禁", "止损、波动、仓位、黑天鹅过滤", 0.12),
            CommitteeAgent("chen_xiaoqun", "陈小群短线选手", "短线狙击", "强势题材、情绪周期、快速止盈止损", 0.08),
        ]

    def _weapons(self) -> list[StrategyWeapon]:
        return [
            StrategyWeapon("VCP", "米勒维尼 VCP", "MinerviniVCPStrategy", "bull", "趋势收缩后的突破确认"),
            StrategyWeapon("ProGapMomentum", "缺口动量", "ProGapMomentumStrategy", "bull", "强势缺口与量能延续"),
            StrategyWeapon("Ichimoku", "一目均衡表", "IchimokuCloudStrategy", "bull", "云图趋势确认"),
            StrategyWeapon("ConnorsRSI2", "康纳斯 RSI(2)", "ConnorsRSI2Strategy", "bear", "极短期超跌反弹"),
            StrategyWeapon("VSAStoppingVolume", "VSA 恐慌停止量", "VSAStoppingVolumeStrategy", "bear", "恐慌放量衰竭"),
            StrategyWeapon("Sperandeo2B", "维克多 2B", "Sperandeo2BReversalStrategy", "bear", "假突破反转"),
            StrategyWeapon("TTM", "TTM 挤压", "TTMSqueezeBreakoutStrategy", "sideways", "波动收缩后的爆发"),
            StrategyWeapon("VWAP", "机构 VWAP 回踩", "VWAPPullbackStrategy", "sideways", "机构均价回踩确认"),
            StrategyWeapon("SuperTrend", "超级趋势", "SuperTrendStrategy", "sideways", "趋势跟踪与止损"),
            StrategyWeapon("BollingerRSI", "布林+RSI 极限反转", "BollingerRSIReversionStrategy", "sideways", "震荡极值反转"),
        ]

    def _active_weapons(self, regime: str) -> list[StrategyWeapon]:
        if regime == "bull":
            buckets = {"bull", "sideways"}
        elif regime == "bear":
            buckets = {"bear", "sideways"}
        else:
            buckets = {"sideways", "bull", "bear"}
        return [weapon for weapon in self._weapons() if weapon.regime_bucket in buckets]

    def _index_universe(self) -> list[dict[str, str]]:
        return [
            {"symbol": "sh000001", "name": "上证指数"},
            {"symbol": "sz399001", "name": "深证成指"},
            {"symbol": "sz399006", "name": "创业板指"},
            {"symbol": "sh000688", "name": "科创50"},
            {"symbol": "bj899050", "name": "北证50"},
        ]

    def _analyze_indexes(self) -> list[dict[str, Any]]:
        rows = []
        quotes = self._list_quotes([item["symbol"] for item in self._index_universe()])
        quote_by_code = {str(q.get("code") or q.get("symbol") or ""): q for q in quotes}
        for item in self._index_universe():
            quote = quote_by_code.get(item["symbol"]) or quote_by_code.get(item["symbol"][-6:]) or {}
            change = float(quote.get("change_pct") or quote.get("pct_chg") or 0)
            regime = "牛市" if change >= 0.8 else "熊市" if change <= -0.8 else "震荡市"
            rows.append({
                "symbol": item["symbol"],
                "name": item["name"],
                "change_pct": round(change, 2),
                "regime": regime,
                "regime_score": self._regime_score(change),
            })
        return rows

    def _overall_regime(self, indexes: list[dict[str, Any]]) -> str:
        avg_score = sum(float(i.get("regime_score") or 0) for i in indexes) / max(1, len(indexes))
        if avg_score >= 0.35:
            return "bull"
        if avg_score <= -0.35:
            return "bear"
        return "sideways"

    def _risk_level(self, indexes: list[dict[str, Any]], regime: str) -> str:
        dispersion = max(float(i["change_pct"]) for i in indexes) - min(float(i["change_pct"]) for i in indexes)
        if regime == "bear" or dispersion > 2.8:
            return "high"
        if regime == "bull" and dispersion < 1.5:
            return "low"
        return "medium"

    def _select_candidates(
        self,
        *,
        strategy_array: list[StrategyWeapon],
        overall_regime: str,
        min_positions: int,
        max_positions: int,
    ) -> list[dict[str, Any]]:
        quotes = self._list_quotes(None)
        if not quotes:
            return []
        scored = []
        for quote in quotes:
            symbol = str(quote.get("code") or quote.get("symbol") or "").strip()
            if not symbol or not symbol[-6:].isdigit():
                continue
            price = float(quote.get("price") or quote.get("last") or 0)
            if price <= 5:
                continue
            change = float(quote.get("change_pct") or quote.get("pct_chg") or 0)
            volume = float(quote.get("volume") or 0)
            amount = float(quote.get("amount") or 0)
            name = str(quote.get("name") or symbol)
            score = self._real_score(change, volume, amount, price, overall_regime)
            weapon = self._pick_weapon(strategy_array, score, change)
            scored.append({
                "symbol": symbol,
                "name": name,
                "price": round(price, 2),
                "change_pct": round(change, 2),
                "volume": volume,
                "amount": amount,
                "sniper_score": round(score, 1),
                "strategy_id": weapon.id,
                "strategy": weapon.name,
                "rationale": f"{weapon.name} 匹配，短线强度 {score:.1f}，涨跌幅 {change:.2f}%。",
            })
        scored.sort(key=lambda item: item["sniper_score"], reverse=True)
        count = min(max_positions, max(min_positions, len(scored[:max_positions])))
        return scored[:count]

    def _real_score(self, change_pct: float, volume: float, amount: float, price: float, regime: str) -> float:
        strength = min(35, max(0, change_pct * 4))
        vol_factor = min(15, volume / 5_000_000) if volume > 0 else 0
        amt_factor = min(10, amount / 100_000_000) if amount > 0 else 0
        price_factor = min(5, max(0, (price - 5) / 20))
        regime_bonus = {"bull": 10, "sideways": 5, "bear": 0}.get(regime, 3)
        safety = 25 if change_pct > 0 else (10 if change_pct > -2 else 0)
        return min(99.0, strength + vol_factor + amt_factor + price_factor + regime_bonus + safety)

    def _pick_weapon(self, weapons: list[StrategyWeapon], score: float, change: float) -> StrategyWeapon:
        if change > 5:
            idx = 0
        elif change > 2:
            idx = 1
        elif change > 0:
            idx = 2
        elif change > -2:
            idx = 3
        else:
            idx = 4
        return weapons[idx % len(weapons)]

    def _build_paper_trades(self, candidates: list[dict[str, Any]], capital: float) -> list[dict[str, Any]]:
        if not candidates:
            return []
        per_trade = capital / max(1, len(candidates))
        trades = []
        for item in candidates:
            price = float(item["price"])
            qty = int(per_trade // price) if price > 0 else 0
            used = qty * price
            trades.append({
                **item,
                "side": "BUY",
                "status": "open",
                "entry_price": price,
                "current_price": price,
                "quantity": qty,
                "capital_used": round(used, 2),
                "stop_loss": round(price * 0.935, 2),
                "take_profit": round(price * 1.12, 2),
                "pnl_pct": 0.0,
            })
        return trades

    def _list_quotes(self, symbols: list[str] | None) -> list[dict[str, Any]]:
        if self._market_service is None:
            return []
        try:
            quotes = self._market_service.list_quotes(MarketCode.CN, symbols)
            return list(quotes or [])
        except Exception:
            return []

    def _latest_price(self, symbol: str) -> float:
        quotes = self._list_quotes([symbol])
        if not quotes:
            return 0.0
        quote = quotes[0]
        return float(quote.get("price") or quote.get("last") or 0)

    def _regime_score(self, change_pct: float) -> float:
        return max(-1.0, min(1.0, change_pct / 2.5))

    def _pnl_pct(self, entry: float, current: float) -> float:
        if entry <= 0:
            return 0.0
        return round((current - entry) / entry * 100, 2)

    def _build_reasoning(
        self,
        regime: str,
        risk_level: str,
        strategies: list[StrategyWeapon],
        trades: list[dict[str, Any]],
    ) -> str:
        regime_label = {"bull": "牛市/偏多", "bear": "熊市/防守", "sideways": "震荡/均衡"}.get(regime, regime)
        names = "、".join(s.name for s in strategies[:4])
        symbols = "、".join(f"{t['symbol']} {t['name']}" for t in trades)
        return (
            f"Regime manager 判定当前市场为 {regime_label}，风险等级 {risk_level}。"
            f"策略武器库收敛为 {len(strategies)} 个可用策略，优先采用 {names}。"
            f"全 A 候选经短线强度、涨跌幅、流动性和风控门禁筛选后，生成模拟持仓：{symbols or '暂无'}。"
        )

    @staticmethod
    def _build_decision_context(payload: dict[str, Any]) -> DecisionContextDTO:
        reasoning = payload.get("reasoning")
        trace = [str(reasoning)] if reasoning else []
        evidence: list[EvidenceNoteDTO] = []
        for row in payload.get("indexes") or []:
            if isinstance(row, dict):
                evidence.append(
                    EvidenceNoteDTO(
                        source="index_regime",
                        title=str(row.get("name") or row.get("symbol") or ""),
                        confidence=row.get("regime_score"),
                        payload=row,
                    )
                )
        for weapon in payload.get("strategy_array") or []:
            if isinstance(weapon, dict):
                evidence.append(
                    EvidenceNoteDTO(
                        source="strategy_weapon",
                        title=str(weapon.get("name") or weapon.get("id") or ""),
                        payload=weapon,
                    )
                )
        for trade in (payload.get("selected_stocks") or [])[:8]:
            if isinstance(trade, dict):
                evidence.append(
                    EvidenceNoteDTO(
                        source="paper_trade",
                        title=str(trade.get("symbol") or ""),
                        confidence=trade.get("score"),
                        payload=trade,
                    )
                )
        return DecisionContextDTO(
            decision_id=f"decision_{uuid.uuid4().hex[:12]}",
            subject=f"committee:{payload.get('id') or 'selection'}",
            model_version="ai_committee_selection_v1",
            input_snapshot={
                "run_id": payload.get("id"),
                "capital": payload.get("capital"),
                "overall_regime": payload.get("overall_regime"),
                "risk_level": payload.get("risk_level"),
                "agent_count": len(payload.get("agents") or []),
            },
            reasoning_trace=trace,
            evidence=evidence,
        )
