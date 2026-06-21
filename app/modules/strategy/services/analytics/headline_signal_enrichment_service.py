from __future__ import annotations

"""Merge offline headline signal cache with lightweight rule fallback."""

import re
from typing import Any

from app.domain.shared.market_time_aligner import DateAligner
from app.infrastructure.cache.headline_signal_cache import HeadlineSignalCache
from app.infrastructure.calendar.cn_sse_calendar import is_cn_equity_trading_day

_CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
_BULLISH = ("上涨", "利好", "突破", "预增", "回购", "降息", "降准", "大涨", "涨停", "创新高")
_BEARISH = ("下跌", "利空", "减持", "亏损", "暴跌", "立案", "处罚", "警示", "跌停", "下调")


class HeadlineSignalEnrichmentService:
    """Read cached Celery annotations; uncached headlines get rule-based tags."""

    def __init__(self, cache: HeadlineSignalCache | None = None) -> None:
        self._cache = cache or HeadlineSignalCache()

    @staticmethod
    def headline_key(headline: dict[str, Any]) -> str:
        title = str(headline.get("title") or "").strip().lower()
        published = str(headline.get("published_at") or "")[:16]
        return f"{published}|{title}"

    @staticmethod
    def _trading_day_fn(market: str):
        if (market or "").upper() == "CN":
            return is_cn_equity_trading_day
        return DateAligner.default_trading_day_fn(market)

    def enrich_headlines(self, headlines: list[dict[str, Any]], *, market: str) -> list[dict[str, Any]]:
        cached = self._cache.load(market)
        trading_day_fn = self._trading_day_fn(market)
        out: list[dict[str, Any]] = []
        for raw in headlines:
            item = dict(raw)
            key = self.headline_key(item)
            tag = cached.get(key)
            if tag:
                item.update(tag)
            else:
                item.update(self.rule_tag(item))
            item = DateAligner.attach_market_time_slot(
                item,
                market=market,
                is_trading_day=trading_day_fn,
            )
            out.append(item)
        return out

    def batch_compute_and_cache(
        self,
        headlines: list[dict[str, Any]],
        *,
        market: str,
    ) -> dict[str, dict[str, Any]]:
        patch: dict[str, dict[str, Any]] = {}
        for raw in headlines:
            item = dict(raw)
            key = self.headline_key(item)
            patch[key] = self.rule_tag(item)
        self._cache.merge(market, patch)
        return patch

    def rule_tag(self, headline: dict[str, Any]) -> dict[str, Any]:
        title = str(headline.get("title") or "")
        summary = str(headline.get("summary") or "")
        text = f"{title} {summary}"
        bull = sum(1 for kw in _BULLISH if kw in text)
        bear = sum(1 for kw in _BEARISH if kw in text)
        if bull > bear and bull > 0:
            signal_tag = "利好"
            sentiment_score = min(0.95, 0.35 + bull * 0.12)
        elif bear > bull and bear > 0:
            signal_tag = "利空"
            sentiment_score = max(-0.95, -0.35 - bear * 0.12)
        else:
            signal_tag = "中性"
            sentiment_score = 0.0
        symbols = list(dict.fromkeys(_CODE_RE.findall(text)))[:6]
        confidence = round(min(0.88, 0.42 + (bull + bear) * 0.08), 2)
        return {
            "signal_tag": signal_tag,
            "sentiment_score": round(sentiment_score, 3),
            "affected_symbols": symbols,
            "confidence": confidence,
            "source": "rule",
        }
