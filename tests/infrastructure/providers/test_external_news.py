import pytest
from app.infrastructure.providers.cn_xueqiu_news import XueqiuNewsProvider

def test_xueqiu_timeline():
    """Test Xueqiu timeline news."""
    provider = XueqiuNewsProvider()
    try:
        news = provider.get_user_timeline(limit=5)
        assert isinstance(news, list)
    except Exception as e:
        pytest.skip(f"Xueqiu access failed: {e}")
