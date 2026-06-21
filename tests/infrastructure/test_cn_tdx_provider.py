"""测试 cn_tdx_provider"""

import sys
sys.path.insert(0, r"E:\project\workspace\myrepo\quant-atlas")

# 确保加载 .env 配置
from dotenv import load_dotenv
load_dotenv(r"E:\project\workspace\myrepo\quant-atlas\.env")

from app.infrastructure.providers.cn_tdx_provider import (
    TdxDataProvider,
    TdxHistoryProvider,
    TdxRealTimeProvider,
    create_tdx_provider,
)
from app.domain.enums import MarketCode
from app.core.runtime_config import get_runtime


def test_tdx_history():
    """测试历史数据读取"""
    print("\n=== 测试 TDX 历史数据 Provider ===")
    
    tdx_root = get_runtime("TDX_ROOT_PATH", "")
    provider = create_tdx_provider(tdx_root_path=tdx_root, use_qfq=True)
    
    # 获取所有股票
    symbols = provider.get_all_symbols(MarketCode.CN)
    print(f"获取到 {len(symbols)} 只股票")
    
    if symbols:
        # 取前3只测试
        for symbol in symbols[:3]:
            print(f"\n测试股票: {symbol}")
            hist = provider.get_stock_history(
                symbol=symbol[-6:],
                market=MarketCode.CN,
                start="2024-01-01",
                end="2024-12-31"
            )
            print(f"  历史数据条数: {len(hist)}")
            if hist:
                print(f"  首条: {hist[0]}")
                print(f"  末条: {hist[-1]}")
    else:
        print("未获取到股票代码，请检查 TDX_ROOT_PATH 配置")


def test_tdx_realtime():
    """测试实时行情"""
    print("\n=== 测试 TDX 实时行情 Provider ===")
    
    provider = create_tdx_provider()
    
    # 检查连接
    connected = provider.is_realtime_connected()
    print(f"TDX 连接状态: {connected}")
    
    if connected:
        # 获取实时行情
        quote = provider.get_quote("000001", MarketCode.CN)
        print(f"000001 实时行情: {quote}")
        
        # 批量获取
        quotes = provider.get_quotes(["000001", "600000"], MarketCode.CN)
        print(f"批量获取: {len(quotes)} 只")
        for q in quotes:
            print(f"  {q.get('symbol')}: {q.get('close')}")
    else:
        print("TDX 未连接，跳过实时行情测试")


def test_tdx_history_provider_direct():
    """直接测试 HistoryProvider"""
    print("\n=== 直接测试 TdxHistoryProvider ===")
    
    tdx_root = get_runtime("TDX_ROOT_PATH", "")
    hist_provider = TdxHistoryProvider(tdx_root_path=tdx_root, use_qfq=True)
    
    # 获取股票列表
    symbols = hist_provider.get_symbols_list(MarketCode.CN)
    print(f"股票数量: {len(symbols)}")
    
    if symbols:
        # 测试读取
        symbol = symbols[0][-6:]  # 取第一只股票代码
        market_prefix = symbols[0][:2]
        print(f"测试读取: {market_prefix}{symbol}")
        
        rows = hist_provider.get_stock_history(
            symbol=symbol,
            market=MarketCode.CN,
            start="2024-06-01",
            end="2024-06-30"
        )
        print(f"读取到 {len(rows)} 条数据")


if __name__ == "__main__":
    # 先测试历史数据
    test_tdx_history()
    
    # 再测试实时行情
    test_tdx_realtime()
    
    # 直接测试 HistoryProvider
    test_tdx_history_provider_direct()
    
    print("\n=== 测试完成 ===")