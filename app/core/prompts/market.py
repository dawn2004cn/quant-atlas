"""Market analysis prompts.

Adapted from guanlan's market prompt templates.
"""

from __future__ import annotations

from app.core.prompts import PromptTemplate

MARKET_ANALYSIS_SYSTEM = """你是一位专业的市场分析师。请基于提供的市场数据进行分析：

1. 大盘走势：判断主要指数的趋势方向和强度
2. 板块轮动：分析热点板块和资金流向
3. 市场情绪：评估当前市场情绪（恐慌/中性/贪婪）
4. 资金面：分析北向资金、主力资金动向
5. 关键事件：关注可能影响市场的重大事件
6. 风险提示：提示潜在的系统性风险
7. 投资建议：给出短期和中期配置建议"""

MARKET_TEMPLATE = PromptTemplate(
    domain="market",
    system=MARKET_ANALYSIS_SYSTEM,
)