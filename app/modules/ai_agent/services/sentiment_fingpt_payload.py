from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""将自由文本叙述映射为 ``fingpt_sentiment`` 入库字段（研究 Sentiment 节点 / AI 个股分析等复用）。"""


import re


def build_sentiment_payload_from_analyst_report(narrative: str) -> GenericResponseDTO:
    """从叙述中抽取 ``sentiment_score`` / ``impact_level`` / ``summary``（失败则合理回退）。"""
    text = (narrative or "").strip()
    if not text:
        return {"sentiment_score": 0.5, "impact_level": "Medium", "summary": ""}

    score = _extract_score(text)
    impact = _extract_impact(text)
    summary = text if len(text) <= 4000 else text[:3997] + "\n…"

    return {
        "sentiment_score": score,
        "impact_level": impact,
        "summary": summary,
    }


def _extract_score(text: str) -> float:
    patterns = (
        r"(?:sentiment_score|情感得分|情绪得分|得分)\s*[:：]?\s*([0-9]+(?:\.[0-9]+)?)",
        r"(?:score)\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
    )
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            try:
                v = float(m.group(1))
                if v > 1.0:
                    v = v / 100.0
                return max(0.0, min(1.0, v))
            except ValueError:
                continue
    bull = len(re.findall(r"(看多|偏多|乐观|正面|利好)", text))
    bear = len(re.findall(r"(看空|偏空|悲观|负面|利空)", text))
    if bull + bear > 0:
        return round(0.5 + 0.08 * (bull - bear), 3)
    return 0.5


def _extract_impact(text: str) -> str:
    if re.search(r"(影响级别|impact\s*level|impact)\s*[:：]?\s*(High|高|重大|极高)", text, re.I):
        return "High"
    if re.search(r"(影响级别|impact\s*level|impact)\s*[:：]?\s*(Low|低|轻微)", text, re.I):
        return "Low"
    if re.search(r"\bHigh\b|\b高影响\b|\b重大\b", text):
        return "High"
    if re.search(r"\bLow\b|\b低影响\b|\b轻微\b", text):
        return "Low"
    return "Medium"
