"""Chart / visual analysis prompts.

Adapted from guanlan's chart analysis prompt template.
"""

from __future__ import annotations

from app.core.prompts import PromptTemplate

CHART_ANALYSIS_SYSTEM = """你是一位资深图表分析师，擅长技术形态识别和交易决策。

分析要点：
1. 图表整体结构和趋势方向
2. 关键支撑位和阻力位
3. 技术形态识别（趋势线、通道、头肩顶、双底等）
4. 均线系统分析
5. 成交量确认
6. 交易策略建议

请以 JSON 格式输出分析结果，包含：trend, support, resistance, patterns, suggestions。"""

CHART_ANALYSIS_TEMPLATE = PromptTemplate(
    domain="chart",
    system=CHART_ANALYSIS_SYSTEM,
)