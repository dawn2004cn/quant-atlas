from __future__ import annotations
"""News relevance filtering utilities."""


import re
from collections.abc import Mapping, Sequence
from typing import Any

from ...core.logger import get_logger


def _compile_keywords(keywords: list[str]) -> re.Pattern | None:
    """Compile keyword list into a single compiled regex for O(n) matching."""
    if not keywords:
        return None
    escaped = [re.escape(k) for k in keywords]
    # Sort by length descending so longer matches are tried first
    escaped.sort(key=len, reverse=True)
    return re.compile("|".join(escaped))

logger = get_logger(__name__)


def industry_boost_tokens(industry_hint: str) -> list[str]:
    """Extract short tokens from industry string for title/summary boosting."""
    s = (industry_hint or "").strip()
    if len(s) < 2:
        return []
    parts = re.split(r"[,，、/&\s]+", s)
    out: list[str] = [s]
    for p in parts:
        t = p.strip()
        if len(t) >= 2:
            out.append(t)
    dedup: list[str] = []
    seen: set[str] = set()
    for x in out:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    return dedup[:10]


class NewsRelevanceFilter:
    """Rule-based news relevance scoring (0-100)."""

    def __init__(self, stock_code: str, company_name: str) -> None:
        self.stock_code = (stock_code or "").strip().upper()
        self.company_name = (company_name or "").strip()

        self.exclude_keywords = [
            "etf", "指数基金", "基金", "指数", "index", "fund", "权重股", "成分股", "板块", "概念股", "主题基金", "跟踪指数", "被动投资", "指数投资", "基金持仓",
            "公告", "披露", "报告", "年报", "季报", "半年报", "财报", "数据", "信息", "新闻", "资讯", "媒体", "报道", "分析", "解读", "观点", "评论",
            "行业", "公司", "市场", "交易所", "监管", "政策", "宏观", "经济", "数据", "报告", "分析师", "研究", "报告", "公告", "会议", "发布会",
            "融资", "融券", "量化", "套利", "期权", "期货", "衍生品", "商品", "债券", "外汇", "货币", "利率", "信贷", "通胀", "通缩", "GDP", "CPI", "PPI",
            "PMI", "PPI", "CPI", "GDP", "通胀", "利率", "信贷", "债务", "汇率", "货币政策", "财政政策", "财政部", "央行", "央行", "货币政策", "财政政策",
        ]
        self.include_keywords = [
            "业绩", "财报", "公告", "重组", "并购", "分红", "派息", "高管", "董事", "股东",
            "增持", "减持", "回购", "年报", "季报", "半年报", "业绩预告", "业绩快报", "股东大会", "董事会", "监事会",
            "重大合同", "投资", "收购", "出售", "转让", "合作", "协议",
            "新股上市", "IPO", "增发", "配股", "定向增发", "融资", "并购重组", "借壳", "上市", "退市", "摘帽",
            "创新", "技术", "研发", "产品", "新药", "新能源", "智能", "芯片", "半导体", "5G", "人工智能", "AI", "大数据",
            "需求", "订单", "签约", "中标", "产能", "扩张", "复苏", "改善", "回升", "乐观", "积极", "利好", "提振",
            "提价", "涨价", "降价", "降成本", "降费", "利润率", "毛利率", "净利率", "现金流", "回购", "稳定", "增长",
            "竞争优势", "成本优势", "技术领先", "研发投入", "专利", "创新药", "新技术", "新材料", "新能源", "智能化", "数字化",
            "受益", "获益", "带动", "推动", "促进", "提振", "支撑", "加强", "巩固", "扩大", "深化", "提升", "改善", "回升", "复苏",
            "稳健", "安全", "可靠", "领先", "领先地位", "市场份额", "高增长", "超预", "亮眼", "大幅", "强力",
            "重大利好", "积极信号", "前景广阔", "潜力巨大", "表现优异", "市场认可",
            "首次覆盖", "目标价上调", "评级上调", "强烈推荐", "买入评级", "买入信号",
        ]
        self.strong_keywords = [
            "停牌", "复牌", "涨停", "跌停", "限售解禁", "股权激励", "员工持股", "定增", "配股", "送股", "资产重组", "借壳上市", "退市", "摘帽", "ST",
            "巨亏", "资不抵债", "破产", "清算", "重组失败", "诉讼", "仲裁", "调查", "处罚", "监管", "警示", "风险", "警告",
            "黑天鹅", "重大风险", "流动性危机", "信用风险", "强制执行", "停产", "减产", "取消", "终止", "延期", "推迟",
            "暴跌", "大跌", "腰斩", "崩盘", "崩塌", "重挫", "危机", "衰退", "滑坡", "不及预期", "业绩下滑", "亏损",
            "利空", "负面", "悲观", "质疑", "争议", "威胁", "不确定", "警报", "失利", "技术封锁", "脱钩",
        ]
        # Compiled regexes for O(n) keyword matching
        self._exclude_re = _compile_keywords(self.exclude_keywords)
        self._include_re = _compile_keywords(self.include_keywords)
        self._strong_re = _compile_keywords(self.strong_keywords)

    def calculate_relevance_score(
        self,
        title: str,
        content: str,
        *,
        industry_boost_keywords: Sequence[str] = (),
    ) -> float:
        score = 0.0
        title_lower = title.lower()
        content_lower = content.lower()

        # Company and stock code matches (higher weight for title)
        if self.company_name:
            if self.company_name in title_lower:
                score += 60.0
            elif self.company_name in content_lower:
                score += 30.0
        if self.stock_code:
            if self.stock_code in title_lower:
                score += 50.0
            elif self.stock_code in content_lower:
                score += 25.0

        # Compiled regex matching — O(n) per category instead of O(n*m)
        if self._strong_re:
            if self._strong_re.search(title_lower):
                score += 40.0
            elif self._strong_re.search(content_lower):
                score += 20.0

        if self._include_re:
            if self._include_re.search(title_lower):
                score += 20.0
            elif self._include_re.search(content_lower):
                score += 10.0

        if self._exclude_re:
            if self._exclude_re.search(title_lower):
                score -= 50.0
            if self._exclude_re.search(content_lower):
                score -= 25.0

        # Penalize if company/stock code is present but excluded keywords are also prominent in title
        if self.company_name and self.stock_code and self._exclude_re:
            if (
                self.company_name not in title_lower
                and self.stock_code not in title_lower
                and self._exclude_re.search(title_lower)
            ):
                score -= 40.0

        # Industry boost keywords (lower weight)
        if industry_boost_keywords:
            boost_re = _compile_keywords([k for k in industry_boost_keywords if len(k.strip()) >= 2])
            if boost_re:
                if boost_re.search(title_lower):
                    score += 8.0
                elif boost_re.search(content_lower):
                    score += 4.0

        # Ensure score is within bounds [0, 100]
        return max(0.0, min(100.0, score))


def rank_news_items(
    items: Sequence[Mapping[str, Any]],
    stock_code: str,
    company_name: str,
    *,
    min_score: float = 25.0,
    max_items: int = 12,
    industry_boost_keywords: Sequence[str] = (),
) -> tuple[list[dict[str, Any]], str]:
    """Score and sort news items; fallback to top-N when threshold yields empty."""
    flt = NewsRelevanceFilter(stock_code, company_name)
    scored: list[tuple[dict[str, Any], float]] = []
    for raw in items:
        title = str(raw.get("title") or "")
        content = str(raw.get("summary") or raw.get("content") or "")
        s = flt.calculate_relevance_score(
            title,
            content,
            industry_boost_keywords=industry_boost_keywords,
        )
        row = dict(raw)
        row["relevance_score"] = round(s, 2)
        scored.append((row, s))
    scored.sort(key=lambda x: x[1], reverse=True)

    above = [r for r, s in scored if s >= min_score][:max_items]
    if above:
        return above, "threshold"

    fallback = [r for r, _ in scored[:max_items]]
    return fallback, "fallback_top_n"