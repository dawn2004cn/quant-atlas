import os
import sys
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

def sync_benchmarks():
    print("🚀 开始补全 Qlib 基准指数数据 (sh000300)...")
    settings = AppSettings.from_env()
    bin_dir = Path("instance/qlib_bin")
    
    # 常用基准代码映射
    bench_map = {
        "sh000300": "sh000300",  # 沪深 300
        "sh000001": "sh000001",  # 上证指数
        "sz399001": "sz399001",  # 深证成指
        "sz399006": "sz399006",  # 创业板指
        "sh000688": "sh000688",  # 科创 50
        "bj899050": "bj899050",  # 北证 50
    }
    
    # 1. 加载日历
    cal_file = bin_dir / "calendars" / "day.txt"
    if not cal_file.exists():
        print("❌ 找不到 Qlib 日历，请先运行全量同步。")
        return
    dates = cal_file.read_text(encoding="utf-8").splitlines()
    date_to_idx = {d: i for i, d in enumerate(dates)}
    total_days = len(dates)

    features = ["open", "high", "low", "close", "volume", "amount"]
    
    conn = mysql_connect(settings.mysql)
    synced_count = 0
    try:
        for db_code, qlib_code in bench_map.items():
            with conn.cursor() as cur:
                # 获取指数数据
                cur.execute(f"""
                    SELECT date, open, high, low, close, volume, amount 
                    FROM stock_history 
                    WHERE stock_code = %s 
                    ORDER BY date ASC
                """, (db_code,))
                rows = cur.fetchall()
                
                if not rows:
                    print(f"⚠️ 数据库中缺少指数 {db_code} 的数据，跳过。")
                    continue
                
                # Convert tuples to dicts for easier access
                rows = [dict(zip(['date', 'open', 'high', 'low', 'close', 'volume', 'amount'], r)) for r in rows]
                
                # 写入 .bin
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
                    
                    feat_dir = bin_dir / "features" / feat
                    feat_dir.mkdir(parents=True, exist_ok=True)
                    bin_path = feat_dir / f"{qlib_code.lower()}.bin"
                    with open(bin_path, "wb") as fb:
                        fb.write(arr.tobytes())
                
                print(f"✅ 成功补全基准: {qlib_code} ({len(rows)} 条记录)")
                synced_count += 1
                
                # 更新 instruments/all.txt (如果不在里面)
                inst_file = bin_dir / "instruments" / "all.txt"
                content = inst_file.read_text(encoding="utf-8") if inst_file.exists() else ""
                v_start, v_end = str(rows[0]['date']), str(rows[-1]['date'])
                if qlib_code not in content:
                    with open(inst_file, "a", encoding="utf-8") as fa:
                        fa.write(f"{qlib_code}\t{v_start}\t{v_end}\n")

    finally:
        conn.close()

    print(f"✨ 补全任务完成。同步了 {synced_count} 个基准。")

if __name__ == "__main__":
    sync_benchmarks()
