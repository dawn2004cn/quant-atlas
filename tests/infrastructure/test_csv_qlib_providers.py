"""测试CSV和Qlib历史数据providers"""

import sys
sys.path.insert(0, r"E:\project\workspace\myrepo\quant-atlas")

from dotenv import load_dotenv
load_dotenv(r"E:\project\workspace\myrepo\quant-atlas\.env")


def test_csv_provider_creation():
    """测试CSV Provider创建"""
    print("\n=== 测试 CSV Provider 创建 ===")
    from app.infrastructure.providers.csv_history_provider import CsvHistoryProvider, create_csv_history_provider

    provider = create_csv_history_provider(r"E:\data\csv", include_subdirs=True)
    print(f"Provider type: {type(provider)}")
    print(f"Root dir: {provider._root_dir}")
    print("OK")


def test_csv_get_history():
    """测试CSV获取历史数据"""
    print("\n=== 测试 CSV 获取历史数据 ===")
    from app.infrastructure.providers.csv_history_provider import CsvHistoryProvider
    from app.domain.enums import MarketCode

    provider = CsvHistoryProvider(r"E:\data\csv")

    history = provider.get_stock_history("600000", MarketCode.SH, start="2024-01-01", end="2024-12-31")
    print(f"获取到 {len(history)} 条数据")

    if history:
        print(f"首条: {history[0]}")
        print(f"末条: {history[-1]}")


def test_csv_list_available():
    """测试列出可用股票"""
    print("\n=== 测试 CSV 列出可用股票 ===")
    from app.infrastructure.providers.csv_history_provider import CsvHistoryProvider

    provider = CsvHistoryProvider(r"E:\data\csv")
    available = provider.list_available()
    print(f"可用市场: {list(available.keys())}")
    for market, symbols in available.items():
        print(f"  {market}: {len(symbols)} 只")


def test_qlib_provider_creation():
    """测试Qlib Provider创建"""
    print("\n=== 测试 Qlib Provider 创建 ===")
    from app.infrastructure.providers.qlib_history_provider import QlibHistoryProvider, create_qlib_history_provider

    provider = create_qlib_history_provider(symbol_prefix="SH.")
    print(f"Provider type: {type(provider)}")
    print(f"Symbol prefix: {provider._symbol_prefix}")
    print("OK")


def test_qlib_get_history():
    """测试Qlib获取历史数据"""
    print("\n=== 测试 Qlib 获取历史数据 ===")
    from app.infrastructure.providers.qlib_history_provider import QlibHistoryProvider

    provider = QlibHistoryProvider(symbol_prefix="SH.")

    history = provider.get_stock_history("600000", start="2024-01-01", end="2024-12-31")
    print(f"获取到 {len(history)} 条数据")

    if history:
        print(f"首条: {history[0]}")
    else:
        print("注意: qlib可能未初始化或无数据")


if __name__ == "__main__":
    print("=" * 50)
    print("测试 CSV/Qlib 历史数据 Providers")
    print("=" * 50)

    test_csv_provider_creation()
    test_csv_list_available()
    test_qlib_provider_creation()
    test_qlib_get_history()

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)