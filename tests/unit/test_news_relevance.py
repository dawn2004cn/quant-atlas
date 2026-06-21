from app.core.utils.news_utils import (
    NewsRelevanceFilter,
    industry_boost_tokens,
    rank_news_items,
)


def test_calculate_relevance_score_company_in_title():
    flt = NewsRelevanceFilter("600036", "招商银行")
    s = flt.calculate_relevance_score("招商银行发布三季报", "")
    assert s >= 50


def test_industry_boost_tokens():
    toks = industry_boost_tokens("银行, 证券")
    assert "银行" in toks or any("银行" in t for t in toks)


def test_rank_news_items_fallback_when_all_below_threshold():
    items = [{"title": "上证180ETF指数基金策略", "summary": ""}]
    ranked, mode = rank_news_items(items, "600519", "贵州茅台", min_score=80, max_items=5)
    assert mode == "fallback_top_n"
    assert len(ranked) == 1
    assert "relevance_score" in ranked[0]
