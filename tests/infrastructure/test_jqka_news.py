"""测试同花顺新闻 Provider"""

import sys
sys.path.insert(0, r"E:\project\workspace\myrepo\quant-atlas")

from dotenv import load_dotenv
load_dotenv(r"E:\project\workspace\myrepo\quant-atlas\.env")


def test_jqka_realtime_news():
    """测试同花顺实时新闻"""
    print("\n=== 测试同花顺实时新闻 ===")
    from app.infrastructure.providers.cn_jqka_news import fetch_10jqka_realtime_news
    
    # 测试全部新闻
    news = fetch_10jqka_realtime_news(limit=10)
    print(f"实时新闻数量: {len(news)}")
    if news:
        for i, n in enumerate(news[:3]):
            title = n.get('title', '')[:50]
            try:
                print(f"  {i+1}. {title}")
            except:
                print(f"  {i+1}. [标题编码问题]")
            print(f"     URL: {n.get('url', '')}")
            print(f"     时间: {n.get('published_at', '')}")


def test_jqka_stock_news():
    """测试同花顺个股新闻"""
    print("\n=== 测试同花顺个股新闻 ===")
    from app.infrastructure.providers.cn_jqka_news import fetch_10jqka_stock_news
    
    # 测试 000001 个股新闻
    news = fetch_10jqka_stock_news("000001", limit=10)
    print(f"000001 新闻数量: {len(news)}")
    if news:
        for i, n in enumerate(news[:3]):
            title = n.get('title', '')[:50]
            try:
                print(f"  {i+1}. {title}")
            except:
                print(f"  {i+1}. [标题编码问题]")
            print(f"     URL: {n.get('url', '')}")


def test_jqka_provider():
    """测试 JqkaNewsProvider 类"""
    print("\n=== 测试 JqkaNewsProvider ===")
    from app.infrastructure.providers.cn_jqka_news import JqkaNewsProvider
    
    provider = JqkaNewsProvider()
    
    # 测试实时新闻
    realtime = provider.get_realtime_news(limit=5)
    print(f"实时新闻: {len(realtime)} 条")
    
    # 测试个股新闻
    stock = provider.get_stock_news("600000", limit=5)
    print(f"600000 新闻: {len(stock)} 条")
    
    # 测试合并
    all_news = provider.get_all_news(realtime_limit=5, stock_symbol="000001", stock_limit=5)
    print(f"合并新闻: {len(all_news)} 条")


def test_jqka_categories():
    """测试不同分类"""
    print("\n=== 测试不同分类 ===")
    from app.infrastructure.providers.cn_jqka_news import fetch_10jqka_realtime_news
    
    categories = ["all", "cj", "gg", "zx", "cy"]
    for cat in categories:
        news = fetch_10jqka_realtime_news(limit=5, category=cat)
        print(f"  {cat}: {len(news)} 条")


if __name__ == "__main__":
    print("=" * 50)
    print("测试同花顺新闻 Provider")
    print("=" * 50)
    
    test_jqka_realtime_news()
    test_jqka_stock_news()
    test_jqka_provider()
    test_jqka_categories()
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)