import os
import sys
import shutil
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from dotenv import load_dotenv

# 1. 环境准备
load_dotenv()
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.database.mysql_client import mysql_connect
from app.config import AppSettings

def run_real_data_sync_full():
    print("🚀 开始将 MySQL 真实数据【全量同步】至 Qlib...")
    settings = AppSettings.from_env()
    bin_dir = Path("instance/qlib_bin")

    # 清理并重新初始化目录
    if bin_dir.exists(): shutil.rmtree(bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    features = ["open", "high", "low", "close", "volume", "amount"]
    for f in features:
        (bin_dir / "features" / f).mkdir(parents=True, exist_ok=True)

    # 1. 获取全量交易日历
    print("📅 正在从 MySQL 提取全量交易日历...")
    conn = mysql_connect(settings.mysql)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT date FROM stock_history ORDER BY date ASC")
            dates = [str(r['date']) for r in cur.fetchall()]
            
            # 获取所有有历史记录的股票代码
            print("🔍 检索全量股票清单...")
            cur.execute("""
                SELECT stock_code, COUNT(*) as cnt 
                FROM stock_history 
                GROUP BY stock_code 
                HAVING cnt > 1 
                ORDER BY stock_code ASC
            """)
            stock_codes = [r['stock_code'] for r in cur.fetchall()]
    finally:
        conn.close()

    if not dates:
        print("❌ MySQL 中没有历史数据。")
        return
    
    # 保存 Qlib 日历
    cal_dir = bin_dir / "calendars"
    cal_dir.mkdir(parents=True, exist_ok=True)
    (cal_dir / "day.txt").write_text("\n".join(dates), encoding="utf-8")
    
    date_to_idx = {d: i for i, d in enumerate(dates)}
    total_days = len(dates)
    print(f"✅ 日历已就绪: {total_days} 天 (1990至今)")

    # 2. 循环处理每一只股票
    instruments_list = []
    total_stocks = len(stock_codes)
    print(f"📦 正在同步 {total_stocks} 只股票的历史特征...")
    
    from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
    
    conn = mysql_connect(settings.mysql)
    try:
        for i, code in enumerate(stock_codes):
            with conn.cursor() as cur:
                # 获取单只股票的 OHLCV
                cur.execute(f"""
                    SELECT date, open, high, low, close, volume, amount 
                    FROM stock_history 
                    WHERE stock_code = %s 
                    ORDER BY date ASC
                """, (code,))
                rows = cur.fetchall()
                if not rows: continue
                
                # 转换代码 (sh600519 -> sh600519)
                clean_code = code.lower()
                if clean_code.startswith(('sh', 'sz', 'bj')):
                    qlib_code = clean_code
                else:
                    prefix = "sh" if clean_code.startswith("6") else "sz"
                    qlib_code = f"{prefix}{clean_code}"
                
                v_start = str(rows[0]['date'])
                v_end = str(rows[-1]['date'])
                
                # 为每个特征生成二进制向量
                for feat in features:
                    arr = np.full(total_days, np.nan, dtype=np.float32)
                    for r in rows:
                        d_str = str(r['date'])
                        if d_str in date_to_idx:
                            val = r.get(feat)
                            try:
                                arr[date_to_idx[d_str]] = float(val) if val is not None else np.nan
                            except:
                                # TODO: log or handle conversion error for individual date
                                pass
                    
                    # 写入 Qlib bin 文件
                    f_path = bin_dir / "features" / feat / f"{qlib_code.lower()}.bin"
                    with open(f_path, "wb") as fb:
                        fb.write(arr.tobytes())
                
                instruments_list.append(f"{qlib_code}\t{v_start}\t{v_end}")
                
                if (i + 1) % 200 == 0 or (i + 1) == total_stocks:
                    print(f"  - [进度] {i+1}/{total_stocks} 股票同步完成")
    finally:
        conn.close()

    # 3. 生成 instruments 索引
    inst_dir = bin_dir / "instruments"
    inst_dir.mkdir(parents=True, exist_ok=True)
    (inst_dir / "all.txt").write_text("\n".join(instruments_list), encoding="utf-8")

    print(f"✨ 全量同步圆满完成！")
    print(f"📊 总计处理股票: {len(instruments_list)} 只")
    print(f"📍 目标路径: {bin_dir.resolve()}")

if __name__ == "__main__":
    run_real_data_sync_full()
