import pandas as pd
import os
import time
import yfinance as yf
import requests
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import threading
from data_fetchers import (
    fetch_from_yfinance, fetch_from_tencent, 
    fetch_from_sohu, fetch_from_adata,
    ADATA_AVAILABLE
)
"""
更新全市场A股历史数据从2023-01-01到stock_history_data目录下的csv文件
用于各种数据计算
"""
# 显示adata库状态
if not ADATA_AVAILABLE:
    print("警告: adata 库未安装，将不使用 adata 数据源")

# ====================== 配置参数 ======================
CSV_INPUT = "stock_code.csv"  # 输入的6位股票代码列表
#CSV_OUTPUT_DIR = "stock_history_data"  # 数据保存目录
CSV_OUTPUT_DIR = "../data_caches"  # 数据保存目录
START_DATE = "2020-01-01"  # 可改为更早，如 "2000-01-01"
END_DATE = datetime.today().strftime('%Y-%m-%d')

MAX_WORKERS = 12  # 线程数（推荐8-15，避免接口限流）
RETRY_TIMES = 3  # 每个接口重试次数

# 创建输出目录，添加异常处理
try:
    os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
except Exception as e:
    print(f"创建目录失败: {e}")
    raise

file_lock = threading.Lock()


# ====================== 辅助函数 ======================
def read_stock_codes(csv_file):
    df = pd.read_csv(csv_file)
    possible_cols = ['code', 'Code', 'symbol', '股票代码', '代码']
    code_col = next((col for col in possible_cols if col in df.columns), None)
    if not code_col:
        raise ValueError(f"未找到代码列，CSV列名为: {df.columns.tolist()}")

    codes = df[code_col].astype(str).str.strip().str.zfill(6)
    print(f"从 {csv_file} 中读取到 {len(codes)} 只 A 股代码")
    return codes.tolist()


# ====================== 检查是否已下载（断点续传核心） ======================
def is_already_downloaded(code: str) -> bool:
    """判断该股票是否已成功下载（文件存在且非空）"""
    file_path = os.path.join(CSV_OUTPUT_DIR, f"{code}.csv")
    if not os.path.exists(file_path):
        return False
    try:
        # 检查文件大小，确保文件不为空
        if os.path.getsize(file_path) == 0:
            return False
        # 尝试读取文件，检查是否有数据
        df = pd.read_csv(file_path, index_col=0, nrows=5)
        return len(df) > 0  # 只要有数据就算有效
    except FileNotFoundError:
        return False
    except PermissionError as e:
        print(f"权限错误，无法访问文件 {code}.csv: {e}")
        return False
    except pd.errors.EmptyDataError:
        return False
    except Exception as e:
        # 处理磁盘 I/O 错误
        if 'disk I/O error' in str(e):
            print(f"磁盘 I/O 错误，无法访问文件 {code}.csv: {e}")
            return False
        print(f"检查文件 {code}.csv 时出错: {e}")
        return False

def download_single_stock(code: str):
    """单只股票下载逻辑（带断点续传判断）"""
    # 每个线程使用自己的局部变量，避免竞态条件
    local_code = str(code).strip()
    output_file = os.path.join(CSV_OUTPUT_DIR, f"{local_code}.csv")

    # 如果已下载且有效，则跳过
    if is_already_downloaded(local_code):
        return local_code, True, "已存在（跳过）"

    sources = [
        ("adata", lambda code: fetch_from_adata(code, START_DATE, END_DATE)),
        ("tencent", lambda code: fetch_from_tencent(code, START_DATE, END_DATE)),
        ("sohu", lambda code: fetch_from_sohu(code, START_DATE, END_DATE)),
        ("yfinance", lambda code: fetch_from_yfinance(code, START_DATE, END_DATE))
    ]

    # 尝试从所有接口获取数据
    results = []
    for source_name, fetch_func in sources:
        for attempt in range(RETRY_TIMES):
            try:
                df, err = fetch_func(local_code)
                if df is not None and not df.empty and len(df) > 20:
                    # 验证数据是否正确：检查第一行数据的索引（日期）是否合理
                    try:
                        first_date = df.index[0]
                        if pd.to_datetime(first_date) >= pd.to_datetime(START_DATE):
                            results.append((source_name, df))
                            break
                    except:
                        # 如果日期验证失败，仍然添加结果
                        results.append((source_name, df))
                        break
            except Exception as e:
                print(f"  {local_code} - {source_name} 尝试 {attempt+1} 失败: {str(e)[:50]}")
            time.sleep(1.2)

    # 如果有多个接口成功，选择数据量最多的
    if results:
        # 按数据量排序
        results.sort(key=lambda x: len(x[1]), reverse=True)
        best_source, best_df = results[0]
        
        # 在保存前再次检查文件是否已存在（双重检查锁定模式）
        if is_already_downloaded(local_code):
            return local_code, True, "已存在（跳过）"
        
        # 使用线程锁保护文件写入操作
        with file_lock:
            # 再次检查，防止在获取锁期间其他线程已写入
            if is_already_downloaded(local_code):
                return local_code, True, "已存在（跳过）"
            
            try:
                # 在DataFrame中添加code信息作为元数据（第一列）
                best_df_with_code = best_df.copy()
                best_df_with_code.insert(0, 'code', local_code)
                
                # 确保输出目录存在
                try:
                    os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
                except Exception as dir_error:
                    return local_code, False, f"创建目录失败: {dir_error[:50]}"
                
                best_df_with_code.to_csv(output_file, encoding='utf-8-sig')
                
                # 验证保存的文件
                verify_df = pd.read_csv(output_file, index_col=0, nrows=5)
                if len(verify_df) == 0:
                    return local_code, False, "保存后验证失败：文件为空"
                
                # 验证code列是否存在且正确
                if 'code' not in verify_df.columns:
                    return local_code, False, "保存后验证失败：缺少code列"
                
                if str(verify_df['code'].iloc[0]) != local_code:
                    return local_code, False, f"保存后验证失败：code不匹配 {verify_df['code'].iloc[0]} != {local_code}"
                
                # 验证数据一致性
                if len(results) > 1:
                    best_len = len(best_df)
                    consistent = True
                    for source_name, df in results[1:]:
                        if len(df) < best_len * 0.9:
                            consistent = False
                            break
                    
                    if consistent:
                        return local_code, True, f"{best_source} 成功 ({len(best_df)} 条) - 数据一致"
                    else:
                        return local_code, True, f"{best_source} 成功 ({len(best_df)} 条) - 数据可能不一致"
                else:
                    return local_code, True, f"{best_source} 成功 ({len(best_df)} 条)"
            except FileNotFoundError:
                return local_code, False, "文件不存在"
            except PermissionError as e:
                return local_code, False, f"权限错误: {e[:50]}"
            except pd.errors.EmptyDataError:
                return local_code, False, "文件为空或格式错误"
            except pd.errors.ParserError:
                return local_code, False, "文件解析错误"
            except Exception as e:
                # 处理磁盘 I/O 错误
                if 'disk I/O error' in str(e):
                    return local_code, False, f"磁盘 I/O 错误: {str(e)[:50]}"
                return local_code, False, f"保存文件失败: {str(e)[:50]}"

    return local_code, False, "三个接口均失败"


# ====================== 主程序 ======================
def download_with_resume():
    all_codes = read_stock_codes(CSV_INPUT)

    # 第一步：验证已下载的文件数据一致性
    # 过滤掉已下载的股票
    todo_codes = [code for code in all_codes if not is_already_downloaded(code)]
    valid_codes = [code for code in all_codes if is_already_downloaded(code)]

    print("=" * 80)
    print("开始下载数据...")
    print("=" * 80)
    print(f"总股票数量: {len(all_codes)} 只")
    print(f"已下载（跳过）: {len(valid_codes)} 只")
    print(f"本次需要下载: {len(todo_codes)} 只")
    print(f"时间范围: {START_DATE} ~ {END_DATE} | 线程数: {MAX_WORKERS}\n")

    if not todo_codes:
        print("所有股票均已下载完成！无需重复下载。")
        return

    success = 0
    failed = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_code = {executor.submit(download_single_stock, c): c for c in todo_codes}

        for future in tqdm(as_completed(future_to_code), total=len(todo_codes), desc="下载进度"):
            code, ok, msg = future.result()
            if ok:
                success += 1
            else:
                failed.append((code, msg))

    print("\n" + "=" * 80)
    print(f"本次下载完成！新增成功: {success} 只 | 失败: {len(failed)} 只")
    print(f"数据保存目录: {CSV_OUTPUT_DIR}")

    if failed:
        print("\n本次失败股票（前15条）:")
        for c, m in failed[:15]:
            print(f"  {c} → {m}")
        pd.DataFrame(failed, columns=["code", "error"]).to_csv("download_failed.csv", index=False, encoding='utf-8-sig')
        print("失败列表已保存到 → download_failed.csv（可后续重试）")

    print("\n断点续传任务结束！下次运行会自动跳过已下载的股票。")


if __name__ == "__main__":
    # 首次运行安装依赖：
    # pip install yfinance pandas requests tqdm
    download_with_resume()