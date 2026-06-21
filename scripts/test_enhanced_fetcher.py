#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强型数据获取器
"""
import sys
sys.path.append('.')

from enhanced_data_fetcher import get_data_fetcher
from datetime import datetime, timedelta

print("=== 测试增强型数据获取器 ===")

# 获取数据获取器实例
fetcher = get_data_fetcher()

# 测试股票代码
test_codes = ['000001', '600519', '000858']
start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
end_date = datetime.now().strftime('%Y-%m-%d')

print(f"\n1. 测试获取单只股票数据")
print(f"股票代码: {test_codes[0]}")
print(f"时间范围: {start_date} ~ {end_date}")

try:
    df, source = fetcher.fetch_stock_data(test_codes[0], start_date, end_date)
    if df is not None and not df.empty:
        print(f"✅ 成功获取数据")
        print(f"数据源: {source}")
        print(f"数据条数: {len(df)}")
        print(f"数据列: {list(df.columns)}")
        print(f"\n前5条数据:")
        print(df.head())
    else:
        print(f"❌ 获取数据失败")
except Exception as e:
    print(f"❌ 获取数据失败: {e}")

print(f"\n2. 测试并发获取多只股票数据")
try:
    results = fetcher.fetch_multiple_stocks(test_codes, start_date, end_date)
    print(f"✅ 并发获取完成")
    for code, (df, source) in results.items():
        if df is not None and not df.empty:
            print(f"  {code}: {source} - {len(df)} 条数据")
        else:
            print(f"  {code}: 获取失败 - {source}")
except Exception as e:
    print(f"❌ 并发获取失败: {e}")

print(f"\n3. 测试获取实时数据")
try:
    realtime_data = fetcher.fetch_realtime_data(test_codes)
    if realtime_data:
        print(f"✅ 成功获取实时数据")
        print(f"获取到 {len(realtime_data)} 只股票数据")
        for code, data in realtime_data.items():
            print(f"  {code}: {data.get('name')} - 价格: {data.get('price')} - 涨跌: {data.get('change_pct'):+.2f}%")
    else:
        print(f"⚠️ 实时数据为空")
except Exception as e:
    print(f"❌ 获取实时数据失败: {e}")

print(f"\n4. 测试各个数据源")

# 测试腾讯接口
print(f"\n4.1 测试腾讯接口")
try:
    df, err = fetcher.fetch_from_tencent(test_codes[0], start_date, end_date)
    if df is not None and not df.empty:
        print(f"✅ 腾讯接口成功 - {len(df)} 条数据")
    else:
        print(f"⚠️ 腾讯接口失败: {err}")
except Exception as e:
    print(f"❌ 腾讯接口异常: {e}")

# 测试搜狐接口
print(f"\n4.2 测试搜狐接口")
try:
    df, err = fetcher.fetch_from_sohu(test_codes[0], start_date, end_date)
    if df is not None and not df.empty:
        print(f"✅ 搜狐接口成功 - {len(df)} 条数据")
    else:
        print(f"⚠️ 搜狐接口失败: {err}")
except Exception as e:
    print(f"❌ 搜狐接口异常: {e}")

# 测试yfinance接口
print(f"\n4.3 测试yfinance接口")
try:
    df, err = fetcher.fetch_from_yfinance(test_codes[0], start_date, end_date)
    if df is not None and not df.empty:
        print(f"✅ yfinance接口成功 - {len(df)} 条数据")
    else:
        print(f"⚠️ yfinance接口失败: {err}")
except Exception as e:
    print(f"❌ yfinance接口异常: {e}")

# 测试adata接口
print(f"\n4.4 测试adata接口")
try:
    df, err = fetcher.fetch_from_adata(test_codes[0], start_date, end_date)
    if df is not None and not df.empty:
        print(f"✅ adata接口成功 - {len(df)} 条数据")
    else:
        print(f"⚠️ adata接口失败: {err}")
except Exception as e:
    print(f"❌ adata接口异常: {e}")

print("\n=== 测试完成 ===")

# 关闭session
fetcher.close()
