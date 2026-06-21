"""测试各类 Providers"""

import sys
sys.path.insert(0, r"E:\project\workspace\myrepo\quant-atlas")

from dotenv import load_dotenv
load_dotenv(r"E:\project\workspace\myrepo\quant-atlas\.env")

from app.domain.enums import MarketCode
from app.core.runtime_config import get_runtime


def test_market_data_provider():
    """测试 MarketDataProvider (跳过，有复杂依赖)"""
    print("\n=== 测试 MarketDataProvider ===")
    print("  跳过 (需要复杂依赖)")


def test_akshare_history():
    """测试 AkShare 历史数据"""
    print("\n=== 测试 AkShare 历史数据 ===")
    try:
        from app.infrastructure.providers.cn_akshare_history import fetch_cn_daily_qfq
        
        rows, status = fetch_cn_daily_qfq("000001", "2024-01-01", "2024-12-31")
        print(f"状态: {status}, 数据条数: {len(rows)}")
        if rows:
            print(f"首条: {rows[0]}")
    except Exception as e:
        print(f"失败: {e}")


def test_akshare_fundamentals():
    """测试 AkShare 基本面数据"""
    print("\n=== 测试 AkShare 基本面数据 ===")
    try:
        from app.infrastructure.providers.cn_akshare_fundamentals import CnAkShareFundamentalsProvider
        
        provider = CnAkShareFundamentalsProvider()
        print(f"Tushare 可用: {provider._tushare_available}")
        
        if provider._tushare_available:
            # 测试获取财务数据
            data = provider.fetch_financial_bundle("000001")
            print(f"数据类型: {type(data)}")
            if data:
                print(f"  symbol: {data.get('symbol')}")
                print(f"  source: {data.get('source')}")
                for key, val in data.items():
                    if isinstance(val, list):
                        print(f"  {key}: {len(val)} 条")
        else:
            print("  Tushare 不可用，使用 AkShare")
            data = provider.fetch_financial_bundle("000001")
            print(f"  symbol: {data.get('symbol')}")
            print(f"  source: {data.get('source')}")
    except Exception as e:
        print(f"失败: {e}")


def test_cn_industry_provider():
    """测试行业 Provider"""
    print("\n=== 测试行业 Provider ===")
    try:
        from app.infrastructure.providers.cn_industry_provider import CnIndustryProvider
        
        provider = CnIndustryProvider()
        # 先尝试从缓存获取
        industry_map = provider.get_industry_map(allow_fetch=False)
        print(f"缓存行业映射数量: {len(industry_map)}")
        
        if not industry_map:
            # 尝试获取新的
            print("尝试获取新数据...")
            industry_map = provider.get_industry_map(allow_fetch=True)
            print(f"新获取行业映射数量: {len(industry_map)}")
        
        if industry_map:
            items = list(industry_map.items())[:5]
            for code, industry in items:
                print(f"  {code}: {industry}")
    except Exception as e:
        print(f"失败: {e}")


def test_news_provider():
    """测试新闻 Provider"""
    print("\n=== 测试新闻 Provider ===")
    try:
        from app.infrastructure.providers.cn_portal_news import portal_headlines_cn, filter_headlines_for_symbol
        
        # 获取全部新闻
        all_news = portal_headlines_cn(limit_per_source=10)
        print(f"新闻总数: {len(all_news)}")
        if all_news:
            print(f"示例: {all_news[0]}")
        
        # 过滤特定股票新闻
        filtered = filter_headlines_for_symbol(all_news, "000001")
        print(f"000001 相关新闻: {len(filtered)}")
    except Exception as e:
        print(f"失败: {e}")


def test_indicators():
    """测试指标计算"""
    print("\n=== 测试指标计算 ===")
    try:
        from app.infrastructure.providers.indicators import TaIndicatorProvider
        
        provider = TaIndicatorProvider()
        
        # 构造测试数据 (至少需要 20 条以计算 MA20)
        history = [
            {"date": f"2024-01-{i+1:02d}", "open": 10+i, "high": 12+i, "low": 9+i, "close": 11+i, "volume": 1000}
            for i in range(30)
        ]
        
        result = provider.calculate(history)
        print(f"计算指标数量: {len(result)}")
        for k, v in list(result.items())[:5]:
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"失败: {e}")


def test_tdx_file_adapter():
    """测试 TDX 文件适配器"""
    print("\n=== 测试 TDX 文件适配器 ===")
    try:
        from app.infrastructure.providers.tdx_file_adapter import TDXFileHistoryAdapter
        
        tdx_root = get_runtime("TDX_ROOT_PATH", "")
        adapter = TDXFileHistoryAdapter(tdx_root)
        
        symbols = adapter.get_symbols_list(MarketCode.CN)
        print(f"股票数量: {len(symbols)}")
        
        if symbols:
            # 测试读取
            symbol = symbols[0][-6:]
            hist = adapter.get_stock_history(symbol, MarketCode.CN, "2024-01-01", "2024-06-30")
            print(f"读取 {symbol}: {len(hist)} 条")
    except Exception as e:
        print(f"失败: {e}")


def test_market_history_fetcher():
    """测试 MarketHistoryFetcher (跳过，导入问题)"""
    print("\n=== 测试 MarketHistoryFetcher ===")
    print("  跳过 (需要包内导入)")


def test_cn_em_industry_map():
    """测试行业地图"""
    print("\n=== 测试行业地图 ===")
    try:
        from app.infrastructure.providers.cn_em_industry_map import get_cn_industry_map_cached
        
        # 尝试获取新的行业地图
        industry_map = get_cn_industry_map_cached(allow_fetch=True)
        print(f"行业映射数量: {len(industry_map)}")
        if industry_map:
            items = list(industry_map.items())[:5]
            for code, industry in items:
                print(f"  {code}: {industry}")
    except Exception as e:
        print(f"失败: {e}")


def test_cn_tdx_provider():
    """测试 TDX Provider"""
    print("\n=== 测试 TDX Provider ===")
    try:
        from app.infrastructure.providers.cn_tdx_provider import create_tdx_provider
        from app.domain.enums import MarketCode
        
        provider = create_tdx_provider()
        if provider is None:
            print("  TDX 不可用 (未配置 TDX_ROOT_PATH)")
            return
            
        print(f"  TDX Provider 初始化成功")
        
        # 获取股票列表
        symbols = provider.get_all_symbols(MarketCode.CN)
        print(f"  股票数量: {len(symbols)}")
        
        if symbols:
            # 测试读取一只股票
            test_code = symbols[0][-6:]
            history = provider.get_stock_history(test_code, limit=5)
            print(f"  读取 {test_code}: {len(history)} 条")
            if history:
                print(f"    首条: {history[0]}")
    except Exception as e:
        print(f"失败: {e}")


def test_cn_xueqiu_news():
    """测试雪球新闻 Provider"""
    print("\n=== 测试雪球新闻 Provider ===")
    try:
        from app.infrastructure.providers.cn_xueqiu_news import XueqiuNewsProvider
        
        provider = XueqiuNewsProvider()
        # 雪球提供的是用户时间线/帖子，不是股票新闻
        news = provider.get_user_timeline(limit=5)
        print(f"  获取新闻: {len(news)} 条")
        if news:
            print(f"  示例: {news[0].get('title', 'N/A')[:50]}")
    except Exception as e:
        print(f"失败: {e}")


def test_cn_jqka_news():
    """测试同花顺新闻 Provider"""
    print("\n=== 测试同花顺新闻 Provider ===")
    try:
        from app.infrastructure.providers.cn_jqka_news import JqkaNewsProvider
        
        provider = JqkaNewsProvider()
        news = provider.get_stock_news("000001", limit=5)
        print(f"  获取新闻: {len(news)} 条")
        if news:
            print(f"  示例: {news[0].get('title', 'N/A')[:50]}")
    except Exception as e:
        print(f"失败: {e}")


def test_msn_market_index():
    """测试 MSN 指数 Provider"""
    print("\n=== 测试 MSN 指数 Provider ===")
    try:
        from app.infrastructure.providers.msn_market_index import MsnMarketIndexProvider
        
        provider = MsnMarketIndexProvider()
        # 使用MSN内部ID (adfh77=上证, adg1m7=深证)
        data = provider.get_quotes(["adfh77", "adg1m7"])
        print(f"  获取指数数据: {len(data)} 条")
        if data:
            print(f"  示例: {data[0].get('symbol')} {data[0].get('price')}")
    except Exception as e:
        print(f"失败: {e}")


def test_web_search():
    """测试网页搜索 Provider"""
    print("\n=== 测试网页搜索 Provider ===")
    try:
        from app.infrastructure.providers.web_search import MultiEngineSearchProvider
        
        provider = MultiEngineSearchProvider()
        results = provider.search("A股市场", max_results=3)
        print(f"  搜索结果: {len(results)} 条")
        if results:
            print(f"  示例: {results[0].get('title', 'N/A')[:50]}")
    except Exception as e:
        print(f"失败: {e}")


def test_rust_indicators():
    """测试 Rust 指标 Provider"""
    print("\n=== 测试 Rust 指标 Provider ===")
    try:
        from app.infrastructure.providers.rust_indicators import RustIndicatorProvider
        
        provider = RustIndicatorProvider()
        
        # 构造测试数据
        history = [
            {"date": f"2024-01-{i+1:02d}", "open": 10+i, "high": 12+i, "low": 9+i, "close": 11+i, "volume": 1000}
            for i in range(30)
        ]
        
        result = provider.calculate(history)
        print(f"  计算指标数量: {len(result)}")
        if result:
            print(f"  指标: {list(result.keys())[:5]}")
    except Exception as e:
        print(f"失败: {e}")


def test_csv_history_provider():
    """测试 CSV 历史数据 Provider (跳过，需要数据文件)"""
    print("\n=== 测试 CSV 历史数据 Provider ===")
    print("  跳过 (需要 ./data 目录下有 CSV 文件)")


def test_market_data_fallback():
    """测试市场数据 Fallback (跳过，需要主 Provider)"""
    print("\n=== 测试市场数据 Fallback ===")
    print("  跳过 (需要 primary_provider 参数)")


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试各类 Providers - 完整版")
    print("=" * 60)
    
    test_market_data_provider()
    test_akshare_history()
    test_akshare_fundamentals()
    test_cn_industry_provider()
    test_news_provider()
    test_indicators()
    test_tdx_file_adapter()
    test_market_history_fetcher()
    test_cn_em_industry_map()
    test_cn_tdx_provider()
    test_cn_xueqiu_news()
    test_cn_jqka_news()
    test_msn_market_index()
    test_web_search()
    test_rust_indicators()
    test_csv_history_provider()
    test_market_data_fallback()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)