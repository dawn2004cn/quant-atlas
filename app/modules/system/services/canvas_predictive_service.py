"""Context-Aware Canvas — Phase 17.
Predictive UI + one-click strategy export."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json

from app.core.logger import get_logger
from app.domain.strategy.strategy_spec import StrategySpec

logger = get_logger(__name__)


@dataclass
class ToolSuggestion:
    """One tool suggestion for the predictive UI."""
    tool_id: str
    tool_name: str
    tool_icon: str
    probability: float  # 0..1
    reason: str = ""


@dataclass
class CanvasExport:
    """Exported strategy from canvas."""
    name: str
    logic: str
    spec: dict[str, Any]
    estimated_sharpe: float = 0.0
    risk_level: str = "medium"


class CanvasPredictiveService:
    """Generates predictive tool suggestions and one-click exports."""
    
    # Archetype → likely tool mappings
    _ARCHETYPE_TOOLS = {
        "novice": [
            ToolSuggestion("chip_distribution", "筹码分布", "bar-chart-2", 0.85, "查看持仓成本结构"),
            ToolSuggestion("ai_sentiment", "AI 情绪解读", "message-circle", 0.78, "了解市场情绪"),
            ToolSuggestion("longhu_tracker", "龙虎榜追踪", "target", 0.65, "查看主力动向"),
        ],
        "day_trader": [
            ToolSuggestion("da_ban_radar", "打板雷达", "zap", 0.92, "监控涨停板封单"),
            ToolSuggestion("wave_band_radar", "波段雷达", "activity", 0.88, "寻找买卖点"),
            ToolSuggestion("order_flow", "订单流分析", "trending-up", 0.82, "分析资金流向"),
        ],
        "strategist": [
            ToolSuggestion("factor_ic", "因子 IC 分析", "hash", 0.90, "分析因子有效性"),
            ToolSuggestion("alpha_search", "Alpha 搜索", "search", 0.85, "遗传算法搜索"),
            ToolSuggestion("backtest", "回测引擎", "play-circle", 0.80, "策略回测验证"),
        ],
    }
    
    # Symbol context → tool suggestions
    _SYMBOL_CONTEXT = {
        "limit_up": [ToolSuggestion("da_ban_radar", "打板雷达", "zap", 0.95, "涨停股分析")],
        "gap_up": [ToolSuggestion("chip_distribution", "筹码分布", "bar-chart-2", 0.88, "跳空后的筹码变化")],
        "high_volume": [ToolSuggestion("order_flow", "订单流分析", "trending-up", 0.90, "异动放量分析")],
        "new_low": [ToolSuggestion("stress_test", "压力测试", "thermometer", 0.85, "新低品种的风险评估")],
    }
    
    def predict_tools(self, archetype: str, symbol: str | None = None,
                      context: dict | None = None) -> list[ToolSuggestion]:
        """Predict most likely needed tools."""
        tools = []
        base = self._ARCHETYPE_TOOLS.get(archetype, self._ARCHETYPE_TOOLS["novice"])
        tools.extend(base)
        
        if context:
            key = context.get("symbol_context")
            if key in self._SYMBOL_CONTEXT:
                for t in self._SYMBOL_CONTEXT[key]:
                    # Boost probability
                    t.probability = min(1.0, t.probability * 1.1)
                    tools.insert(0, t)
        
        # Deduplicate by tool_id
        seen = set()
        unique = []
        for t in tools:
            if t.tool_id not in seen:
                seen.add(t.tool_id)
                unique.append(t)
        
        return unique[:5]  # Top 5
    
    def export_strategy(self, canvas_json: dict) -> CanvasExport:
        """Export canvas logic as a deployable strategy."""
        try:
            name = canvas_json.get("name", "未命名策略")
            logic = canvas_json.get("logic", {})
            spec = StrategySpec.from_canvas(canvas_json).to_dict()
            return CanvasExport(
                name=name,
                logic=json.dumps(logic, ensure_ascii=False),
                spec=spec,
                estimated_sharpe=spec.get("metrics", {}).get("predicted_sharpe", 0.0),
                risk_level=spec.get("risk", "medium"),
            )
        except Exception as exc:
            logger.warning("Canvas export failed: %s", exc)
            return CanvasExport(
                name=canvas_json.get("name", "导出失败"),
                logic=str(exc),
                spec={"error": str(exc)},
            )
