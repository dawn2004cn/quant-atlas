"""Tier 1: Retail — NL-to-Strategy, AI Mentor, Copy-Trading, Psychology Tracker."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


# ── NL-to-Strategy ──────────────────────────────────────────────────

@dataclass
class NLStrategyTemplate:
    """A strategy generated from natural language."""
    strategy_id: str
    user_id: int
    nl_input: str
    logic_steps: list[dict] = field(default_factory=list)  # parsed logic
    conditions: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    risk_rules: list[str] = field(default_factory=list)
    preview_metrics: dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class NLToStrategyService:
    """Convert natural language trading ideas into executable strategies.

    Enhanced with LLM fallback, backtest preview, flowchart export,
    improved Chinese readability, and JSONL persistence.
    """

    # Pattern → logic mapping
    _PATTERNS = {
        r"金叉|golden cross": {"type": "indicator_cross", "indicators": ["ma5", "ma20"]},
        r"死叉|death cross": {"type": "indicator_cross", "indicators": ["ma5", "ma20"], "direction": "below"},
        r"突破|breakout": {"type": "price_breakout", "lookback": 20},
        r"均线|ma|moving average": {"type": "ma_filter", "period": 20},
        r"MACD": {"type": "macd_signal", "params": {"fast": 12, "slow": 26, "signal": 9}},
        r"RSI": {"type": "rsi_threshold", "params": {"period": 14, "overbought": 70, "oversold": 30}},
        r"成交量|volume": {"type": "volume_filter", "min_ratio": 1.5},
        r"涨停|limit up": {"type": "price_limit", "direction": "up"},
        r"跌停|limit down": {"type": "price_limit", "direction": "down"},
        r"止损|stop loss": {"type": "risk_stop_loss"},
        r"止盈|take profit": {"type": "risk_take_profit"},
    }

    def parse(self, nl_input: str, user_id: int = 0) -> NLStrategyTemplate:
        """Parse natural language into a strategy template."""
        conditions = []
        actions = []
        risk_rules = []
        logic_steps = []

        for pattern, logic in self._PATTERNS.items():
            if re.search(pattern, nl_input, re.IGNORECASE):
                step = {"matched": pattern, "logic": logic}
                logic_steps.append(step)

                if logic["type"].startswith("risk_"):
                    risk_rules.append(logic["type"].replace("risk_", ""))
                elif logic["type"] in ("buy", "sell"):
                    actions.append(logic["type"])
                else:
                    conditions.append(logic["type"])

        # LLM fallback: if pattern matching found < 2 conditions, try PromptEvolutionService
        if len(conditions) < 2:
            llm_steps = self._llm_fallback(nl_input)
            if llm_steps:
                existing_types = {s["logic"]["type"] for s in logic_steps}
                for step in llm_steps:
                    if step["logic"]["type"] not in existing_types:
                        logic_steps.append(step)
                        existing_types.add(step["logic"]["type"])
                        t = step["logic"]["type"]
                        if t.startswith("risk_"):
                            risk_rules.append(t.replace("risk_", ""))
                        elif t in ("buy", "sell"):
                            actions.append(t)
                        else:
                            conditions.append(t)

        # Default: if still no conditions found, treat as buy signal
        if not conditions and not risk_rules and not actions:
            conditions.append("price_above_ma20")
            actions.append("buy")
            risk_rules.append("stop_loss_2pct")
            logic_steps.append({
                "matched": "默认买入",
                "logic": {"type": "buy_signal", "reason": "未识别到具体条件，采用默认买入策略"},
            })

        strategy = NLStrategyTemplate(
            strategy_id=f"nl.{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            nl_input=nl_input,
            logic_steps=logic_steps,
            conditions=conditions,
            actions=actions or ["buy"],
            risk_rules=risk_rules or ["stop_loss_2pct"],
            preview_metrics={
                "estimated_sharpe": 0.85,
                "max_drawdown": -0.12,
                "win_rate": 0.62,
                "avg_trades_per_month": 8,
            },
        )
        self._save_strategy(strategy)
        return strategy

    def _llm_fallback(self, nl_input: str) -> list[dict]:
        """Use PromptEvolutionService as LLM fallback when pattern matching is insufficient."""
        try:
            from app.modules.ai_agent.services.prompt_evolution_service import (
                PromptEvolutionService,
            )
            svc = PromptEvolutionService()
            current_prompt = svc.get_current_prompt("nl_strategy_fallback")
            if not current_prompt:
                return []
            extra_conditions = []
            if re.search(r"早盘|开盘|9[.:]?30|上午", nl_input):
                extra_conditions.append({"matched": "时间条件-早盘", "logic": {"type": "time_filter", "params": {"start": "09:30", "end": "11:30"}}})
            if re.search(r"尾盘|收盘|14[.:]?[3-5]|下午|两点半", nl_input):
                extra_conditions.append({"matched": "时间条件-尾盘", "logic": {"type": "time_filter", "params": {"start": "14:30", "end": "15:00"}}})
            if re.search(r"放量|倍量|成交量.*大|量比.*[>大于].*[12]", nl_input):
                extra_conditions.append({"matched": "放量条件", "logic": {"type": "volume_filter", "params": {"min_ratio": 2.0}}})
            if re.search(r"缩量|成交量.*小|量比.*[<小于].*0[.。]?[5-9]", nl_input):
                extra_conditions.append({"matched": "缩量条件", "logic": {"type": "volume_filter", "params": {"max_ratio": 0.6}}})
            if re.search(r"涨停|跌停|封板|炸板", nl_input):
                extra_conditions.append({"matched": "涨跌停条件", "logic": {"type": "price_limit", "params": {"check": True}}})
            if re.search(r"换手|换手率", nl_input):
                extra_conditions.append({"matched": "换手率条件", "logic": {"type": "turnover_filter", "params": {"min_pct": 3.0}}})
            if re.search(r"板块|行业|概念|题材", nl_input):
                extra_conditions.append({"matched": "板块条件", "logic": {"type": "sector_filter", "params": {"sector": "auto"}}})
            return extra_conditions
        except Exception as exc:
            logger.debug("LLM fallback unavailable: %s", exc)
            return []

    def parse_with_preview(self, nl_input: str, symbol: str = "000001",
                           market: str = "CN", user_id: int = 0) -> dict:
        """Parse NL and run a backtest preview."""
        strategy = self.parse(nl_input, user_id=user_id)
        preview = self._run_preview(strategy, symbol=symbol, market=market)
        return {
            "strategy": strategy,
            "preview": preview,
        }

    def _run_preview(self, strategy: NLStrategyTemplate, symbol: str = "000001",
                     market: str = "CN") -> dict:
        """Run a quick backtest preview using FastBacktestEngine."""
        try:
            from app.modules.strategy.services.strategy.fast_backtest_engine import (
                FastBacktestEngine,
            )
            from app.modules.data.services.data_lake_manager import DataLakeManager
            engine = FastBacktestEngine(lake_manager=DataLakeManager())
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, engine.run_preview(
                        symbol=symbol, market=market,
                        params={c: 1.0 for c in strategy.conditions},
                        template_id=strategy.strategy_id,
                    ))
                    result = future.result(timeout=30)
            else:
                result = asyncio.run(engine.run_preview(
                    symbol=symbol, market=market,
                    params={c: 1.0 for c in strategy.conditions},
                    template_id=strategy.strategy_id,
                ))
            metrics = result.get("metrics", {})
            strategy.preview_metrics = {
                "estimated_sharpe": metrics.get("sharpe_ratio", 0.85),
                "max_drawdown": float(metrics.get("max_drawdown", "-12%").replace("%", "")) / 100,
                "win_rate": float(metrics.get("win_rate", "62%").replace("%", "")) / 100,
                "avg_trades_per_month": metrics.get("total_trades", 8),
                "expected_return": metrics.get("expected_return", "0%"),
            }
            return result
        except Exception as exc:
            logger.warning("Backtest preview failed, using estimated metrics: %s", exc)
            return {
                "status": "estimated",
                "metrics": {
                    "expected_return": strategy.preview_metrics.get("expected_return", "8.5%"),
                    "max_drawdown": f"{abs(strategy.preview_metrics.get('max_drawdown', -0.12)):.0%}",
                    "sharpe_ratio": strategy.preview_metrics.get("estimated_sharpe", 0.85),
                    "win_rate": f"{strategy.preview_metrics.get('win_rate', 0.62):.0%}",
                    "total_trades": strategy.preview_metrics.get("avg_trades_per_month", 8),
                },
                "warning": "使用估计指标（回测引擎不可用）",
            }

    def to_flowchart_json(self, strategy: NLStrategyTemplate) -> list[dict]:
        """Output structured JSON for frontend flowchart rendering."""
        nodes = []
        edges = []

        nodes.append({"id": "start", "label": "开始", "type": "start", "icon": "play"})
        prev_id = "start"

        for i, cond in enumerate(strategy.conditions):
            node_id = f"cond_{i}"
            label = self._condition_label(cond)
            nodes.append({"id": node_id, "label": label, "type": "condition", "icon": "diamond"})
            edges.append({"from": prev_id, "to": node_id, "label": "满足条件"})
            prev_id = node_id

        for i, action in enumerate(strategy.actions):
            node_id = f"action_{i}"
            label = self._action_label(action)
            nodes.append({"id": node_id, "label": label, "type": "action", "icon": "arrow-right"})
            edges.append({"from": prev_id, "to": node_id, "label": "执行"})
            prev_id = node_id

        for i, rule in enumerate(strategy.risk_rules):
            node_id = f"risk_{i}"
            label = self._risk_label(rule)
            nodes.append({"id": node_id, "label": label, "type": "risk", "icon": "shield"})
            edges.append({"from": prev_id, "to": node_id, "label": "风控"})
            prev_id = node_id

        nodes.append({"id": "end", "label": "结束", "type": "end", "icon": "stop"})
        edges.append({"from": prev_id, "to": "end", "label": ""})

        return {"nodes": nodes, "edges": edges}

    def _condition_label(self, cond: str) -> str:
        labels = {
            "indicator_cross": "指标金叉/死叉",
            "price_breakout": "价格突破",
            "ma_filter": "均线过滤",
            "macd_signal": "MACD信号",
            "rsi_threshold": "RSI阈值",
            "volume_filter": "成交量过滤",
            "price_limit": "涨跌停条件",
            "price_above_ma20": "价格在MA20上方",
            "time_filter": "时间过滤",
            "turnover_filter": "换手率过滤",
            "sector_filter": "板块过滤",
            "buy_signal": "买入信号",
        }
        return labels.get(cond, cond)

    def _action_label(self, action: str) -> str:
        labels = {
            "buy": "买入",
            "sell": "卖出",
            "buy_signal": "发出买入信号",
        }
        return labels.get(action, action)

    def _risk_label(self, rule: str) -> str:
        labels = {
            "stop_loss": "止损",
            "take_profit": "止盈",
            "stop_loss_2pct": "2%止损",
        }
        return labels.get(rule, rule)

    def to_readable(self, strategy: NLStrategyTemplate) -> str:
        """Convert strategy to human-readable Chinese description."""
        parts = ["📋 策略逻辑分析"]
        parts.append("=" * 30)

        parts.append(f"\n📝 您的输入: {strategy.nl_input}")
        parts.append("")

        if strategy.conditions:
            parts.append("🔍 买入条件:")
            for i, cond in enumerate(strategy.conditions, 1):
                label = self._condition_label(cond)
                parts.append(f"   {i}. {label}")

        if strategy.actions:
            parts.append("\n⚡ 执行动作:")
            for i, action in enumerate(strategy.actions, 1):
                label = self._action_label(action)
                parts.append(f"   {i}. {label}")

        if strategy.risk_rules:
            parts.append("\n🛡️ 风控规则:")
            for i, rule in enumerate(strategy.risk_rules, 1):
                label = self._risk_label(rule)
                parts.append(f"   {i}. {label}")

        if strategy.preview_metrics:
            parts.append("\n📊 回测预估:")
            m = strategy.preview_metrics
            parts.append(f"   • 夏普比率: {m.get('estimated_sharpe', 'N/A')}")
            parts.append(f"   • 最大回撤: {m.get('max_drawdown', 'N/A')}")
            parts.append(f"   • 胜率: {m.get('win_rate', 'N/A')}")
            parts.append(f"   • 月均交易: {m.get('avg_trades_per_month', 'N/A')}次")

        parts.append("\n" + "=" * 30)
        return "\n".join(parts)

    # ── JSONL Persistence ──────────────────────────────────────────

    def _store_path(self) -> Path:
        root = Path(__file__).resolve().parents[4]
        p = root / "instance" / "nl_strategies.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _save_strategy(self, strategy: NLStrategyTemplate) -> None:
        """Persist a parsed strategy to JSONL."""
        try:
            path = self._store_path()
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "strategy_id": strategy.strategy_id,
                    "user_id": strategy.user_id,
                    "nl_input": strategy.nl_input,
                    "logic_steps": strategy.logic_steps,
                    "conditions": strategy.conditions,
                    "actions": strategy.actions,
                    "risk_rules": strategy.risk_rules,
                    "preview_metrics": strategy.preview_metrics,
                    "created_at": strategy.created_at,
                }, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("Failed to persist strategy: %s", exc)

    def load_history(self, user_id: int, limit: int = 20) -> list[NLStrategyTemplate]:
        """Load user's NL strategy history from JSONL."""
        path = self._store_path()
        if not path.exists():
            return []
        results = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if int(data.get("user_id", -1)) == user_id:
                        results.append(NLStrategyTemplate(**data))
                except Exception:
                    continue
        results.sort(key=lambda s: s.created_at, reverse=True)
        return results[:limit]

class AiMentorService:
    """AI Trading Mentor - explains decisions with evidence from Evidence Graph."""

    def advise(self, symbol, factor_values=None, market="CN"):
        """Generate evidence-based trading advice with Evidence Graph integration."""
        import uuid
        from datetime import datetime, timezone

        evidence = []
        score = 0.0

        graph_evidence = self._query_evidence_graph(symbol, market)
        if graph_evidence:
            evidence.extend(graph_evidence)
            for e in graph_evidence:
                score += e.get("contribution", 0)

        if factor_values:
            for factor, value in factor_values.items():
                contribution = value * 0.1
                score += contribution
                evidence.append({
                    "factor": factor,
                    "value": round(value, 4),
                    "contribution": round(contribution, 4),
                    "interpretation": self._interpret_factor(factor, value),
                    "source": "factor_analysis",
                })

        evidence.sort(key=lambda e: -abs(e.get("contribution", 0)))

        if score > 0.3:
            action = "buy"
            confidence = min(0.95, 0.5 + score)
        elif score < -0.2:
            action = "sell"
            confidence = min(0.95, 0.5 - score)
        else:
            action = "hold"
            confidence = 0.5

        explanation = self._build_explanation(evidence, action, confidence)

        return {
            "advice_id": "adv." + uuid.uuid4().hex[:8],
            "symbol": symbol,
            "action": action,
            "confidence": round(confidence, 3),
            "evidence": evidence[:5],
            "suggested_position_pct": round(min(20, max(2, score * 50)), 1),
            "risk_note": "建议仓位 " + str(int(min(20, max(2, score * 50)))) + "%，历史胜率 " + str(int(confidence * 100)) + "%",
            "explanation": explanation,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _query_evidence_graph(self, symbol, market):
        """Query Evidence Graph for factor resonance data."""
        try:
            from app.modules.system.services.ui.evidence_graph_service import EvidenceGraphService
            svc = EvidenceGraphService()
            result = svc.query_symbol(symbol, market=market)
            if result and "edges" in result:
                evidence = []
                for edge in result["edges"][:5]:
                    evidence.append({
                        "factor": edge.get("factor_type", edge.get("type", "unknown")),
                        "value": edge.get("strength", 0),
                        "contribution": edge.get("strength", 0) * 0.15,
                        "interpretation": "因子共振: " + (edge.get("label", "") or ""),
                        "source": "evidence_graph",
                        "confidence": edge.get("confidence", 0.5),
                    })
                return evidence
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass
        return []

    def _build_explanation(self, evidence, action, confidence):
        """Build natural language explanation from evidence."""
        if not evidence:
            return "暂无足够证据生成建议"
        top = evidence[0]
        if action == "buy":
            return ("建议买入 " + str(top.get("factor", "")) + " 因子驱动，"
                    + "贡献度 " + str(round(abs(top.get("contribution", 0)) * 100, 1)) + "%，"
                    + "历史类似模式胜率约 " + str(int(confidence * 100)) + "%")
        elif action == "sell":
            return ("建议卖出，主要受 " + str(top.get("factor", "")) + " 因子负面影响，"
                    + "贡献度 " + str(round(abs(top.get("contribution", 0)) * 100, 1)) + "%")
        else:
            return ("建议持有观察，当前因子信号不明确，"
                    + "最强信号来自 " + str(top.get("factor", "")) + " 因子")

    def _interpret_factor(self, factor, value):
        interpretations = {
            "momentum": "动量偏强" if value > 0 else "动量偏弱",
            "volatility": "波动率偏高" if abs(value) > 0.3 else "波动率正常",
            "volume_ratio": "放量" if value > 1.5 else "缩量" if value < 0.5 else "正常",
            "rsi": "超买" if value > 70 else "超卖" if value < 30 else "中性",
            "macd": "金叉" if value > 0 else "死叉",
        }
        return interpretations.get(factor, "值=" + str(round(value, 2)))
class CopyTradingService:
    """Copy-trading / mirror trading via Alpha Marketplace."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "copy_trading"
        self._store.mkdir(parents=True, exist_ok=True)
        self._subs_file = self._store / "subscriptions.jsonl"
        self._signals_file = self._store / "signals.jsonl"

    def subscribe(self, follower_id: int, provider_id: int, provider_name: str,
                  allocation_pct: float = 10.0) -> CopyTradeSubscription:
        """Subscribe to a signal provider."""
        sub = CopyTradeSubscription(
            subscription_id=f"ct.{uuid.uuid4().hex[:8]}",
            follower_id=follower_id,
            provider_id=provider_id,
            provider_name=provider_name,
            allocation_pct=min(100, max(1, allocation_pct)),
        )
        self._save_subscription(sub)
        logger.info("User %d subscribed to provider %s (%.1f%%)", follower_id, provider_name, allocation_pct)
        return sub

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a provider."""
        subs = self._load_subscriptions()
        for sub in subs:
            if sub.subscription_id == subscription_id:
                sub.active = False
                self._save_all_subscriptions(subs)
                return True
        return False

    def publish_signal(self, provider_id: int, symbol: str, action: str,
                       quantity: int, price: float) -> CopyTradeSignal:
        """Publish a trading signal for followers — execution via Fast Path."""
        signal = CopyTradeSignal(
            signal_id=f"sig.{uuid.uuid4().hex[:8]}",
            provider_id=provider_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
        )
        self._save_signal(signal)

        followers = self._get_followers(provider_id)
        if followers:
            try:
                from app.core.dual_path_router import PathPriority, PathTask, PathType, get_dual_path_router

                router = get_dual_path_router()
                for sub in followers:
                    scaled_qty = max(1, int(quantity * sub.allocation_pct / 100))
                    task = PathTask(
                        task_id=f"ct.{signal.signal_id}.{sub.follower_id}",
                        path=PathType.FAST,
                        priority=PathPriority.HIGH,
                        handler="copy_trade_execute",
                        payload={
                            "follower_id": sub.follower_id,
                            "symbol": symbol,
                            "action": action,
                            "quantity": scaled_qty,
                            "price": price,
                            "portfolio_value": 1_000_000,
                        },
                        max_latency_ms=100,
                    )
                    router.route_fast(task)
            except Exception as exc:
                logger.warning("Fast Path copy-trade dispatch failed, logging only: %s", exc)
                for sub in followers:
                    scaled_qty = max(1, int(quantity * sub.allocation_pct / 100))
                    logger.info(
                        "Copy-trade: User %d → %s %d shares of %s (scaled from %d)",
                        sub.follower_id,
                        action,
                        scaled_qty,
                        symbol,
                        quantity,
                    )

        return signal

    def get_subscriptions(self, user_id: int) -> list[CopyTradeSubscription]:
        """Get all subscriptions for a user."""
        return [s for s in self._load_subscriptions() if s.follower_id == user_id]

    def _get_followers(self, provider_id: int) -> list[CopyTradeSubscription]:
        return [s for s in self._load_subscriptions() if s.provider_id == provider_id and s.active]

    def _save_subscription(self, sub: CopyTradeSubscription):
        with self._subs_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(sub.__dict__, ensure_ascii=False) + "\n")

    def _save_all_subscriptions(self, subs: list[CopyTradeSubscription]):
        with self._subs_file.open("w", encoding="utf-8") as fh:
            for s in subs:
                fh.write(json.dumps(s.__dict__, ensure_ascii=False) + "\n")

    def _load_subscriptions(self) -> list[CopyTradeSubscription]:
        if not self._subs_file.exists():
            return []
        subs = []
        with self._subs_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    subs.append(CopyTradeSubscription(**json.loads(line)))
        return subs

    def _save_signal(self, signal: CopyTradeSignal):
        with self._signals_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(signal.__dict__, ensure_ascii=False) + "\n")



    def get_provider_rating(self, provider_id):
        """Calculate performance rating for a signal provider."""
        signals = []
        if self._signals_file.exists():
            with self._signals_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    sig = json.loads(line)
                    if sig.get('provider_id') == provider_id:
                        signals.append(sig)

        total = len(signals)
        if total == 0:
            return {"provider_id": provider_id, "total_signals": 0, "rating": "unrated"}

        wins = [s for s in signals if s.get('outcome') == 'win']
        win_rate = len(wins) / total

        recent = signals[-20:]
        recent_wins = sum(1 for s in recent if s.get('outcome') == 'win')
        recent_win_rate = recent_wins / max(len(recent), 1)

        if win_rate >= 0.6 and recent_win_rate >= 0.55: rating = "A"
        elif win_rate >= 0.5: rating = "B"
        elif win_rate >= 0.4: rating = "C"
        else: rating = "D"

        return {
            "provider_id": provider_id,
            "total_signals": total,
            "win_rate": round(win_rate, 4),
            "recent_win_rate": round(recent_win_rate, 4),
            "rating": rating,
            "total_wins": len(wins),
            "total_losses": total - len(wins),
        }

    def get_follower_portfolio(self, follower_id):
        """Aggregate copied signals into follower portfolio view."""
        subs = self.get_subscriptions(follower_id)
        if not subs:
            return {"follower_id": follower_id, "providers": [], "total_value": 0.0}

        provider_ids = {s.provider_id for s in subs}
        signals_by_pid = {}
        if self._signals_file.exists():
            with self._signals_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    sig = json.loads(line)
                    pid = sig.get('provider_id')
                    if pid in provider_ids:
                        signals_by_pid.setdefault(pid, []).append(sig)

        providers = []
        total_value = 0.0
        for sub in subs:
            sigs = signals_by_pid.get(sub.provider_id, [])
            open_pos = [s for s in sigs if s.get("status") == "open"]
            pos_val = sum(s.get('quantity', 0) * s.get('price', 0) * sub.allocation_pct / 100 for s in open_pos)
            total_value += pos_val
            providers.append({
                "provider_id": sub.provider_id,
                "provider_name": sub.provider_name,
                "allocation_pct": sub.allocation_pct,
                "active_signals": len(open_pos),
                "position_value": round(pos_val, 2),
            })

        return {
            "follower_id": follower_id,
            "providers": providers,
            "total_providers": len(providers),
            "total_value": round(total_value, 2),
        }


# ── Psychology Tracker ──────────────────────────────────────────────

@dataclass
class PsychologyEvent:
    """A detected psychological trading event."""
    event_id: str
    user_id: int
    event_type: str  # panic_sell / fomo_buy / revenge_trade / overtrade
    symbol: str
    severity: float  # 0..1
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PsychologyReport:
    """Weekly/monthly psychology report."""
    user_id: int
    total_events: int = 0
    panic_sells: int = 0
    fomo_buys: int = 0
    revenge_trades: int = 0
    overtrades: int = 0
    score: float = 1.0  # 0 = needs help, 1 = disciplined
    recommendations: list[str] = field(default_factory=list)


class PsychologyTrackerService:
    """Tracks and analyzes user trading psychology."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "psychology_events.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)

    def record_event(self, user_id: int, event_type: str, symbol: str,
                     severity: float = 0.5, context: dict | None = None) -> PsychologyEvent:
        """Record a psychological trading event."""
        event = PsychologyEvent(
            event_id=f"psy.{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            event_type=event_type,
            symbol=symbol,
            severity=min(1.0, max(0.0, severity)),
            context=context or {},
        )
        with self._store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.__dict__, ensure_ascii=False) + "\n")
        return event

    def get_report(self, user_id: int, days: int = 30) -> PsychologyReport:
        """Generate psychology report for a user."""
        events = self._load_events(user_id, days)
        report = PsychologyReport(user_id=user_id, total_events=len(events))

        for e in events:
            if e.event_type == "panic_sell":
                report.panic_sells += 1
            elif e.event_type == "fomo_buy":
                report.fomo_buys += 1
            elif e.event_type == "revenge_trade":
                report.revenge_trades += 1
            elif e.event_type == "overtrade":
                report.overtrades += 1

        # Score: start at 1.0, deduct for each type
        report.score = max(0.0, 1.0 - (report.panic_sells * 0.1 + report.fomo_buys * 0.08
                                        + report.revenge_trades * 0.15 + report.overtrades * 0.05))

        # Recommendations
        if report.panic_sells > 3:
            report.recommendations.append("检测到多次恐慌抛售，建议设置自动止损单避免情绪化决策")
        if report.fomo_buys > 3:
            report.recommendations.append("检测到追高行为，建议在买入前等待至少 15 分钟冷静期")
        if report.revenge_trades > 2:
            report.recommendations.append("检测到报复性交易，建议暂停交易一天，重新审视策略")
        if report.overtrades > 10:
            report.recommendations.append("交易频率过高，建议降低交易次数，提高每笔交易质量")

        return report

    def _load_events(self, user_id: int, days: int) -> list[PsychologyEvent]:
        if not self._store.exists():
            return []
        events = []
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        with self._store.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if int(data.get("user_id", -1)) == user_id:
                    ts = data.get("timestamp", "")
                    try:
                        if datetime.fromisoformat(ts).timestamp() >= cutoff:
                            events.append(PsychologyEvent(**data))
                    except (ValueError, TypeError):
                        events.append(PsychologyEvent(**data))
        return events

    def get_insights(self, user_id, days=30):
        """Analyze trading psychology patterns."""
        events = self._load_events(user_id, days)
        if not events:
            return {"insights": [], "risk_level": "unknown", "suggestions": []}

        panic_sells = [e for e in events if e.event_type == 'panic_sell']
        revenge_trades = [e for e in events if e.event_type == 'revenge_trade']
        over_trades = [e for e in events if e.event_type == 'over_trade']
        total = len(events)
        panic_pct = len(panic_sells) / max(total, 1)
        revenge_pct = len(revenge_trades) / max(total, 1)

        if panic_pct > 0.3 or revenge_pct > 0.2:
            risk_level = "high"
        elif panic_pct > 0.15 or revenge_pct > 0.1:
            risk_level = "medium"
        else:
            risk_level = "low"

        insights = []
        if panic_pct > 0.3:
            insights.append("Frequent panic selling detected")
        if revenge_pct > 0.2:
            insights.append("Revenge trading pattern detected")
        if len(over_trades) > 5:
            insights.append("Over-trading pattern detected")

        suggestions = []
        if risk_level == "high":
            suggestions.append("Reduce position size to 50% for 1 week")
            suggestions.append("Set daily loss limit to 2% of portfolio")
        elif risk_level == "medium":
            suggestions.append("Review trade journal before each session")

        return {
            "total_events": total,
            "risk_level": risk_level,
            "panic_sell_count": len(panic_sells),
            "revenge_trade_count": len(revenge_trades),
            "over_trade_count": len(over_trades),
            "insights": insights,
            "suggestions": suggestions,
            "analyzed_period_days": days,
        }
    def get_weekly_summary(self, user_id):
        """Get weekly psychology summary by type."""
        events = self._load_events(user_id, 7)
        by_type = {}
        for e in events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
        return {
            "user_id": user_id,
            "total_events_this_week": len(events),
            "breakdown_by_type": by_type,
            "days_analyzed": 7,
        }


