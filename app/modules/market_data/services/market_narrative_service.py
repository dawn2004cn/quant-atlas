from __future__ import annotations
"""Market Narrative Service - Convert market data into readable stories."""

from datetime import datetime
from typing import Any
import requests
import json
from snownlp import SnowNLP

from app.core.logger import get_logger

logger = get_logger(__name__)
class MarketNarrativeService:
    def __init__(self, market_service: object, ai_adapter: object):
        self._market = market_service
        self._ai = ai_adapter
        self._cache = []
        self._cache_time = None

    def get_latest_pulse(self, market_code: str = "CN") -> list[dict[str, Any]]:
        """获取全市场叙事脉动 - 从东方财富实时抓取"""
        now = datetime.now()

        # 缓存 5 分钟
        if self._cache and self._cache_time and (now - self._cache_time).seconds < 300:
            return self._cache

        events = self._fetch_eastmoney_news()
        if events:
            self._cache = events
            self._cache_time = now
            return events

        return events if events else self._get_fallback_events()

    def _fetch_eastmoney_news(self) -> list[dict[str, Any]]:
        """从东方财富抓取实时新闻"""
        try:
            url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://stock.eastmoney.com/"
            }
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                response.encoding = 'utf-8'  # 确保中文不乱码
                # 1. 清洗数据：去掉开头的 "var ajaxResult="
                raw_text = response.text
                json_str = raw_text.replace("var ajaxResult=", "")
                # 2. 解析 JSON
                data = json.loads(json_str)
                #data = response.json()
                if data.get("LivesList"):
                    events = []
                    for item in data["LivesList"][:10]:
                        content = item.get("title", "")
                        time_str = item.get("showtime", "")
                        if content:
                            #sentiment = self._analyze_sentiment(content)
                            sentiment = self._analyze_sentiment(content)
                            events.append({
                                "time": time_str.replace("今天", "").replace("刚刚", datetime.now().strftime("%H:%M")),
                                "type": "news",
                                "content": content[:80] + ("..." if len(content) > 80 else ""),
                                "sentiment": sentiment
                            })

                    logger.info(f"news: {events}")
                    return events
        except Exception as e:
            logger.warning(f"Fetch EastMoney news failed: {e}")
        return []

    def _analyze_sentiment(self, text: str) -> str:
        """简单情感分析"""
        text = text.lower()
        positive_words = ["涨", "升", "利好", "上涨", "创新高", "突破", "反弹", "涨停", "拉升", "大涨", '增长', '盈利', '重组', '买入', '增持', '预增']
        negative_words = ["跌", "降", "利空", "下跌", "创新低", "跳水", "回落", "跌停", "重挫", "大跌", '减少', '亏损', '破产', '卖出', '减持', '预减']

        for word in positive_words:
            if word in text:
                return "bullish"
        for word in negative_words:
            if word in text:
                return "bearish"
        return "neutral"

    def analyze_sentiment_simple(self, text: str)-> str:
        s = SnowNLP(text)
        score = s.sentiments  # 情感得分

        if score > 0.6:
            tag = "利好 (Positive)"
        elif score < 0.4:
            tag = "利空 (Negative)"
        else:
            tag = "中性 (Neutral)"

        return tag

    def _get_fallback_events(self) -> list[dict[str, Any]]:
        """备用事件 - 当抓取失败时使用"""
        now = datetime.now().strftime("%H:%M")
        return [
            {
                "time": now,
                "type": "sector",
                "content": "市场整体震荡整理，板块轮动分化，关注业绩预增方向。",
                "sentiment": "neutral"
            },
            {
                "time": now,
                "type": "agent",
                "content": "AI Agent 持续关注科技板块回调后的低吸机会。",
                "sentiment": "neutral"
            },
            {
                "time": now,
                "type": "risk",
                "content": "短线注意高位股回调风险，建议控制仓位。",
                "sentiment": "bearish"
            }
        ]
