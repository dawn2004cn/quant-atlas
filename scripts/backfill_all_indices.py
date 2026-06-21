import os
import sys
import pandas as pd
import akshare as ak
from pathlib import Path
from dotenv import load_dotenv

# 1. 环境准备
load_dotenv()
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.database.mysql_client import mysql_connect
from app.config import AppSettings
from scripts.sync_benchmarks import sync_benchmarks

def backfill_all_indices():
    print("🚀 开始补齐五大核心指数全量历史数据...")
    settings = AppSettings.from_env()

    # 指数配置 (DB Code -> AkShare Symbol)
    indices = {
        "sh000001": "sh000001",  # 上证指数
        "sz399001": "sz399001",  # 深证成指
        "sz399006": "sz399006",  # 创业板指
        "sh000688": "sh000688",  # 科创 50
        "bj899050": "bj899050",  # 北证 50
    }

    column_map = {
        "date": "date", "日期": "date",
        "open": "open", "开盘价": "open", "开盘": "open",
        "high": "high", "最高价": "high", "最高": "high",
        "low": "low", "最低价": "low", "最低": "low",
        "close": "close", "收盘价": "close", "收盘": "close",
        "volume": "volume", "成交量": "volume",
        "amount": "amount", "成交额": "amount"
    }

    conn = mysql_connect(settings.mysql, autocommit=True)
    
    try:
        for db_code, ak_symbol in indices.items():
            print(f"\n🌐 正在抓取指数: {ak_symbol} ({db_code})...")
            try:
                # 尝试默认抓取
                try:
                    df = ak.stock_zh_index_daily(symbol=ak_symbol)
                except:
                    print(f"  - 尝试备用接口 (EM)...")
                    df = ak.stock_zh_index_daily_em(symbol=ak_symbol)
                
                if df.empty:
                    print(f"  - ⚠️ 抓取结果为空")
                    continue
                
                # 规范化列名
                if df.index.name == 'date' or df.index.name == '日期':
                    df = df.reset_index()
                
                df.columns = [column_map.get(str(col).lower(), col) for col in df.columns]
                
                # 再次检查 date 是否在列中
                if 'date' not in df.columns:
                    # 如果列名里没有 date，尝试寻找第一列看起来像日期的
                    for col in df.columns:
                        if 'date' in str(col).lower() or '日期' in str(col):
                            df.rename(columns={col: 'date'}, inplace=True)
                            break
                
                # 缺失字段补全
                if 'amount' not in df.columns:
                    df['amount'] = df['volume'] * df['close']

                print(f"  - ✅ 抓取到 {len(df)} 条记录")

                # 存入 MySQL
                data = []
                for _, row in df.iterrows():
                    d_val = row['date']
                    d_str = d_val[:10] if isinstance(d_val, str) else d_val.strftime('%Y-%m-%d')
                    
                    data.append((
                        db_code, d_str,
                        float(row['open']), float(row['high']),
                        float(row['low']), float(row['close']),
                        float(row['volume']), float(row.get('amount', 0))
                    ))
                
                sql = """
                    REPLACE INTO stock_history 
                    (stock_code, date, open, high, low, close, volume, amount) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                # 分批写入
                batch_size = 1000
                for i in range(0, len(data), batch_size):
                    with conn.cursor() as cur:
                        cur.executemany(sql, data[i:i+batch_size])
                
                print(f"  - 💾 MySQL 同步完成 ({len(data)} 条)")

            except Exception as e:
                print(f"  - ❌ 抓取/保存失败: {e}")

    finally:
        conn.close()

    print("\n🔄 正在触发 Qlib 缓存刷新...")
    sync_benchmarks()
    print("✨ 全部指数补全任务完成！")

if __name__ == "__main__":
    backfill_all_indices()
