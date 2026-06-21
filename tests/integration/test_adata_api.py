import adata
import pandas as pd
from datetime import datetime
import time

# 测试股票代码
TEST_CODES = ["000001", "600519", "600000", "300001"]

def test_all_code():
    """测试获取所有A股股票代码"""
    print("\n=== 测试获取所有A股股票代码 ===")
    try:
        start_time = time.time()
        df = adata.stock.info.all_code()
        end_time = time.time()
        print(f"  ✓ 成功获取所有A股股票代码")
        print(f"  数据条数: {len(df)}")
        print(f"  耗时: {end_time - start_time:.2f}s")
        print(f"  列名: {df.columns.tolist()}")
        print(f"  前5行数据:")
        print(df.head())
        return True
    except Exception as e:
        print(f"  ✗ 失败: {str(e)}")
        return False

def test_kline_data():
    """测试获取K线数据"""
    print("\n=== 测试获取K线数据 ===")
    for code in TEST_CODES:
        try:
            start_time = time.time()
            df = adata.stock.market.get_market(
                stock_code=code,
                k_type=1,           # 1=daily, 2=weekly, 3=monthly
                start_date='2023-01-01',
                adjust_type=1        # 0=unadjusted, 1=forward, 2=backward
            )
            end_time = time.time()
            if not df.empty and len(df) > 10:
                print(f"  ✓ {code}: 成功，数据条数: {len(df)}, 耗时: {end_time - start_time:.2f}s")
                print(f"    列名: {df.columns.tolist()}")
                print(f"    数据范围: {df['trade_date'].min()} ~ {df['trade_date'].max()}")
            else:
                print(f"  ✗ {code}: 失败，数据不足")
        except Exception as e:
            print(f"  ✗ {code}: 异常 - {str(e)[:50]}")
        time.sleep(0.5)  # 避免请求过快

def test_realtime_quotes():
    """测试获取实时行情数据"""
    print("\n=== 测试获取实时行情数据 ===")
    try:
        start_time = time.time()
        df = adata.stock.market.list_market_current(
            code_list=TEST_CODES
        )
        end_time = time.time()
        if not df.empty:
            print(f"  ✓ 成功获取实时行情数据")
            print(f"  数据条数: {len(df)}")
            print(f"  耗时: {end_time - start_time:.2f}s")
            print(f"  列名: {df.columns.tolist()}")
            print(f"  数据预览:")
            print(df)
        else:
            print(f"  ✗ 失败，数据为空")
    except Exception as e:
        print(f"  ✗ 异常 - {str(e)}")

def test_data_integrity():
    """测试数据完整性"""
    print("\n=== 测试数据完整性 ===")
    for code in TEST_CODES:
        try:
            df = adata.stock.market.get_market(
                stock_code=code,
                k_type=1,
                start_date='2023-01-01',
                adjust_type=1
            )
            
            # 检查必要的列是否存在
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"  ✗ {code}: 缺少必要的列: {missing_columns}")
                continue
            
            # 检查数据是否有缺失值
            null_count = df[required_columns].isnull().sum().sum()
            
            # 检查数据是否合理
            latest_close = df['close'].iloc[-1]
            if latest_close <= 0 or latest_close > 10000:
                print(f"  ✗ {code}: 收盘价异常: {latest_close}")
                continue
            
            print(f"  ✓ {code}: 数据完整性检查通过")
            print(f"    数据条数: {len(df)}")
            print(f"    缺失值数量: {null_count}")
            print(f"    最新收盘价: {latest_close}")
            
        except Exception as e:
            print(f"  ✗ {code}: 异常 - {str(e)[:50]}")
        time.sleep(0.5)

if __name__ == "__main__":
    print("开始测试 adata 接口可用性...")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试获取所有A股股票代码
    all_code_success = test_all_code()
    
    # 测试获取K线数据
    test_kline_data()
    
    # 测试获取实时行情数据
    test_realtime_quotes()
    
    # 测试数据完整性
    test_data_integrity()
    
    print("\n测试完成！")
    
    # 总结
    print("\n=== 测试结果总结 ===")
    if all_code_success:
        print("✓ adata 接口可用，建议添加到项目中")
    else:
        print("✗ adata 接口存在问题，需要进一步检查")
