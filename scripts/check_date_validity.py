import os
import pandas as pd

# 定义目录路径
qlib_export_dir = r"/instance/qlib_export"

# 检查目录是否存在
if not os.path.exists(qlib_export_dir):
    print(f"目录不存在: {qlib_export_dir}")
    exit(1)

# 统计信息
file_count = 0
invalid_date_count = 0
invalid_files = []

# 遍历所有 CSV 文件
for root, dirs, files in os.walk(qlib_export_dir):
    for file in files:
        if file.endswith('.csv'):
            file_path = os.path.join(root, file)
            file_count += 1
            
            try:
                # 读取 CSV 文件
                df = pd.read_csv(file_path)
                
                # 检查是否有日期列
                if 'date' in df.columns:
                    # 尝试将日期列转换为 datetime，使用 errors='coerce'
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                    
                    # 检查无效日期
                    invalid_dates = df[df['date'].isna()]
                    if len(invalid_dates) > 0:
                        invalid_date_count += len(invalid_dates)
                        if file_path not in invalid_files:
                            invalid_files.append(file_path)
                        print(f"文件 {file_path} 包含 {len(invalid_dates)} 个无效日期")
                            
            except Exception as e:
                print(f"读取文件 {file_path} 时出错: {e}")

# 输出统计结果
print(f"\n===== 严格检查结果 =====")
print(f"检查的文件数: {file_count}")
print(f"发现的无效日期数: {invalid_date_count}")
print(f"包含无效日期的文件数: {len(invalid_files)}")

if invalid_files:
    print("\n包含无效日期的文件:")
    for file_path in invalid_files[:5]:  # 只显示前5个
        print(f"- {file_path}")
    if len(invalid_files) > 5:
        print(f"... 还有 {len(invalid_files) - 5} 个文件")
else:
    print("\n所有文件中的日期都是有效的！")
