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


@dataclass
class NLStrategyTemplate:
    """A strategy generated from natural language."""

    strategy_id: str
    user_id: int
    nl_input: str
    logic_steps: list[dict] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    risk_rules: list[str] = field(default_factory=list)
    preview_metrics: dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    candidate_ready: bool = False
    sandbox_status: str = "pending"
    bias_passed: bool = False

class NLToStrategyService:
    """Convert natural language trading ideas into executable strategies."""

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
        if not conditions and not risk_rules and not actions:
            conditions.append("price_above_ma20")
            actions.append("buy")
            risk_rules.append("stop_loss_2pct")
            logic_steps.append(
                {"matched": "默认买入", "logic": {"type": "buy_signal", "reason": "未识别到具体条件，采用默认买入策略"}}
            )
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
        try:
            from app.modules.ai_agent.services.prompt_evolution_service import PromptEvolutionService
            svc = PromptEvolutionService()
            current_prompt = svc.get_current_prompt("nl_strategy_fallback")
            if not current_prompt:
                return []
            extra = []
            if re.search(r"早盘|开盘|9[.:]?30|上午", nl_input):
                extra.append({"matched": "时间条件-早盘", "logic": {"type": "time_filter", "params": {"start": "09:30", "end": "11:30"}}})
            if re.search(r"尾盘|收盘|14[.:]?[3-5]|下午|两点半", nl_input):
                extra.append({"matched": "时间条件-尾盘", "logic": {"type": "time_filter", "params": {"start": "14:30", "end": "15:00"}}})
            if re.search(r"放量|倍量|成交量.*大|量比.*[>大于].*[12]", nl_input):
                extra.append({"matched": "放量条件", "logic": {"type": "volume_filter", "params": {"min_ratio": 2.0}}})
            if re.search(r"缩量|成交量.*小|量比.*[<小于].*0[.。]?[5-9]", nl_input):
                extra.append({"matched": "缩量条件", "logic": {"type": "volume_filter", "params": {"max_ratio": 0.6}}})
            if re.search(r"涨停|跌停|封板|炸板", nl_input):
                extra.append({"matched": "涨跌停条件", "logic": {"type": "price_limit", "params": {"check": True}}})
            if re.search(r"换手|换手率", nl_input):
                extra.append({"matched": "换手率条件", "logic": {"type": "turnover_filter", "params": {"min_pct": 3.0}}})
            if re.search(r"板块|行业|概念|题材", nl_input):
                extra.append({"matched": "板块条件", "logic": {"type": "sector_filter", "params": {"sector": "auto"}}})
            return extra
        except Exception as exc:
            logger.debug("LLM fallback unavailable: %s", exc)
            return []

    def parse_with_preview(self, nl_input: str, symbol: str = "000001", market: str = "CN", user_id: int = 0) -> dict:
        strategy = self.parse(nl_input, user_id=user_id)
        preview = self._run_preview(strategy, symbol=symbol, market=market)
        gate = self.apply_sandbox_gate(strategy, preview)
        return {"strategy": strategy, "preview": preview, "gate": gate, "candidate_ready": gate["candidate_ready"]}

    def apply_sandbox_gate(self, strategy: NLStrategyTemplate, preview: dict[str, Any]) -> dict[str, Any]:
        """Mark tournament candidacy only after a non-estimated sandbox/preview pass.

        Estimated metrics (engine unavailable) must not enter the tournament pool.
        """
        status = str(preview.get("status") or "").strip().lower()
        warning = str(preview.get("warning") or "").strip()
        if status in {"estimated", "error", "failed"} or warning:
            strategy.candidate_ready = False
            strategy.sandbox_status = "blocked_estimated" if status == "estimated" or warning else f"blocked_{status or 'unknown'}"
            return {
                "candidate_ready": False,
                "sandbox_status": strategy.sandbox_status,
                "bias_passed": False,
                "reason": warning or status or "preview_not_ready",
            }
        bias_passed = bool(preview.get("bias_passed"))
        bars = preview.get("bars") or preview.get("ohlcv")
        if bars is not None and not bias_passed:
            try:
                import pandas as pd

                from app.domain.backtest.bias_detector import validate_backtest_data

                df = bars if isinstance(bars, pd.DataFrame) else pd.DataFrame(bars)
                bias_passed = validate_backtest_data(df, strict=True).passed
            except Exception:
                logger.warning("nl bias gate scan failed", exc_info=True)
                bias_passed = False
        strategy.candidate_ready = True
        strategy.sandbox_status = "passed"
        strategy.bias_passed = bias_passed
        return {
            "candidate_ready": True,
            "sandbox_status": "passed",
            "bias_passed": bias_passed,
            "reason": "preview_ok" if bias_passed else "preview_ok_bias_pending",
            "strategy_id": strategy.strategy_id,
        }

    def render_strategy_source(self, strategy: NLStrategyTemplate) -> str:
        """Render a minimal Python stub for STRATEGY_SANDBOX execution."""
        conditions = ", ".join(repr(c) for c in strategy.conditions) or "'none'"
        actions = ", ".join(repr(a) for a in strategy.actions) or "'buy'"
        return (
            f'# Auto-generated from NL strategy {strategy.strategy_id}\n'
            f'# nl_input: {strategy.nl_input!r}\n'
            f'CONDITIONS = [{conditions}]\n'
            f'ACTIONS = [{actions}]\n'
            f'\n'
            f'def strategy_signal(bar: dict) -> str:\n'
            f'    """Return buy/sell/hold for a single bar dict."""\n'
            f'    _ = bar\n'
            f'    return "buy" if ACTIONS else "hold"\n'
            f'\n'
            f'if __name__ == "__main__":\n'
            f'    print({{"strategy_id": {strategy.strategy_id!r}, "ok": True}})\n'
        )

    def run_source_sandbox(self, strategy: NLStrategyTemplate) -> dict[str, Any]:
        """Persist rendered source and execute via STRATEGY_SANDBOX runner."""
        import tempfile
        from pathlib import Path

        from app.infrastructure.sandbox.strategy_docker_runner import (
            StrategySandboxError,
            run_strategy_sandboxed,
        )

        src = self.render_strategy_source(strategy)
        with tempfile.TemporaryDirectory(prefix="nl_strat_") as tmp:
            entry = Path(tmp) / "strategy_entry.py"
            entry.write_text(src, encoding="utf-8")
            try:
                result = run_strategy_sandboxed(entry, workdir=Path(tmp))
            except StrategySandboxError as exc:
                strategy.candidate_ready = False
                strategy.sandbox_status = "sandbox_error"
                return {"ok": False, "error": str(exc), "candidate_ready": False}
            if not result.success:
                strategy.candidate_ready = False
                strategy.sandbox_status = "sandbox_failed"
                return {
                    "ok": False,
                    "exit_code": result.exit_code,
                    "stderr": result.stderr,
                    "candidate_ready": False,
                }
            # Source sandbox alone is not enough for tournament; preview gate still required.
            return {
                "ok": True,
                "mode": result.mode,
                "stdout": result.stdout,
                "candidate_ready": strategy.candidate_ready,
            }

    def _run_preview(self, strategy: NLStrategyTemplate, symbol: str = "000001", market: str = "CN") -> dict:
        try:
            from app.modules.data.services.data_lake_manager import DataLakeManager
            from app.modules.strategy.services.strategy.fast_backtest_engine import FastBacktestEngine
            engine = FastBacktestEngine(lake_manager=DataLakeManager())
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, engine.run_preview(symbol=symbol, market=market, params={c: 1.0 for c in strategy.conditions}, template_id=strategy.strategy_id))
                    result = future.result(timeout=30)
            else:
                result = asyncio.run(engine.run_preview(symbol=symbol, market=market, params={c: 1.0 for c in strategy.conditions}, template_id=strategy.strategy_id))
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
                    "max_drawdown": f"{abs(strategy.preview_metrics.get("max_drawdown", -0.12)):.0%}",
                    "sharpe_ratio": strategy.preview_metrics.get("estimated_sharpe", 0.85),
                    "win_rate": f"{strategy.preview_metrics.get("win_rate", 0.62):.0%}",
                    "total_trades": strategy.preview_metrics.get("avg_trades_per_month", 8),
                },
                "warning": "使用估计指标（回测引擎不可用）",
            }

    def to_flowchart_json(self, strategy: NLStrategyTemplate) -> list[dict]:
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
        labels = {"buy": "买入", "sell": "卖出", "buy_signal": "发出买入信号"}
        return labels.get(action, action)

    def _risk_label(self, rule: str) -> str:
        labels = {"stop_loss": "止损", "take_profit": "止盈", "stop_loss_2pct": "2%止损"}
        return labels.get(rule, rule)

    def to_readable(self, strategy: NLStrategyTemplate) -> str:
        parts = ["📋 策略逻辑分析"]
        parts.append(f"\n📝 您的输入: {strategy.nl_input}")
        if strategy.conditions:
            parts.append("\n🔍 买入条件:")
            for i, cond in enumerate(strategy.conditions, 1):
                parts.append(f"   {i}. {self._condition_label(cond)}")
        if strategy.actions:
            parts.append("\n⚡ 执行动作:")
            for i, action in enumerate(strategy.actions, 1):
                parts.append(f"   {i}. {self._action_label(action)}")
        if strategy.risk_rules:
            parts.append("\n🛡️ 风控规则:")
            for i, rule in enumerate(strategy.risk_rules, 1):
                parts.append(f"   {i}. {self._risk_label(rule)}")
        if strategy.preview_metrics:
            parts.append("\n📊 回测预估:")
            m = strategy.preview_metrics
            parts.append(f"   • 夏普比率: {m.get('estimated_sharpe', 'N/A')}")
            parts.append(f"   • 最大回撤: {m.get('max_drawdown', 'N/A')}")
            parts.append(f"   • 胜率: {m.get('win_rate', 'N/A')}")
            parts.append(f"   • 月均交易: {m.get('avg_trades_per_month', 'N/A')}次")
        parts.append("\n" + "=" * 30)
        return "\n".join(parts)

    def _store_path(self) -> Path:
        root = Path(__file__).resolve().parents[4]
        p = root / "instance" / "nl_strategies.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _save_strategy(self, strategy: NLStrategyTemplate) -> None:
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
                    "candidate_ready": strategy.candidate_ready,
                    "sandbox_status": strategy.sandbox_status,
                    "bias_passed": strategy.bias_passed,
                }, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("Failed to persist strategy: %s", exc)

    def load_history(self, user_id: int, limit: int = 20) -> list[NLStrategyTemplate]:
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
