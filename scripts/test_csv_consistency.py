import os
import sys

# 添加当前目录到路径，以便导入模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from test_multithread_yfinance import verify_csv_data_consistency, CSV_OUTPUT_DIR

# 测试几个CSV文件的一致性
print("测试CSV数据一致性检查功能...")
print("=" * 80)

# 获取stock_data目录中的CSV文件
csv_files = [f for f in os.listdir(CSV_OUTPUT_DIR) if f.endswith('.csv')]

if not csv_files:
    print("没有找到CSV文件，请先运行下载脚本")
    sys.exit(1)

# 测试前10个文件
for i, csv_file in enumerate(csv_files[:10]):
    code = csv_file.replace('.csv', '')
    print(f"测试文件 {i+1}/{len(csv_files[:10])}: {csv_file}")
    is_consistent, need_redownload, message = verify_csv_data_consistency(code)
    status = "✓ 一致" if is_consistent else "✗ 不一致"
    print(f"  状态: {status}")
    print(f"  消息: {message}")
    print(f"  需要重新下载: {need_redownload}")
    print()

print("=" * 80)
print("测试完成！")
