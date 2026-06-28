from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Signal-to-Noise Filter - 舆情信噪比过滤服务.

利用LLM自动识别新闻质量，过滤无效信息."""


from datetime import datetime


class NewsQualityFilter:
    """新闻质量过滤器."""

    # 质量评分关键词
    HIGH_QUALITY_KEYWORDS = [
        "财报", "营收", "净利润", "同比增长", "订单", "中标",
        "产能", "扩产", "政策", "监管", "业绩预告",
    ]

    LOW_QUALITY_KEYWORDS = [
        "疑似", "或将", "可能", "传闻", "小道",
        "蹭热点", "强行", "硬蹭", "公关稿",
    ]

    @staticmethod
    def evaluate_quality(news_text: str) -> GenericResponseDTO:
        """评估新闻质量."""
        text = news_text.lower()

        # 统计关键词
        high_count = sum(1 for k in NewsQualityFilter.HIGH_QUALITY_KEYWORDS if k in text)
        low_count = sum(1 for k in NewsQualityFilter.LOW_QUALITY_KEYWORDS if k in text)

        # 评分
        if low_count >= 2:
            quality = "low"
            reason = "疑似无效信息或蹭热点"
        elif high_count >= 2:
            quality = "high"
            reason = "包含实质信息"
        else:
            quality = "medium"
            reason = "信息价值一般"

        return {
            "quality": quality,
            "score": high_count - low_count,
            "reason": reason,
        }


class NewsImpactEstimator:
    """新闻影响估算器."""

    @staticmethod
    def estimate_impact(
        news_text: str,
        sentiment: float,
    ) -> GenericResponseDTO:
        """估算新闻对股价的影响."""
        # 简单关键词匹配
        positive_impact = ["大涨", "订单", "中标", "扩产", "业绩增长"]
        negative_impact = ["预警", "亏损", "减持", "诉讼", "调查"]

        impact_direction = "neutral"
        impact_magnitude = "low"

        text = news_text.lower()
        pos_count = sum(1 for k in positive_impact if k in text)
        neg_count = sum(1 for k in negative_impact if k in text)

        if pos_count > neg_count:
            impact_direction = "positive"
            impact_magnitude = "medium" if pos_count >= 2 else "low"
        elif neg_count > pos_count:
            impact_direction = "negative"
            impact_magnitude = "medium" if neg_count >= 2 else "low"

        # 估算对净利润的影响
        if "10%" in text:
            impact_estimate = "10%"
        elif "20%" in text:
            impact_estimate = "20%"
        elif "50%" in text:
            impact_estimate = "50%"
        else:
            impact_estimate = "未知"

        return {
            "direction": impact_direction,
            "magnitude": impact_magnitude,
            "estimated_impact": f"{impact_estimate} 净利润影响",
            "sentiment": sentiment,
        }


class SentimentNoiseFilterService:
    """舆情信噪比过滤服务."""

    def filter_news(
        self,
        news_list: list[dict],
    ) -> GenericResponseDTO:
        """过滤新闻，返回高质量内容."""
        if not news_list:
            return {
                "ok": True,
                "filtered": [],
                "summary": "无新闻",
            }

        processed = []
        for news in news_list:
            text = news.get("title", "") + " " + news.get("content", "")

            quality = NewsQualityFilter.evaluate_quality(text)
            impact = NewsImpactEstimator.estimate_impact(
                text, news.get("sentiment", 0.5)
            )

            processed.append({
                "news": news,
                "quality": quality,
                "impact": impact,
                "filter_out": quality.get("quality") == "low",
            })

        # 过滤低质量
        filtered = [p for p in processed if not p["filter_out"]]
        filtered.sort(key=lambda x: x["impact"].get("magnitude") != "low", reverse=True)

        return {
            "ok": True,
            "generated_at": datetime.now().isoformat(),
            "total_news": len(news_list),
            "filtered_count": len(filtered),
            "filtered": filtered[:10],
            "summary": f"过滤掉{len(news_list) - len(filtered)}条低质量新闻",
        }
