"""Strategy Synthesizer Service — NL → StrategySpec AST → compiled code.

This service is the heart of Phase 14.1. It:

1. Classifies whether a natural-language query is a simple screening request
   (fallback to ``AdvancedNLParser``) or a full strategy specification.
2. For strategy queries, sends a structured prompt to the LLM adapter to
   produce a JSON AST, validates it, and builds a ``StrategySpec``.
3. Compiles the AST into Python, PineScript, TDX, or MQL5 code.
4. Generates plain-language "Evidence Cards" explaining why the strategy
   suggests a trade.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict
from typing import Any

from app.domain.dto.service_result import GenericResponseDTO
from app.domain.strategies.strategy_synthesizer_models import (
    ConditionGroup,
    ExitMode,
    ExitRule,
    FactorNode,
    LanguageTarget,
    OperatorKind,
    StrategySpec,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent classification helpers
# ---------------------------------------------------------------------------

_STRATEGY_KEYWORDS = [
    "买入", "卖出", "止损", "止盈",
    "跌破", "突破", "金叉", "死叉",
    "如果.*就", "如果.*则", "如果.*买", "如果.*卖",
    "帮我制定.*策略", "写一个.*策略", "创建.*策略", "生成.*策略",
]

# Compile once at import time
_STRATEGY_RE = re.compile("|".join(_STRATEGY_KEYWORDS))


def _is_strategy_intent(query: str) -> bool:
    """Return True when the query describes a full strategy, not just a screen."""
    if _STRATEGY_RE.search(query):
        return True
    # Heuristic: mentions of 2+ action verbs → strategy
    action_verbs = ["买入", "卖出", "止损", "止盈", "跌破", "突破", "金叉", "死叉"]
    count = sum(1 for kw in action_verbs if kw in query)
    return count >= 2


# ---------------------------------------------------------------------------
# LLM prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
你是量化交易策略专家。将用户的自然语言描述转换为结构化的策略 AST。

输出 JSON 格式（不要输出任何其他文本）：
{
  "name": "策略名称",
  "description": "简短描述",
  "entry_conditions": {
    "logic": "and",
    "children": [
      {"left_factor": "price", "right_factor": "sma_20", "operator": "greater", "params": {"period": 20}},
      {"left_factor": "rsi", "right_factor": "constant", "operator": "less", "params": {"value": 30}}
    ]
  },
  "exit_rules": [
    {"exit_mode": "percent_stop", "threshold": 0.05, "reference": "entry_price"},
    {"exit_mode": "percent_stop", "threshold": 0.10, "reference": "entry_price"}
  ]
}

操作符映射：
- greater: 大于/高于/超过
- less: 小于/低于/跌破
- equals: 等于/约为
- cross_above: 金叉/上穿
- cross_below: 死叉/下穿
- above_sma: 在均线上方
- below_sma: 在均线下方
- rsi_overbought: RSI超买
- rsi_oversold: RSI超卖
- volume_spike: 放量/成交量放大
- breakout: 突破
- breakdown: 跌破

止损/止盈模式：
- percent_stop: 百分比止损/止盈
- indicator_stop: 指标止损
- trailing_stop: 移动止损
- time_stop: 时间止损
- manual: 手动退出

因子命名规则：
- price: 股价
- sma_N: N日均线 (如 sma_20, sma_60)
- ema_N: N日指数均线 (如 ema_12)
- rsi: RSI 指标
- macd_histogram: MACD 柱状图
- volume: 成交量
- volume_ma_N: 成交量 N 日均量
- atr_N: N日 ATR

退出规则参考：
- entry_price: 以入场价为基准
- high_watermark: 以最高价为基准 (移动止损)

如果没有明确的入场条件，entry_conditions 的 children 可以为空数组。
如果没有止损/止盈，exit_rules 可以为空数组。
"""


def _build_parse_prompt(user_query: str) -> str:
    return f"用户策略描述：{user_query}\n\n请将其转换为上述 JSON 格式的 AST。"


# ---------------------------------------------------------------------------
# AST validation
# ---------------------------------------------------------------------------

_VALID_OPERATORS = set(e.value for e in OperatorKind)
_VALID_FACTORS = {
    "price", "volume", "rsi", "macd_histogram", "macd_line", "macd_signal",
    "open", "high", "low", "close", "change_pct",
}
_VALID_EXIT_MODES = set(e.value for e in ExitMode)


def _validate_ast_json(data: dict[str, Any]) -> list[str]:
    """Validate LLM-generated AST JSON. Returns list of error messages."""
    errors: list[str] = []

    entry = data.get("entry_conditions")
    if entry:
        if entry.get("logic") not in ("and", "or", "not"):
            errors.append(f"Invalid entry_conditions logic: {entry.get('logic')}")
        for i, child in enumerate(entry.get("children", [])):
            if "left_factor" not in child or "right_factor" not in child:
                errors.append(f"entry_conditions.child[{i}] missing left_factor/right_factor")
            if child.get("operator") not in _VALID_OPERATORS:
                errors.append(f"entry_conditions.child[{i}] invalid operator: {child.get('operator')}")

    for i, rule in enumerate(data.get("exit_rules", [])):
        if rule.get("exit_mode") not in _VALID_EXIT_MODES:
            errors.append(f"exit_rules[{i}] invalid exit_mode: {rule.get('exit_mode')}")
        if "threshold" not in rule:
            errors.append(f"exit_rules[{i}] missing threshold")

    if not data.get("name"):
        errors.append("Missing strategy name")

    return errors


# ---------------------------------------------------------------------------
# NL → Rust operator mapping
# ---------------------------------------------------------------------------

NL_TO_RUST_OPERATOR: dict[str, tuple[str, str]] = {
    "sma": ("calculate_sma", "Simple Moving Average"),
    "ema": ("calculate_ema", "Exponential Moving Average"),
    "atr": ("calculate_atr", "Average True Range"),
    "zscore": ("calculate_zscore", "Z-Score"),
    "sharpe": ("calculate_sharpe_ratio", "Sharpe Ratio"),
    "drawdown": ("calculate_max_drawdown", "Max Drawdown"),
    "chip": ("calculate_chip_distribution", "Chip Distribution"),
    "spread": ("calculate_spread", "Spread"),
}


# ---------------------------------------------------------------------------
# Code compilation templates
# ---------------------------------------------------------------------------

def _compile_python(spec: StrategySpec) -> str:
    """Generate a Python backtest skeleton from StrategySpec."""
    lines: list[str] = [
        f"# 策略: {spec.name}",
        f"# {spec.description}",
        f"# 自动生成 — 请勿手动编辑",
        "",
        "import pandas as pd",
        "from typing import List, Tuple",
        "",
        "",
        f"class {spec.name.replace(' ', '_').title()}Strategy:",
        f'    """Auto-generated strategy from NL description."""',
        "",
        f"    def __init__(self, **kwargs):",
        f"        self.name = '{spec.name}'",
        f"        self.description = '{spec.description}'",
        f"        self.max_positions = {spec.max_positions}",
        f"        self.capital_per_trade = {spec.capital_per_trade}",
        f"",
        f"    def on_bar(self, bar: dict) -> 'tuple[str, str, int] | None':",
        f"        '''Called on each bar. Returns (action, symbol, quantity) or None.'''",
        f"        pass",
        "",
    ]

    # Entry conditions stub
    lines.append(f"    def check_entry(self, bar: dict) -> bool:")
    lines.append(f"        '''Check entry conditions from AST.'''")
    lines.append(f"        # TODO: translate entry_conditions AST to Python logic")
    lines.append(f"        return False")
    lines.append("")

    # Exit rules stub
    lines.append(f"    def check_exit(self, position: dict, bar: dict) -> 'tuple[bool, str]':")
    lines.append(f"        '''Check exit rules. Returns (should_exit, reason).'''")
    for i, rule in enumerate(spec.exit_rules):
        if rule.exit_mode == ExitMode.PERCENT_STOP:
            pct = int(rule.threshold * 100)
            if i < len(spec.exit_rules) // 2:
                lines.append(f"        # Stop loss {pct}%")
                lines.append(f"        if position['pnl_pct'] <= -{rule.threshold}:")
                lines.append(f"            return True, '止损 {pct}%'")
            else:
                lines.append(f"        # Take profit {pct}%")
                lines.append(f"        if position['pnl_pct'] >= {rule.threshold}:")
                lines.append(f"            return True, '止盈 {pct}%'")
    lines.append(f"        return False, ''")
    lines.append("")

    return "\n".join(lines)


def _compile_pine(spec: StrategySpec) -> str:
    """Generate PineScript (TradingView) code from StrategySpec."""
    lines: list[str] = [
        f"//@version=5",
        f"strategy('{spec.name}', overlay=true)",
        "",
        f"// {spec.description}",
        "",
    ]

    # Entry conditions
    lines.append("// === 入场条件 ===")
    children = spec.entry_conditions.children
    if children:
        pine_parts: list[str] = []
        for child in children:
            if isinstance(child, FactorNode):
                pine_parts.append(_factor_to_pine(child))
        if pine_parts:
            logic = " and " if spec.entry_conditions.logic.value == "and" else " or "
            lines.append(f"entry_signal = {logic.join(pine_parts)}")
    else:
        lines.append("entry_signal = false")
    lines.append("")

    # Exit rules
    lines.append("// === 出场规则 ===")
    for i, rule in enumerate(spec.exit_rules):
        if rule.exit_mode == ExitMode.PERCENT_STOP:
            pct = int(rule.threshold * 100)
            if i < len(spec.exit_rules) // 2:
                lines.append(f"stop_loss_pct = {rule.threshold}")
                lines.append(f"strategy.exit('SL', 'stoploss', loss=stop_loss_pct * 100)")
            else:
                lines.append(f"take_profit_pct = {rule.threshold}")
                lines.append(f"strategy.exit('TP', 'takeprofit', profit=take_profit_pct * 100)")
    lines.append("")

    lines.append("// === 信号执行 ===")
    lines.append("if entry_signal")
    lines.append("    strategy.entry('Long', strategy.long)")
    lines.append("")

    return "\n".join(lines)


def _factor_to_pine(node: FactorNode) -> str:
    """Convert a FactorNode to a PineScript boolean expression."""
    left = node.left_factor
    right = node.right_factor
    op = {
        "greater": ">",
        "less": "<",
        "equals": "==",
        "greater_or_equal": ">=",
        "less_or_equal": "<=",
        "cross_above": "ta.crossover",
        "cross_below": "ta.crossunder",
    }.get(node.operator.value, ">")

    # Transform factor names to PineScript functions
    pine_left = _factor_to_pine_expr(left)
    pine_right = _factor_to_pine_expr(right)

    if node.operator.value in ("cross_above", "cross_below"):
        return f"{op}({pine_left}, {pine_right})"
    return f"{pine_left} {op} {pine_right}"


def _factor_to_pine_expr(factor: str) -> str:
    """Convert a factor name to a PineScript expression."""
    if factor.startswith("sma_"):
        period = factor.replace("sma_", "")
        return f"ta.sma(close, {period})"
    if factor.startswith("ema_"):
        period = factor.replace("ema_", "")
        return f"ta.ema(close, {period})"
    if factor == "rsi":
        return "ta.rsi(close, 14)"
    if factor == "macd_histogram":
        return "ta.macd(close, 12, 26, 9)[2]"
    if factor == "macd_line":
        return "ta.macd(close, 12, 26, 9)[0]"
    if factor == "volume":
        return "volume"
    if factor.startswith("volume_ma_"):
        period = factor.replace("volume_ma_", "")
        return f"ta.sma(volume, {period})"
    if factor == "price" or factor == "close":
        return "close"
    if factor == "high":
        return "high"
    if factor == "low":
        return "low"
    if factor == "open":
        return "open"
    if factor == "change_pct":
        return "close / close[1] - 1"
    if factor == "constant":
        return "0"
    return f"{factor}"


def _compile_tdx(spec: StrategySpec) -> str:
    """Generate TDX (通达信) formula code from StrategySpec."""
    lines: list[str] = [
        f"{spec.name}:M0:0",
        f"// {spec.description}",
        "// 自动生成 — 请勿手动编辑",
        "",
    ]

    # Define indicators
    children = spec.entry_conditions.children
    defined_vars: dict[str, str] = {}
    for child in children:
        if isinstance(child, FactorNode):
            var_name = f"VAR{len(defined_vars)}"
            tdx_expr = _factor_to_tdx_expr(child)
            lines.append(f"{var_name}: {tdx_expr}")
            defined_vars[child.left_factor] = var_name

    # Entry signal
    lines.append("")
    lines.append("// === 买入信号 ===")
    if children:
        tdx_parts: list[str] = []
        for child in children:
            if isinstance(child, FactorNode):
                tdx_parts.append(_factor_to_tdx_bool(child))
        logic = "AND" if spec.entry_conditions.logic.value == "and" else "OR"
        lines.append(f"BUY_SIGNAL: {' ' + logic + ' '.join(tdx_parts)}")
    else:
        lines.append("BUY_SIGNAL: 0")

    # Exit rules
    lines.append("")
    lines.append("// === 卖出信号 ===")
    for i, rule in enumerate(spec.exit_rules):
        if rule.exit_mode == ExitMode.PERCENT_STOP:
            pct = int(rule.threshold * 100)
            if i < len(spec.exit_rules) // 2:
                lines.append(f"SELL_SIGNAL: CROSS(CLOSE/REF(CLOSE,1)-1, -{rule.threshold})")
            else:
                lines.append(f"SELL_TAKE: CROSS({pct/100}-CLOSE/REF(CLOSE,1), 0)")

    return "\n".join(lines)


def _factor_to_tdx_expr(node: FactorNode) -> str:
    """Convert a FactorNode to a TDX numeric expression."""
    left = _factor_to_tdx_val(node.left_factor)
    right = _factor_to_tdx_val(node.right_factor)
    op = {
        "greater": ">",
        "less": "<",
        "equals": "=",
        "greater_or_equal": ">=",
        "less_or_equal": "<=",
        "cross_above": "CROSS",
        "cross_below": "CROSS",
    }.get(node.operator.value, ">")

    if node.operator.value in ("cross_above", "cross_below"):
        return f"CROSS({left}, {right})"
    return f"({left} {op} {right})"


def _factor_to_tdx_bool(node: FactorNode) -> str:
    """Convert a FactorNode to a TDX boolean expression (1/0)."""
    left = _factor_to_tdx_val(node.left_factor)
    right = _factor_to_tdx_val(node.right_factor)
    return f"IF({left} {node.operator.value.replace('_', ' ')} {right}, 1, 0)"


def _factor_to_tdx_val(factor: str) -> str:
    """Convert a factor name to a TDX function call."""
    if factor.startswith("sma_"):
        period = factor.replace("sma_", "")
        return f"SMA(CLOSE, {period}, 1)"
    if factor.startswith("ema_"):
        period = factor.replace("ema_", "")
        return f"EMA(CLOSE, {period})"
    if factor == "rsi":
        return "RSI(14)"
    if factor == "macd_histogram":
        return "MACD.DIF - MACD.DEA"
    if factor == "volume":
        return "VOL"
    if factor.startswith("volume_ma_"):
        period = factor.replace("volume_ma_", "")
        return f"SMA(VOL, {period}, 1)"
    if factor in ("price", "close"):
        return "CLOSE"
    if factor == "high":
        return "HIGH"
    if factor == "low":
        return "LOW"
    if factor == "open":
        return "OPEN"
    if factor == "constant":
        return "0"
    return factor


# ---------------------------------------------------------------------------
# Evidence card generation
# ---------------------------------------------------------------------------

_FACTOR_INTERPRETATIONS: dict[str, str] = {
    "price": "股价",
    "volume": "成交量",
    "rsi": "RSI 相对强弱指标",
    "macd_histogram": "MACD 柱状图",
    "macd_line": "MACD 快线",
    "macd_signal": "MACD 信号线",
    "open": "开盘价",
    "high": "最高价",
    "low": "最低价",
    "close": "收盘价",
    "change_pct": "涨跌幅",
}

_OPERATOR_LABELS: dict[str, str] = {
    "greater": "高于",
    "less": "低于",
    "equals": "等于",
    "greater_or_equal": "不低于",
    "less_or_equal": "不高于",
    "above_sma": "在均线上方",
    "below_sma": "在均线下方",
    "cross_above": "金叉（上穿）",
    "cross_below": "死叉（下穿）",
    "rsi_overbought": "RSI 超买区",
    "rsi_oversold": "RSI 超卖区",
    "volume_spike": "成交量放大",
    "breakout": "突破阻力位",
    "breakdown": "跌破支撑位",
}

_EXIT_MODE_LABELS: dict[str, str] = {
    "percent_stop": "百分比{mode}",
    "indicator_stop": "指标{mode}",
    "trailing_stop": "移动{mode}",
    "time_stop": "时间{mode}",
    "manual": "手动{mode}",
}


def _interpret_factor(factor_name: str) -> str:
    return _FACTOR_INTERPRETATIONS.get(factor_name, factor_name)


def _interpret_operator(operator: str) -> str:
    return _OPERATOR_LABELS.get(operator, operator)


def _interpret_exit_mode(exit_mode: str, threshold: float) -> str:
    mode_type = "止损" if threshold < 0.08 else "止盈"
    label = _EXIT_MODE_LABELS.get(exit_mode, exit_mode)
    pct = int(abs(threshold) * 100)
    return label.format(mode=f"{mode_type} {pct}%")


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------


class StrategySynthesizerService:
    """NL → StrategySpec AST → compiled code pipeline (LLM-driven)."""

    def __init__(
        self,
        *,
        ai_adapter: Any | None = None,
        rust_indicator_provider: Any | None = None,
        nl_parser: Any | None = None,
    ) -> None:
        self._ai_adapter = ai_adapter
        self._rust_provider = rust_indicator_provider
        self._nl_parser = nl_parser

    # ---- public API -------------------------------------------------------

    def parse_strategy_intent(self, nl_query: str) -> StrategySpec | None:
        """Entry point: classify intent and return StrategySpec or None."""
        if not nl_query or not nl_query.strip():
            return None
        query = nl_query.strip()

        if _is_strategy_intent(query):
            return self._parse_full_strategy(query)
        return None  # Simple screening → caller should use AdvancedNLParser

    def compile_to_language(
        self,
        spec: StrategySpec,
        target: LanguageTarget | str,
    ) -> str:
        """Compile StrategySpec AST to a target language string."""
        if isinstance(target, str):
            target = LanguageTarget(target)

        compiler = {
            LanguageTarget.PYTHON: _compile_python,
            LanguageTarget.PINE: _compile_pine,
            LanguageTarget.TDX: _compile_tdx,
            LanguageTarget.MQL5: _compile_python,  # MQL5 placeholder
        }
        code = compiler[target](spec)
        spec.compiled_code[target.value] = code
        return code

    def compile_all(self, spec: StrategySpec) -> dict[str, str]:
        """Compile to all supported languages."""
        for target in LanguageTarget:
            self.compile_to_language(spec, target)
        return spec.compiled_code

    def synthesize_evidence_card(
        self,
        spec: StrategySpec,
        symbol: str = "",
    ) -> dict[str, Any]:
        """Generate a plain-language evidence card: 'Why buy this?'."""
        factors: list[dict[str, str]] = []
        for child in spec.entry_conditions.children:
            if isinstance(child, FactorNode):
                interp = _interpret_factor(child.left_factor)
                op_label = _interpret_operator(child.operator.value)
                right_desc = child.right_factor.replace("_", " ")
                factors.append({
                    "name": interp,
                    "interpretation": f"{interp}{op_label}{right_desc}",
                    "raw": child.to_dict(),
                })
            elif isinstance(child, ConditionGroup):
                # Sub-group: summarize
                sub_names = []
                for sub in child.children:
                    if isinstance(sub, FactorNode):
                        sub_names.append(_interpret_factor(sub.left_factor))
                factors.append({
                    "name": f"子条件 ({child.logic.value.upper()})",
                    "interpretation": f"包含: {', '.join(sub_names)}",
                    "raw": child.to_dict(),
                })

        exit_descriptions: list[str] = []
        for rule in spec.exit_rules:
            exit_descriptions.append(_interpret_exit_mode(rule.exit_mode.value, rule.threshold))

        return {
            "strategy_name": spec.name,
            "strategy_description": spec.description,
            "symbol": symbol,
            "confidence": "medium",
            "factors": factors,
            "exit_rules": exit_descriptions,
            "why_this_works": self._generate_why_explanation(spec),
            "generated_at": self._utcnow_iso(),
        }

    def preview_full_pipeline(self, nl_query: str) -> dict[str, Any]:
        """Full pipeline: NL → AST → compile → evidence card."""
        spec = self.parse_strategy_intent(nl_query)
        if spec is None:
            return {"ok": False, "error": "未识别到策略意图，请使用简单筛选或重试"}

        codes = self.compile_all(spec)
        evidence = self.synthesize_evidence_card(spec)

        return {
            "ok": True,
            "spec": spec.to_dict(),
            "compiled_code": codes,
            "evidence_card": evidence,
        }

    # ---- private helpers --------------------------------------------------

    def _parse_full_strategy(self, query: str) -> StrategySpec:
        """LLM-driven strategy parsing with validation and fallback."""
        if self._ai_adapter is None:
            logger.warning("StrategySynthesizerService: ai_adapter is None, cannot parse strategy")
            raise RuntimeError("ai_adapter is required for strategy parsing")

        prompt = _build_parse_prompt(query)
        try:
            llm_response = self._call_llm(prompt)
        except Exception as exc:
            logger.error("StrategySynthesizerService: LLM call failed: %s", exc)
            raise RuntimeError(f"LLM parsing failed: {exc}") from exc

        # Parse and validate JSON
        try:
            ast_json = json.loads(llm_response)
        except json.JSONDecodeError as exc:
            logger.error("StrategySynthesizerService: LLM returned invalid JSON: %s", exc)
            raise RuntimeError(f"Invalid JSON from LLM: {llm_response[:200]}") from exc

        errors = _validate_ast_json(ast_json)
        if errors:
            logger.warning("StrategySynthesizerService: AST validation errors: %s", errors)
            # Attempt to repair common issues
            ast_json = self._repair_ast(ast_json, errors)
            errors = _validate_ast_json(ast_json)
            if errors:
                logger.error("StrategySynthesizerService: Unrecoverable AST errors: %s", errors)
                raise RuntimeError(f"AST validation failed: {', '.join(errors)}")

        return StrategySpec.from_dict(ast_json)

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM adapter with the structured prompt."""
        if hasattr(self._ai_adapter, "analyze"):
            result = self._ai_adapter.analyze(
                system_prompt=_SYSTEM_PROMPT,
                user_message=prompt,
                response_format={"type": "json_object"},
            )
            if isinstance(result, dict):
                return str(result.get("analysis", result.get("content", "")))
            return str(result)
        # Fallback: try generic callable
        return str(self._ai_adapter(prompt))

    def _repair_ast(self, ast_json: dict[str, Any], errors: list[str]) -> dict[str, Any]:
        """Attempt to fix common LLM output issues."""
        repaired = dict(ast_json)

        # Fix operator names (map Chinese to English)
        op_map = {
            "大于": "greater",
            "小于": "less",
            "等于": "equals",
            "高于": "greater",
            "低于": "less",
            "金叉": "cross_above",
            "死叉": "cross_below",
            "突破": "breakout",
            "跌破": "breakdown",
            "放量": "volume_spike",
            "超买": "rsi_overbought",
            "超卖": "rsi_oversold",
        }
        for key in ("entry_conditions",):
            entry = repaired.get(key)
            if entry and isinstance(entry, dict):
                for child in entry.get("children", []):
                    op = child.get("operator", "")
                    if op in op_map:
                        child["operator"] = op_map[op]
        for rule in repaired.get("exit_rules", []):
            mode = rule.get("exit_mode", "")
            if mode in ("百分比止损", "百分比止盈"):
                rule["exit_mode"] = "percent_stop"
            elif mode in ("指标止损", "指标止盈"):
                rule["exit_mode"] = "indicator_stop"
            elif mode in ("移动止损", "移动止盈"):
                rule["exit_mode"] = "trailing_stop"

        if not repaired.get("name"):
            repaired["name"] = "自动策略"
        if not repaired.get("description"):
            repaired["description"] = "由自然语言自动生成"

        return repaired

    @staticmethod
    def _generate_why_explanation(spec: StrategySpec) -> str:
        """Generate a plain-language 'why this strategy works' explanation."""
        factor_count = len(spec.entry_conditions.children)
        exit_count = len(spec.exit_rules)

        parts: list[str] = []
        parts.append(f"该策略包含 {factor_count} 个入场条件和 {exit_count} 个退出规则。")

        if spec.exit_rules:
            stops = [r for r in spec.exit_rules if r.threshold < 0.08]
            profits = [r for r in spec.exit_rules if r.threshold >= 0.08]
            if stops:
                pct = int(stops[0].threshold * 100)
                parts.append(f"设置 {pct}% 止损保护本金，控制单笔最大亏损。")
            if profits:
                pct = int(profits[0].threshold * 100)
                parts.append(f"达到 {pct}% 盈利自动止盈，锁定利润。")

        parts.append("策略基于技术指标组合，避免单一信号的假突破风险。")
        return " ".join(parts)

    @staticmethod
    def _utcnow_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
