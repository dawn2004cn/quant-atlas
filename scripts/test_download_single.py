import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from test_multithread_yfinance import download_single_stock, CSV_OUTPUT_DIR

# 测试下载一只股票
print("测试下载单只股票...")
print("=" * 80)

# 使用一个测试code
test_code = "000001"  # 平安银行

# 先删除已存在的文件（如果有）
output_file = os.path.join(CSV_OUTPUT_DIR, f"{test_code}.csv")
if os.path.exists(output_file):
    os.remove(output_file)
    print(f"已删除旧文件: {test_code}.csv")

# 下载股票数据
code, ok, msg = download_single_stock(test_code)

print(f"下载结果:")
print(f"  Code: {code}")
print(f"  成功: {ok}")
print(f"  消息: {msg}")

# 验证文件内容
if ok and os.path.exists(output_file):
    print("\n验证文件内容:")
    with open(output_file, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
        print(f"  总行数: {len(lines)}")
        print(f"  第一行(列名): {lines[0].strip()}")
        if len(lines) > 1:
            print(f"  第二行(数据): {lines[1].strip()}")
        
        # 检查是否包含code列
        if 'code' in lines[0]:
            print("  ✓ 文件包含code列")
        else:
            print("  ✗ 文件不包含code列")

print("=" * 80)
print("测试完成！")
