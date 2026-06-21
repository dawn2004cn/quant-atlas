import yfinance as yf
import pandas as pd
from datetime import datetime
import os
from tqdm import tqdm
import time

# ====================== 配置参数 ======================
CSV_INPUT = "stock_list.csv"  # 输入的股票代码文件
CSV_OUTPUT_DIR = "../scripts/stock_history"  # 输出文件夹
START_DATE = "2023-01-01"  # 开始日期
END_DATE = datetime.today().strftime('%Y-%m-%d')  # 到今天

# 如果输出文件夹不存在则创建
os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)


# ====================== 读取股票代码 ======================
def read_stock_codes(csv_file):
    """从CSV读取股票代码，支持多种常见格式"""
    df = pd.read_csv(csv_file)

    # 自动识别代码列（常见列名）
    code_column = None
    possible_names = ['code', 'Code', 'symbol', 'Symbol', 'ticker', 'Ticker', '股票代码', '代码']

    for col in possible_names:
        if col in df.columns:
            code_column = col
            break

    if code_column is None:
        raise ValueError(f"无法找到股票代码列！CSV文件包含的列为: {df.columns.tolist()}")

    # 提取代码并清理
    codes = df[code_column].astype(str).str.strip()
    codes = codes.str.zfill(6)  # 补齐6位

    print(f"从 {csv_file} 中读取到 {len(codes)} 只股票代码")
    return codes.tolist()


# ====================== 自动添加后缀 ======================
def get_yahoo_ticker(code: str) -> str:
    """将6位A股代码转为 yfinance 可用的 ticker"""
    code = str(code).zfill(6)
    if code.startswith(('6', '9')):  # 沪市
        return f"{code}.SS"
    else:  # 深市
        return f"{code}.SZ"


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
        print(f"检查文件 {code}.csv 时出错: {e}")
        return False

# ====================== 主程序 ======================
def download_a_shares():
    codes = read_stock_codes(CSV_INPUT)

    # 第二步：过滤掉已下载且数据有效的股票
    todo_codes = [code for code in codes if not is_already_downloaded(code)]
    print(f"总股票数量: {len(codes)} 只")
    print(f"本次需要下载: {len(todo_codes)} 只")
    print(f"时间范围: {START_DATE} 到 {END_DATE}")

    success_count = 0
    failed_list = []

    for code in tqdm(todo_codes, desc="下载进度"):
        try:
            yahoo_ticker = get_yahoo_ticker(code)

            # 下载数据
            df = yf.download(
                tickers=yahoo_ticker,
                start=START_DATE,
                end=END_DATE,
                interval="1d",
                auto_adjust=True,  # 自动复权（推荐）
                progress=False,
                threads=True
            )

            if df.empty:
                print(f"⚠️  {code} 无数据")
                failed_list.append(code)
                continue

            # 保存为 CSV
            output_file = os.path.join(CSV_OUTPUT_DIR, f"{code}.csv")
            df.to_csv(output_file, encoding='utf-8-sig')

            success_count += 1

            # 避免请求过快被封（可选）
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ 下载失败 {code}: {e}")
            failed_list.append(code)

    # ====================== 下载总结 ======================
    print("\n" + "=" * 60)
    print("下载完成！")
    print(f"成功下载: {success_count} 只")
    print(f"失败/无数据: {len(failed_list)} 只")

    if failed_list:
        print("\n失败股票代码:")
        print(failed_list)

        # 保存失败列表
        pd.DataFrame({"failed_code": failed_list}).to_csv("download_failed.csv", index=False)


if __name__ == "__main__":
    download_a_shares()