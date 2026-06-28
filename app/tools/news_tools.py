from __future__ import annotations
"""News Tools - 新闻和情绪分析工具."""


from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from langchain_core.tools import tool

from ..core.logger import get_logger

logger = get_logger(__name__)


class StockNewsToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    ok: bool = True
    error: str | None = None
    news: list[dict[str, Any]] = Field(default_factory=list)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class SentimentScoreToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    ok: bool = True
    error: str | None = None
    score: float = 0.0
    label: str = ""
    top_news: list[dict[str, Any]] = Field(default_factory=list)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class MarketMoodToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    market: str
    ok: bool = True
    error: str | None = None
    mood: dict[str, Any] = Field(default_factory=dict)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


POSITIVE_KEYWORDS = [
    "涨停", "涨停板", "暴涨", "大幅上涨", "突破", "创新高", "业绩增长",
    "扭亏", "预增", "中标", "签约", "订单", "产能扩张", "景气",
    "买入", "增持", "推荐", "看好", "目标价", "上调",
]

NEGATIVE_KEYWORDS = [
    "跌停", "跌停板", "暴跌", "大幅下跌", "破位", "创新低", "业绩亏损",
    "预减", "预警", "违约", "诉讼", "处罚", "减持", "下调",
    "卖出", "减持", "看空", "风险", "下调",
]


def _sentiment_score_from_text(text: str) -> float:
    """基于关键词计算文本情感得分."""
    text.lower()
    positive_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
    negative_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
    total = positive_count + negative_count
    if total == 0:
        return 0.0
    return (positive_count - negative_count) / total


def _sentiment_label(score: float) -> str:
    """将情感得分转换为标签."""
    if score > 0.3:
        return "偏多"
    if score < -0.3:
        return "偏空"
    return "中性"


def _extract_key_metrics(named: dict[str, float]) -> str:
    """提取关键指标字符串."""
    if not named:
        return "N/A"
    parts = [f"{k}: {v:.2f}" for k, v in list(named.items())[:3]]
    return ", ".join(parts)


@tool
def get_stock_news(ticker: str, max_news: int = 30, days_back: int = 7) -> StockNewsToolResult:
    """获取股票相关新闻."""
    from ..application.services.tool_facade_service import get_tool_facade_service
    from datetime import datetime, timedelta
    from ..core.utils.news_utils import rank_news_items

    try:
        service = get_tool_facade_service()
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)

        stock_news = service.get_stock_news(ticker, start_time, end_time, max_news)
        industry_news = service.get_industry_news(ticker, start_time, end_time, max_news // 2)

        all_news = stock_news + industry_news
        ranked_news = rank_news_items(all_news, ticker)

        return StockNewsToolResult(
            ticker=ticker,
            news=ranked_news[:max_news],
            evidence=f"Retrieved {len(ranked_news)} news items for {ticker}",
            confidence=0.8 if ranked_news else 0.4,
        )
    except Exception as e:
        logger.error(f"get_stock_news failed: {e}")
        return StockNewsToolResult(
            ticker=ticker,
            ok=False,
            error=str(e),
            confidence=0.3,
        )


@tool
def get_news_sentiment(ticker: str, max_news: int = 30, days_back: int = 7) -> SentimentScoreToolResult:
    """对标的最近N条新闻做情感打分."""
    from datetime import datetime, timedelta
    from ..application.services.tool_facade_service import get_tool_facade_service
    from ..application.services.sentiment_filter_service import get_sentiment_service

    try:
        service = get_tool_facade_service()
        get_sentiment_service()

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        news_items = service.get_stock_news(ticker, start_time, end_time, max_news)

        if not news_items:
            return SentimentScoreToolResult(
                ticker=ticker,
                ok=False,
                error="No news available",
                score=0.0,
                label="中性",
                confidence=0.3,
            )

        scored_news = []
        total_score = 0.0

        for news in news_items:
            title = news.get("title", "")
            content = news.get("content", "")
            text = f"{title} {content}"
            score = _sentiment_score_from_text(text)
            scored_news.append({
                **news,
                "sentiment_score": score,
                "sentiment_label": _sentiment_label(score),
            })
            total_score += score

        avg_score = total_score / len(scored_news)
        label = _sentiment_label(avg_score)

        top_news = sorted(scored_news, key=lambda x: abs(x.get("sentiment_score", 0)), reverse=True)[:5]

        return SentimentScoreToolResult(
            ticker=ticker,
            score=avg_score,
            label=label,
            top_news=top_news,
            evidence=f"Analyzed {len(news_items)} news items, avg sentiment: {avg_score:.2f}",
            confidence=0.7,
        )
    except Exception as e:
        logger.error(f"get_news_sentiment failed: {e}")
        return SentimentScoreToolResult(
            ticker=ticker,
            ok=False,
            error=str(e),
            score=0.0,
            label="异常",
            confidence=0.2,
        )


@tool
def get_market_mood(market: str = "CN", days_back: int = 3) -> MarketMoodToolResult:
    """获取市场情绪仪表盘."""
    from ..application.services.market_narrative_service import get_market_narrative_service

    try:
        service = get_market_narrative_service()
        mood = service.get_market_mood(market=market, days_back=days_back)

        if mood.get("fear_greed_index", 50) < 30:
            pass
        elif mood.get("fear_greed_index", 50) > 70:
            pass

        return MarketMoodToolResult(
            market=market,
            mood=mood,
            evidence=f"Retrieved market mood for {market}",
            confidence=0.7,
        )
    except Exception as e:
        logger.error(f"get_market_mood failed: {e}")
        return MarketMoodToolResult(
            market=market,
            ok=False,
            error=str(e),
            confidence=0.3,
        )
