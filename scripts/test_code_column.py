import os
import pandas as pd
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from test_multithread_yfinance import verify_csv_data_consistency, CSV_OUTPUT_DIR

print("测试code列验证功能...")
print("=" * 80)

# 创建一个测试CSV文件，包含code列
test_code = "999999"
test_file = os.path.join(CSV_OUTPUT_DIR, f"{test_code}.csv")

# 创建测试数据
test_data = pd.DataFrame({
    'code': [test_code] * 5,
    'open': [10.0, 10.5, 11.0, 10.8, 11.2],
    'high': [10.5, 11.0, 11.5, 11.2, 11.8],
    'low': [9.8, 10.2, 10.5, 10.5, 10.9],
    'close': [10.5, 10.8, 11.2, 11.0, 11.5],
    'volume': [1000000, 1200000, 1100000, 1300000, 1250000]
}, index=pd.date_range('2023-01-01', periods=5))

# 保存测试文件
test_data.to_csv(test_file, encoding='utf-8-sig')
print(f"✓ 创建测试文件: {test_code}.csv (包含code列)")

# 测试验证 - 应该通过
is_consistent, need_redownload, message = verify_csv_data_consistency(test_code)
print(f"\n测试1: code匹配")
print(f"  状态: {'✓ 通过' if is_consistent else '✗ 失败'}")
print(f"  消息: {message}")

# 创建一个code不匹配的测试文件
wrong_code = "888888"
wrong_file = os.path.join(CSV_OUTPUT_DIR, f"{wrong_code}.csv")

# 创建错误数据（code列与文件名不匹配）
wrong_data = pd.DataFrame({
    'code': ["123456"] * 5,  # 错误的code
    'open': [10.0, 10.5, 11.0, 10.8, 11.2],
    'high': [10.5, 11.0, 11.5, 11.2, 11.8],
    'low': [9.8, 10.2, 10.5, 10.5, 10.9],
    'close': [10.5, 10.8, 11.2, 11.0, 11.5],
    'volume': [1000000, 1200000, 1100000, 1300000, 1250000]
}, index=pd.date_range('2023-01-01', periods=5))

wrong_data.to_csv(wrong_file, encoding='utf-8-sig')
print(f"\n✓ 创建测试文件: {wrong_code}.csv (code列与文件名不匹配)")

# 测试验证 - 应该失败
is_consistent, need_redownload, message = verify_csv_data_consistency(wrong_code)
print(f"\n测试2: code不匹配")
print(f"  状态: {'✓ 通过' if is_consistent else '✗ 失败'}")
print(f"  消息: {message}")
print(f"  需要重新下载: {need_redownload}")

# 清理测试文件
os.remove(test_file)
os.remove(wrong_file)
print(f"\n✓ 清理测试文件")

print("=" * 80)
print("测试完成！")
