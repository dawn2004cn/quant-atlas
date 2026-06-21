from __future__ import annotations
"""News provider implementations."""


import os

import logging
logger = logging.getLogger(__name__)
from ...domain.entities import NewsItem
from ...domain.enums import MarketCode
from ...domain.ports import NewsProvider
from .cn_portal_news import (

    fetch_10jqka_gdxw_headlines,
    fetch_eastmoney_roll_headlines,
    filter_headlines_for_symbol,
    portal_headlines_cn,
)


class AkshareNewsProvider(NewsProvider):
    """AkShare 个股新闻 + 东方财富滚动 / 同花顺股道门户快讯（A 股合并）。"""

    _PORTAL_MAX_MERGE = 12

    @staticmethod
    def _http_blocked() -> bool:
        return any("127.0.0.1:9" in os.environ.get(name, "") for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"))

    def get_stock_news(self, symbol: str, market: MarketCode) -> list[NewsItem]:
        if market in (MarketCode.US, MarketCode.HK):
            return self._get_yfinance_news(symbol, market)
        if market is MarketCode.CRYPTO:
            return self._get_crypto_news(symbol)
        if self._http_blocked():
            return []

        frame = None
        # 批量回填场景：可通过环境变量禁用 AkShare 个股新闻（少量机器/网络下会卡住），仅保留门户快讯过滤。
        if os.environ.get("NEWS_BACKFILL_FAST_ONLY", "").strip() not in ("1", "true", "TRUE", "yes", "YES"):
            try:
                import akshare as ak

                frame = ak.stock_news_em(symbol=symbol)
            except Exception:
                frame = None

        items: list[NewsItem] = []
        if frame is not None and hasattr(frame, "head") and hasattr(frame, "iterrows"):
            try:
                for _, row in frame.head(20).iterrows():
                    items.append(
                        NewsItem(
                            title=str(row.get("新闻标题", "")),
                            published_at=str(row.get("发布时间", "")),
                            source=str(row.get("文章来源", "akshare")),
                            url=str(row.get("新闻链接", "")),
                            summary=str(row.get("新闻内容", ""))[:280],
                        )
                    )
            except Exception as e:
                logger.warning("news.py.get_stock_news: %s", e)

        if not self._http_blocked():
            try:
                em = fetch_eastmoney_roll_headlines(limit=35)
                th = fetch_10jqka_gdxw_headlines(limit=35)
                portal_hits = filter_headlines_for_symbol(em + th, symbol)[: self._PORTAL_MAX_MERGE]
                seen = {(i.title.strip(), (i.url or "").strip()) for i in items}
                for h in portal_hits:
                    title = str(h.get("title") or "").strip()
                    url = str(h.get("url") or "").strip()
                    if not title or (title, url) in seen:
                        continue
                    seen.add((title, url))
                    items.append(
                        NewsItem(
                            title=title,
                            published_at=str(h.get("published_at") or ""),
                            source=str(h.get("source") or "portal"),
                            url=url,
                            summary=str(h.get("summary") or "")[:280],
                        )
                    )
            except Exception as e:
                logger.warning("news.py.get_stock_news: %s", e)

        return items

    def get_market_headlines(self, market: MarketCode, *, limit: int = 40) -> list[NewsItem]:
        """A 股：东方财富滚动 + 同花顺股道合并（门户层，不按代码过滤）。"""
        if market is not MarketCode.CN or self._http_blocked():
            return []
        try:
            raw = portal_headlines_cn(limit_per_source=max(10, min(30, limit // 2 + 5)))[:limit]
        except Exception:
            return []
        out: list[NewsItem] = []
        for h in raw:
            title = str(h.get("title") or "").strip()
            if len(title) < 4:
                continue
            out.append(
                NewsItem(
                    title=title,
                    published_at=str(h.get("published_at") or ""),
                    source=str(h.get("source") or "portal"),
                    url=str(h.get("url") or ""),
                    summary=str(h.get("summary") or "")[:280],
                )
            )
        return out[:limit]

    def get_industry_news(self, industry: str, market: MarketCode) -> list[NewsItem]:
        topic = industry.strip() or "market"
        if market in (MarketCode.US, MarketCode.HK, MarketCode.CN):
            return [
                NewsItem(
                    title=f"{topic} 行业跟踪",
                    published_at="",
                    source="industry-feed",
                    summary=f"行业 {topic} 最新动态（市场: {market.value}）。",
                )
            ]
        return [
            NewsItem(
                title=f"{topic} 板块动态",
                published_at="",
                source="crypto-feed",
                summary=f"加密行业 {topic} 相关新闻摘要。",
            )
        ]

    def _get_yfinance_news(self, symbol: str, market: MarketCode) -> list[NewsItem]:
        try:
            import yfinance as yf

            news = yf.Ticker(symbol).news or []
            items: list[NewsItem] = []
            for item in news[:20]:
                items.append(
                    NewsItem(
                        title=str(item.get("title", "")),
                        published_at=str(item.get("providerPublishTime", "")),
                        source=str(item.get("publisher", "yfinance")),
                        url=str(item.get("link", "")),
                        summary=str(item.get("summary", ""))[:280],
                    )
                )
            return items
        except Exception:
            return []

    def _get_crypto_news(self, symbol: str) -> list[NewsItem]:
        return [
            NewsItem(
                title=f"{symbol} 市场快讯",
                published_at="",
                source="crypto-news",
                summary=f"{symbol} 最新市场消息（示例新闻，建议接入专门新闻源）。",
            )
        ]
