"""K-line / technical analysis prompts.

Adapted from guanlan's prompt template system:
- KLINE_ANALYSIS_SYSTEM: structured technical analysis
- KLINE_IMAGE_SYSTEM: visual chart recognition
- format_kline_prompt: bar data → readable prompt
"""

from __future__ import annotations

from app.core.prompts import PromptTemplate

KLINE_ANALYSIS_SYSTEM = """你是一位资深量化交易员和技术分析师。你的任务是分析 K 线数据并输出结构化的技术分析报告。

分析框架：
1. 趋势分析：判断当前趋势方向（上升/下降/震荡），确认主要趋势和次要趋势
2. 支撑阻力：识别关键支撑位和阻力位
3. 技术指标：结合均线、MACD、RSI、布林带等指标
4. 成交量分析：量价配合情况
5. 形态识别：识别 K 线组合形态（头肩顶、双底、旗形等）
6. 交易建议：给出具体的入场、止损、止盈建议
7. 风险提示：提示可能的风险因素

注意：
- 基于提供的 K 线数据做客观分析
- 标注数据的时间周期（分钟/小时/日线）
- 给出明确的支撑位和阻力位价格
- 区分短期和长期趋势"""

KLINE_IMAGE_SYSTEM = """你是一位资深图表分析师，擅长从 K 线图截图中识别技术形态。

请分析图中的：
1. 当前价格走势和趋势方向
2. 明显的技术形态（头肩顶、双底双顶、旗形、三角形、楔形等）
3. 关键支撑位和阻力位
4. 成交量变化趋势
5. 均线系统形态（多头排列/空头排列/交叉等）
6. 综合交易建议

请以清晰的结构化格式输出分析结果。"""


def format_kline_data(kline_data: list[dict], symbol: str = "", interval: str = "") -> str:
    """Format OHLCV data into a readable prompt.

    Args:
        kline_data: List of bar dicts with keys: datetime, open, high, low, close, volume
        symbol: Stock/futures symbol
        interval: Timeframe label (e.g. "日线", "1小时", "5分钟")

    Returns:
        Formatted text block for AI prompt context
    """
    lines = [f"标的: {symbol or '未知'}", f"周期: {interval or '未知'}", f"数据点: {len(kline_data)} 根 K 线", ""]

    for bar in kline_data[-50:]:
        dt = bar.get("datetime", bar.get("date", ""))
        o = bar.get("open", 0)
        h = bar.get("high", 0)
        l_ = bar.get("low", 0)
        c = bar.get("close", 0)
        v = bar.get("volume", 0)
        change = ((c - o) / o * 100) if o > 0 else 0
        direction = "↑" if c >= o else "↓"
        lines.append(f"{dt}  O:{o:.2f} H:{h:.2f} L:{l_:.2f} C:{c:.2f} V:{v:.0f} {direction} {change:+.2f}%")

    return "\n".join(lines)


KLINE_TEMPLATE = PromptTemplate(
    domain="kline",
    system=KLINE_ANALYSIS_SYSTEM,
)

KLINE_IMAGE_TEMPLATE = PromptTemplate(
    domain="kline_image",
    system=KLINE_IMAGE_SYSTEM,
)
