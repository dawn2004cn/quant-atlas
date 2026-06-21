"""测试 Web Search (Tavily)"""

from dotenv import load_dotenv

load_dotenv()


def test_tavily_search():
    """测试 Tavily 搜索"""
    print("=== 测试 Web Search (Tavily) ===\n")
    
    from app.infrastructure.providers.web_search import MultiEngineSearchProvider, TavilySearchProvider
    
    # 检查配置
    from app.core.runtime_config import get_runtime
    tavily_key = get_runtime("TAVILY_API_KEY")
    print(f"TAVILY_API_KEY: {'已配置' if tavily_key else '未配置'}")
    if tavily_key:
        print(f"Key: {tavily_key[:20]}...")
    
    # 测试 Tavily 直接搜索
    print("\n1. 测试 TavilySearchProvider:")
    provider = TavilySearchProvider(tavily_key)
    results = provider.search("A股 今日走势", max_results=5)
    print(f"   结果数: {len(results)}")
    for i, r in enumerate(results[:3]):
        print(f"   [{i+1}] {r.get('title', 'N/A')[:50]}")
        print(f"       URL: {r.get('url', '')}")
        print(f"       内容: {r.get('content', '')[:100]}...")
    print()
    
    # 测试 MultiEngineSearchProvider
    print("2. 测试 MultiEngineSearchProvider:")
    multi = MultiEngineSearchProvider()
    results = multi.search("股票 市场分析", max_results=5)
    print(f"   结果数: {len(results)}")
    for i, r in enumerate(results[:3]):
        print(f"   [{i+1}] {r.get('title', 'N/A')[:50]}")
    
    print("\n=== 完成 ===")


if __name__ == "__main__":
    test_tavily_search()