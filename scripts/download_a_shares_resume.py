import pandas as pd
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import threading
from data_fetchers import (
    fetch_from_yfinance, fetch_from_tencent, 
    fetch_from_sohu, ADATA_AVAILABLE
)

# ====================== 配置参数 ======================
CSV_INPUT = "stock_list.csv"  # 输入的6位股票代码列表
CSV_OUTPUT_DIR = "stock_data"  # 数据保存目录
START_DATE = "2023-01-01"  # 可改为更早，如 "2000-01-01"
END_DATE = datetime.today().strftime('%Y-%m-%d')

MAX_WORKERS = 12  # 线程数（推荐8-15，避免接口限流）
RETRY_TIMES = 3  # 每个接口重试次数

os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
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
        df = pd.read_csv(file_path, index_col=0, nrows=5)  # 只读前几行检查
        return len(df) > 10  # 至少有10条以上数据才算有效
    except:
        return False





def download_single_stock(code: str):
    """单只股票下载逻辑（带断点续传判断）"""
    output_file = os.path.join(CSV_OUTPUT_DIR, f"{code}.csv")

    # 如果已下载且有效，则跳过
    if is_already_downloaded(code):
        return code, True, "已存在（跳过）"

    sources = [
        ("yfinance", lambda code: fetch_from_yfinance(code, START_DATE, END_DATE)),
        ("tencent", lambda code: fetch_from_tencent(code, START_DATE, END_DATE)),
        ("sohu", lambda code: fetch_from_sohu(code, START_DATE, END_DATE))
    ]

    for source_name, fetch_func in sources:
        for attempt in range(RETRY_TIMES):
            try:
                df, err = fetch_func(code)
                if df is not None and not df.empty and len(df) > 20:
                    with file_lock:
                        df.to_csv(output_file, encoding='utf-8-sig')
                    return code, True, f"{source_name} 成功 ({len(df)} 条)"
            except:
                pass
            time.sleep(1.2)

    return code, False, "三个接口均失败"


# ====================== 主程序 ======================
def download_with_resume():
    all_codes = read_stock_codes(CSV_INPUT)

    # 过滤掉已下载的股票
    todo_codes = [code for code in all_codes if not is_already_downloaded(code)]

    print(f"总股票数量: {len(all_codes)} 只")
    print(f"已下载（跳过）: {len(all_codes) - len(todo_codes)} 只")
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