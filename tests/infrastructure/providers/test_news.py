import pytest
from app.infrastructure.providers.cn_portal_news import portal_headlines_cn
from app.infrastructure.providers.cn_jqka_news import JqkaNewsProvider

def test_portal_headlines_cn():
    """Test fetching portal news headlines."""
    news = portal_headlines_cn(limit_per_source=5)
    assert isinstance(news, list)
    if news:
        assert 'title' in news[0]
        assert 'url' in news[0]

def test_jqka_stock_news():
    """Test fetching stock-specific news from Jqka."""
    provider = JqkaNewsProvider()
    news = provider.get_stock_news('000001', limit=5)
    assert isinstance(news, list)
    if news:
        assert 'title' in news[0]
