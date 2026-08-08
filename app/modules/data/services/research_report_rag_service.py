from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""RAG-based research report service."""


from typing import Any

from app.domain.ports.news_archive_port import NewsArchiveRepository


class ResearchReportRAGService:
    """RAG service for semantic search of research reports."""

    def __init__(self, news_archive: NewsArchiveRepository):
        self._archive = news_archive
        self._embeddings_cache: dict[str, list[float]] = {}

    def search_reports(
        self,
        symbol: str,
        query: str,
        market: str = "CN",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search research reports for a symbol based on semantic query."""
        raw_reports = self._archive.list_for_symbol(market, symbol.upper(), limit=limit * 2)

        if not raw_reports:
            return []

        query_lower = query.lower()
        query_keywords = set(query_lower.split())

        scored_reports = []
        for report in raw_reports:
            content = report.get("content", "") or ""
            title = report.get("title", "") or ""

            combined_text = f"{title} {content}".lower()

            score = 0
            for keyword in query_keywords:
                if keyword in combined_text:
                    score += 1

            if query_lower in combined_text:
                score += 5

            if score > 0:
                scored_reports.append((score, report))

        scored_reports.sort(key=lambda x: x[0], reverse=True)

        return [r[1] for r in scored_reports[:limit]]

    def summarize_opinion_trend(
        self,
        symbol: str,
        market: str = "CN",
        limit: int = 20,
    ) -> GenericResponseDTO:
        """Analyze opinion trend for a symbol over time."""
        raw_reports = self._archive.list_for_symbol(market, symbol.upper(), limit=limit)

        if not raw_reports:
            return {
                "symbol": symbol,
                "trend": "neutral",
                "sentiment_score": 0.0,
                "recent_reports": [],
                "summary": f"No research reports found for {symbol}",
            }

        positive_keywords = ["买入", "增持", "推荐", "看好", "上涨", "超配", "bullish", "buy", "outperform"]
        negative_keywords = ["卖出", "减持", "看空", "下跌", "低配", "bearish", "sell", "underperform"]
        neutral_keywords = ["持有", "中性", "持有", "hold", "neutral"]

        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for report in raw_reports:
            content = (report.get("content", "") or "").lower()
            title = (report.get("title", "") or "").lower()

            combined = f"{title} {content}"

            if any(kw in combined for kw in positive_keywords):
                positive_count += 1
            elif any(kw in combined for kw in negative_keywords):
                negative_count += 1
            else:
                neutral_count += 1

        total = positive_count + negative_count + neutral_count
        if total == 0:
            sentiment_score = 0.0
            trend = "neutral"
        else:
            sentiment_score = (positive_count - negative_count) / total
            if sentiment_score > 0.2:
                trend = "positive"
            elif sentiment_score < -0.2:
                trend = "negative"
            else:
                trend = "neutral"

        recent = [
            {
                "title": r.get("title", ""),
                "date": r.get("published_at", r.get("fetched_at", "")),
                "source": r.get("source", ""),
            }
            for r in raw_reports[:5]
        ]

        summary = f"Analysis of {len(raw_reports)} reports: {positive_count} positive, {neutral_count} neutral, {negative_count} negative. Overall sentiment: {trend}."

        return {
            "symbol": symbol,
            "trend": trend,
            "sentiment_score": round(sentiment_score, 3),
            "positive_count": positive_count,
            "neutral_count": neutral_count,
            "negative_count": negative_count,
            "recent_reports": recent,
            "summary": summary,
        }