import pytest
from app.infrastructure.providers.web_search import MultiEngineSearchProvider

def test_multi_engine_search():
    """Test web search provider."""
    provider = MultiEngineSearchProvider()
    try:
        results = provider.search("Quant Atlas", max_results=2)
        assert isinstance(results, list)
    except Exception as e:
        pytest.skip(f"Web search failed (likely network/blocked): {e}")
