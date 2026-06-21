import os
import sys
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from tqdm import tqdm

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_SCRIPTS_ROOT.parent), str(_SCRIPTS_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)
from data_fetchers import (
    fetch_from_adata, fetch_from_yfinance, fetch_from_tencent, fetch_from_sohu, fetch_from_akshare,
    ADATA_AVAILABLE, AKSHARE_AVAILABLE
)
'''
更新今日的数据
python update_daily_latest.py
更新某一天的数据
python update_daily_latest.py --date 2026-04-05
'''
# 显示adata库状态
if not ADATA_AVAILABLE:
    print("警告: adata 库未安装，将不使用 adata 数据源")

# ====================== 配置 ======================
CSV_INPUT = "Astock20260405.xls"  # 你的股票代码列表
OUTPUT_DIR = "daily_latest"  # 每日文件存放目录
STOCK_HISTORY_DIR = "data_caches"  # 历史数据目录
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STOCK_HISTORY_DIR, exist_ok=True)

MAX_WORKERS = 12  # 线程数
RETRY_TIMES = 3  # 重试次数

file_lock = threading.Lock()  # 文件写入锁


# ====================== 断电续传功能 ======================
def is_already_updated(code: str, target_date: str) -> bool:
    """判断该股票在指定日期是否已成功更新（检查daily_latest目录中的汇总文件）"""
    daily_file = os.path.join(OUTPUT_DIR, f"daily_latest_{target_date}.csv")
    
    if not os.path.exists(daily_file):
        return False
    try:
        # 检查文件大小，确保文件不为空
        if os.path.getsize(daily_file) == 0:
            return False
        # 尝试读取文件，检查是否包含该股票的数据
        df = pd.read_csv(daily_file)
        if len(df) == 0:
            return False
        # 检查是否包含该股票的代码
        if 'code' not in df.columns:
            return False
        # 检查该股票是否已在指定日期的汇总文件中
        return code in df['code'].astype(str).str.strip().str.zfill(6).tolist()
    except FileNotFoundError:
        return False
    except PermissionError as e:
        print(f"权限错误，无法访问文件 {daily_file}: {e}")
        return False
    except pd.errors.EmptyDataError:
        return False
    except Exception as e:
        # 处理磁盘 I/O 错误
        if 'disk I/O error' in str(e):
            print(f"磁盘 I/O 错误，无法访问文件 {daily_file}: {e}")
            return False
        print(f"检查文件 {daily_file} 时出错: {e}")
        return False


# ====================== 辅助函数 ======================


def read_stock_codes(csv_file):
    """
    从文件中读取股票代码
    支持 CSV 和 Excel 文件格式
    """
    # 尝试使用不同的方法读取文件
    try:
        # 首先尝试作为制表符分隔的文件读取
        print(f"尝试作为制表符分隔的文件读取 {csv_file}...")
        df = pd.read_csv(csv_file, sep='\t', encoding='utf-8')
        print("成功作为制表符分隔的文件读取")
    except:
        try:
            # 尝试使用 gbk 编码读取制表符分隔的文件
            print(f"尝试使用 gbk 编码读取制表符分隔的文件 {csv_file}...")
            df = pd.read_csv(csv_file, sep='\t', encoding='gbk')
            print("成功使用 gbk 编码读取制表符分隔的文件")
        except:
            try:
                # 尝试作为普通 CSV 文件读取
                print(f"尝试作为 CSV 文件读取 {csv_file}...")
                df = pd.read_csv(csv_file, encoding='utf-8')
                print("成功作为 CSV 文件读取")
            except:
                try:
                    # 尝试使用 gbk 编码读取 CSV 文件
                    print(f"尝试使用 gbk 编码读取 CSV 文件 {csv_file}...")
                    df = pd.read_csv(csv_file, encoding='gbk')
                    print("成功使用 gbk 编码读取 CSV 文件")
                except:
                    try:
                        # 尝试作为 Excel 文件读取
                        print(f"尝试作为 Excel 文件读取 {csv_file}...")
                        df = pd.read_excel(csv_file)
                        print("成功作为 Excel 文件读取")
                    except Exception as e:
                        print(f"读取文件失败: {e}")
                        raise
    
    # 查找代码列
    possible_code_cols = ['code', 'Code', 'symbol', '股票代码', '代码']
    code_col = next((col for col in possible_code_cols if col in df.columns), None)
    if not code_col:
        raise ValueError(f"未找到代码列，文件列名为: {df.columns.tolist()}")

    # 处理代码，去除引号、等号和反引号
    codes = []
    for _, row in df.iterrows():
        code = str(row[code_col]).strip().strip('"').strip("'").strip('=').strip('"').zfill(6)
        print("code:" + code)
        codes.append(code)
    
    print(f"从 {csv_file} 中读取到 {len(codes)} 只 A 股代码")
    return codes


# ====================== 五个接口获取最新交易日数据 ======================
def fetch_latest_yfinance(code: str, end_date: str) -> Tuple[Optional[pd.DataFrame], str]:
    try:
        # 获取最近5天的数据，然后取最后一条
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - pd.Timedelta(days=10)).strftime('%Y-%m-%d')
        df, err = fetch_from_yfinance(code, start_date, end_date)
        if df is not None and not df.empty:
            return df.iloc[-1:].copy(), "yfinance"
        return None, f"yfinance 无数据: {err}"
    except Exception as e:
        return None, f"yfinance 异常: {str(e)[:60]}"


def fetch_latest_tencent(code: str, end_date: str) -> Tuple[Optional[pd.DataFrame], str]:
    try:
        # 获取最近5天的数据，然后取最后一条
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - pd.Timedelta(days=10)).strftime('%Y-%m-%d')
        df, err = fetch_from_tencent(code, start_date, end_date)
        if df is not None and not df.empty:
            return df.iloc[-1:].copy(), "tencent"
        return None, f"tencent 无数据: {err}"
    except Exception as e:
        return None, f"tencent 异常: {str(e)[:60]}"


def fetch_latest_sohu(code: str, end_date: str) -> Tuple[Optional[pd.DataFrame], str]:
    try:
        # 获取最近5天的数据，然后取最后一条
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - pd.Timedelta(days=10)).strftime('%Y-%m-%d')
        df, err = fetch_from_sohu(code, start_date, end_date)
        if df is not None and not df.empty:
            return df.iloc[-1:].copy(), "sohu"
        return None, f"sohu 无数据: {err}"
    except Exception as e:
        return None, f"sohu 异常: {str(e)[:60]}"


def fetch_latest_adata(code: str, end_date: str) -> Tuple[Optional[pd.DataFrame], str]:
    try:
        if not ADATA_AVAILABLE:
            return None, "adata 库未安装"
        
        # 获取最近5天的数据，然后取最后一条
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - pd.Timedelta(days=10)).strftime('%Y-%m-%d')
        df, err = fetch_from_adata(code, start_date, end_date)
        if df is not None and not df.empty:
            return df.iloc[-1:].copy(), "adata"
        return None, f"adata 无数据: {err}"
    except Exception as e:
        return None, f"adata 异常: {str(e)[:60]}"


def fetch_latest_akshare(code: str, end_date: str) -> Tuple[Optional[pd.DataFrame], str]:
    try:
        if not AKSHARE_AVAILABLE:
            return None, "akshare 库未安装"
        
        # 获取最近5天的数据，然后取最后一条
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - pd.Timedelta(days=10)).strftime('%Y-%m-%d')
        df, err = fetch_from_akshare(code, start_date, end_date)
        if df is not None and not df.empty:
            return df.iloc[-1:].copy(), "akshare"
        return None, f"akshare 无数据: {err}"
    except Exception as e:
        return None, f"akshare 异常: {str(e)[:60]}"


def get_latest_trading_day(code: str, target_date: str):
    """优先级：adata → akshare → yfinance → tencent → sohu，确保至少一种数据源成功"""
    sources = []
    if ADATA_AVAILABLE:
        sources.append((fetch_latest_adata, "adata"))
    if AKSHARE_AVAILABLE:
        sources.append((fetch_latest_akshare, "akshare"))
    sources.extend([(fetch_latest_yfinance, "yfinance"), (fetch_latest_tencent, "tencent"), (fetch_latest_sohu, "sohu")])
    
    # 存储所有数据源的结果
    results = []
    
    for fetch_func, source_name in sources:
        print(f"正在尝试 {source_name} 数据源获取 {code} {target_date} 数据...")
        for attempt in range(RETRY_TIMES):  # 重试3次
            try:
                print(f"  尝试 {attempt+1}/{RETRY_TIMES}")
                df, src = fetch_func(code, target_date)
                if df is not None and not df.empty:
                    # 检查数据日期是否与目标日期一致
                    latest_date = df.index[0].strftime('%Y-%m-%d')
                    if latest_date == target_date:
                        print(f"  ✅ {source_name} 数据源获取成功！")
                        return df, src
                    else:
                        print(f"  ⚠️ {source_name} 数据源日期不匹配: {latest_date} != {target_date}")
                        results.append((src, df))
                else:
                    results.append((src, df))
                    print(f"  ⚠️  {source_name} 数据源无数据")
            except Exception as e:
                error_msg = f"{source_name} 异常: {str(e)[:50]}"
                results.append((error_msg, None))
                print(f"  ❌ {error_msg}")
            time.sleep(0.8)
    
    # 再次检查所有结果，确保没有遗漏
    print(f"所有数据源尝试失败，再次检查结果...")
    for src, df in results:
        if df is not None and not df.empty:
            print(f"  ✅ 从之前的结果中找到有效数据: {src}")
            return df, src
    
    print(f"  ❌ 所有数据源均失败")
    return None, "全部失败"


def update_single_stock(code: str, target_date: str):
    """更新单只股票的指定日期数据（带断电续传）"""
    local_code = str(code).strip()
    stock_file = os.path.join(STOCK_HISTORY_DIR, f"{local_code}.csv")
    
    # 检查是否已经更新过
    if is_already_updated(code, target_date):
        return local_code, True, f"{target_date} 已更新（跳过）"
    
    # 获取指定日期的数据
    df_latest, source = get_latest_trading_day(local_code, target_date)
    
    if df_latest is None or df_latest.empty:
        return local_code, False, f"获取数据失败: {source}"
    
    try:
        # 读取历史数据
        if os.path.exists(stock_file):
            df_history = pd.read_csv(stock_file, index_col=0, parse_dates=True)
        else:
            # 如果历史文件不存在，创建新的
            df_history = pd.DataFrame(columns=['code', 'open', 'high', 'low', 'close', 'volume'])
            df_history.index.name = 'Date'
        
        # 检查最新数据的日期是否已存在
        latest_date = df_latest.index[0]
        if latest_date in df_history.index:
            return local_code, True, f"数据已存在 ({latest_date.strftime('%Y-%m-%d')})"
        
        # 添加code列
        df_latest['code'] = local_code
        
        # 合并数据
        df_updated = pd.concat([df_history, df_latest])
        # 按日期排序
        df_updated = df_updated.sort_index()
        # 去重
        df_updated = df_updated[~df_updated.index.duplicated(keep='last')]
        
        # 保存更新后的数据
        with file_lock:
            # 再次检查，防止在获取锁期间其他线程已更新
            if is_already_updated(code, target_date):
                return local_code, True, f"{target_date} 已更新（跳过）"
            
            # 确保输出目录存在
            try:
                os.makedirs(STOCK_HISTORY_DIR, exist_ok=True)
            except Exception as dir_error:
                return local_code, False, f"创建目录失败: {str(dir_error)[:50]}"
            
            df_updated.to_csv(stock_file, encoding='utf-8-sig')
            
            # 验证保存的文件
            verify_df = pd.read_csv(stock_file, index_col=0, nrows=5)
            if len(verify_df) == 0:
                return local_code, False, "保存后验证失败：文件为空"
            
            # 验证code列是否存在且正确
            if 'code' not in verify_df.columns:
                return local_code, False, "保存后验证失败：缺少code列"
            
            if str(verify_df['code'].iloc[0]) != local_code:
                return local_code, False, f"保存后验证失败：code不匹配 {verify_df['code'].iloc[0]} != {local_code}"
        
        return local_code, True, f"{source} 成功更新 ({latest_date.strftime('%Y-%m-%d')})"
        
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
        return local_code, False, f"更新失败: {str(e)[:60]}"


# ====================== 主程序 ======================
def update_daily_latest(target_date=None):
    """更新每日最新数据
    
    Args:
        target_date: 目标日期，格式为 'YYYY-MM-DD'，默认为今天
    """
    # 如果未指定目标日期，使用今天
    if target_date is None:
        target_date = datetime.today().strftime('%Y-%m-%d')
    
    # 读取股票列表
    all_codes = read_stock_codes(CSV_INPUT)

    # 过滤掉已经更新过的股票
    todo_codes = [code for code in all_codes if not is_already_updated(code, target_date)]
    updated_codes = [code for code in all_codes if is_already_updated(code, target_date)]

    print("=" * 80)
    print(f"开始获取 A 股【{target_date}】数据...")
    print("=" * 80)
    print(f"总股票数量: {len(all_codes)} 只")
    print(f"已更新（跳过）: {len(updated_codes)} 只")
    print(f"本次需要更新: {len(todo_codes)} 只")
    print(f"线程数: {MAX_WORKERS}")
    print(f"数据保存目录: {OUTPUT_DIR}")

    if not todo_codes:
        print(f"所有股票在 {target_date} 均已更新完成！无需重复更新。")
        return

    success = 0
    failed = []
    results = []

    # 使用多线程并行处理
    # 创建一个非守护线程的ThreadPoolExecutor
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    try:
        future_to_code = {executor.submit(update_single_stock, c, target_date): c for c in todo_codes}

        for future in tqdm(as_completed(future_to_code), total=len(todo_codes), desc="更新进度"):
            code, ok, msg = future.result()
            if ok:
                success += 1
                # 收集成功的结果用于生成每日汇总文件
                if "成功更新" in msg:
                    # 解析日期
                    date_str = msg.split('(')[1].split(')')[0]
                    # 获取最新数据
                    stock_file = os.path.join(STOCK_HISTORY_DIR, f"{code}.csv")
                    if os.path.exists(stock_file):
                        df = pd.read_csv(stock_file, index_col=0, parse_dates=True)
                        if not df.empty:
                            latest_row = df.iloc[-1]
                            row = {
                                'code': code,
                                'trade_date': date_str,
                                'Open': latest_row.get('open'),
                                'High': latest_row.get('high'),
                                'Low': latest_row.get('low'),
                                'Close': latest_row.get('close'),
                                'Volume': latest_row.get('volume')
                            }
                            results.append(row)
            else:
                failed.append((code, msg))
    finally:
        # 确保所有线程都完成
        executor.shutdown(wait=True)
        # 给线程一些时间来完全清理
        time.sleep(1)

    # 生成每日汇总文件（append模式）
    if results:
        final_df = pd.DataFrame(results)
        # 列顺序
        cols = ['code', 'trade_date', 'Open', 'High', 'Low', 'Close', 'Volume']
        final_df = final_df[[c for c in cols if c in final_df.columns]]

        # 每天生成一个文件
        filename = f"daily_latest_{target_date}.csv"
        save_path = os.path.join(OUTPUT_DIR, filename)
        
        # 检查文件是否存在，如果存在则追加，否则创建
        if os.path.exists(save_path):
            # 读取现有文件
            existing_df = pd.read_csv(save_path)
            # 合并数据并去重
            combined_df = pd.concat([existing_df, final_df])
            combined_df = combined_df.drop_duplicates(subset=['code'], keep='last')
            combined_df.to_csv(save_path, index=False, encoding='utf-8-sig')
        else:
            # 创建新文件
            final_df.to_csv(save_path, index=False, encoding='utf-8-sig')

    print("\n" + "=" * 80)
    print(f"✅ {target_date} 数据更新完成！")
    print(f"本次成功更新: {success} 只")
    print(f"本次失败: {len(failed)} 只")
    print(f"历史数据保存目录: {STOCK_HISTORY_DIR}")
    
    if results:
        print(f"每日汇总文件: {save_path}")
        print(f"汇总文件包含: {len(results)} 只股票")
        print(final_df[["code", "trade_date", "Close"]].tail(5))
    
    if failed:
        print("\n失败股票（前10条）:")
        for c, m in failed[:10]:
            print(f"  {c} → {m}")
        pd.DataFrame(failed, columns=["code", "error"]).to_csv(f"update_failed_{target_date}.csv", index=False, encoding='utf-8-sig')
        print(f"失败列表已保存到 → update_failed_{target_date}.csv（可后续重试）")
    
    print(f"\n断点续传功能已启用！下次运行会自动跳过 {target_date} 已更新的股票。")


if __name__ == "__main__":
    # 首次运行安装依赖（只需一次）：
    # pip install yfinance pandas requests tqdm
    import argparse
    
    parser = argparse.ArgumentParser(description='更新每日最新数据')
    parser.add_argument('--date', type=str, help='目标日期，格式为 YYYY-MM-DD，默认为今天')
    
    args = parser.parse_args()
    
    update_daily_latest(args.date)
