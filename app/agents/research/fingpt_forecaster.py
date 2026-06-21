from __future__ import annotations
"""FinGPT-inspired forecasting agent node for LangGraph."""


import re
from datetime import date
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from ...modules.ai_agent.services.fingpt_application_service import FinGPTApplicationService
from ...core.logger import get_logger
from ...domain.entities import FinGPTPrediction
from .react_loop import react_with_tools
from .state import ResearchState

logger = get_logger(__name__)

FINGPT_FORECASTER_SYSTEM_PROMPT = """你是一个基于 FinGPT 理念的深度金融预测专家。
你的任务是结合历史价格走势、财务基本面和近期新闻，给出下周的预测。

分析框架：
1. [Company/Crypto Introduction]: 简要背景。
2. [Positive Factors]: 基于新闻和数据的看多因素 (2-4条)。
3. [Potential Concerns]: 基于新闻和数据的看空因素 (2-4条)。
4. [Prediction]: 预测涨跌幅 (例如: up by 1-2%, down by more than 5%)。
5. [Summary Analysis]: 支持你预测的综合理由。

请严格按照 FinGPT 风格输出，保持专业且客观。"""


def build_prediction_from_forecast_text(ticker: str, report: str) -> FinGPTPrediction:
    """将节点自由文本尽最大努力映射为结构化实体（解析失败时使用占位字段）。"""
    text = (report or "").strip()
    prediction_date = date.today().isoformat()

    movement = _extract_after_heading(text, r"\[Prediction\]", r"\[Summary Analysis\]|5\.")
    if not movement:
        m = re.search(
            r"(?is)4\.\s*\[Prediction\][^\n]*\n(.+?)(?=\n\s*5\.|\n\s*\[Summary|\Z)",
            text,
        )
        if m:
            movement = m.group(1).strip().split("\n")[0]

    predicted_movement = (movement or "(see narrative)").strip()
    if len(predicted_movement) > 500:
        predicted_movement = predicted_movement[:497] + "…"

    positive_factors = _extract_bullets_between(text, r"\[Positive Factors\]", r"\[Potential Concerns\]|3\.")
    potential_concerns = _extract_bullets_between(text, r"\[Potential Concerns\]", r"\[Prediction\]|4\.")
    if not positive_factors:
        positive_factors = ["（未能从正文解析看多要点，全文见 analysis_summary）"]
    if not potential_concerns:
        potential_concerns = ["（未能从正文解析风险提示，全文见 analysis_summary）"]

    analysis_summary = text if len(text) <= 8000 else text[:7997] + "\n…"

    confidence = _guess_confidence(text)

    return FinGPTPrediction(
        ticker=ticker or "UNKNOWN",
        prediction_date=prediction_date,
        predicted_movement=predicted_movement,
        analysis_summary=analysis_summary,
        positive_factors=positive_factors[:20],
        potential_concerns=potential_concerns[:20],
        confidence=confidence,
    )


def _guess_confidence(text: str) -> float:
    m = re.search(r"(?:confidence|置信度|情感得分)\s*[:：]?\s*([0-9]+(?:\.[0-9]+)?)", text, re.I)
    if m:
        try:
            v = float(m.group(1))
            return max(0.05, min(0.95, v if v <= 1.0 else v / 100.0))
        except ValueError as e:
            logger.warning("fingpt_forecaster.py._guess_confidence: %s", e)
    return 0.55


def _extract_after_heading(block: str, start: str, until: str) -> str:
    pat = rf"(?is){start}\s*:?\s*(.+?)(?={until}|\Z)"
    m = re.search(pat, block)
    if not m:
        return ""
    chunk = m.group(1).strip()
    line = chunk.split("\n")[0].strip()
    return line


def _extract_bullets_between(block: str, start_heading: str, until_heading: str) -> list[str]:
    m = re.search(
        rf"(?is){start_heading}\s*:?\s*(.+?)(?={until_heading}|\Z)",
        block,
    )
    if not m:
        return []
    chunk = m.group(1)
    out: list[str] = []
    for raw in chunk.splitlines():
        line = raw.strip()
        if not line or line.startswith("[") and "]" in line[:12]:
            continue
        line = re.sub(r"^[-*•]\s*", "", line)
        line = re.sub(r"^\d+[\.)]\s*", "", line).strip()
        if line:
            out.append(line[:500])
    return out[:12]


async def run_fingpt_forecast_step(
    llm: BaseChatModel,
    state: ResearchState,
    fingpt_app: FinGPTApplicationService | None,
) -> dict[str, Any]:
    """生成 FinGPT 风格预测文本；若启用 MySQL 则经应用服务落库。"""
    ticker = state.get("ticker")
    query = state.get("query")

    context = f"""标的: {ticker}
用户需求: {query}

[基础面快照]:
{state.get('fundamental_report', '暂无数据')}

[技术面趋势]:
{state.get('technical_report', '暂无数据')}

[舆情分析]:
{state.get('sentiment_report', '暂无数据')}
"""

    report = await react_with_tools(
        llm,
        [],
        system=FINGPT_FORECASTER_SYSTEM_PROMPT,
        user=context,
        max_rounds=1,
    )

    if fingpt_app and fingpt_app.can_write_research_prediction() and (report or "").strip():
        try:
            pred = build_prediction_from_forecast_text(str(ticker or "").strip(), report)
            rec = fingpt_app.record_prediction(pred)
            if not rec.get("ok"):
                logger.warning("FinGPT record_prediction not ok: %s", rec.get("error"))
        except Exception as exc:  # noqa: BLE001
            logger.exception("FinGPT forecast persistence failed: %s", exc)

    return {"fingpt_forecast": report}
