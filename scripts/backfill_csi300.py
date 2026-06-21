import os
import sys
import pandas as pd
import akshare as ak
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 1. 环境准备
load_dotenv()
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.database.mysql_client import mysql_connect
from app.config import AppSettings
from scripts.sync_benchmarks import sync_benchmarks

def backfill_csi300():
    print("🚀 开始补全沪深 300 (000300) 全量历史数据...")
    settings = AppSettings.from_env()

    # 1. 联网抓取全量数据
    try:
        print("🌐 正在从 AkShare 获取 000300 全量数据...")
        # 尝试使用最新的 akshare 接口名
        df = ak.stock_zh_index_daily(symbol="sh000300")
        if df.empty:
            print("❌ 未获取到数据。")
            return
        
        print(f"✅ 获取成功，共 {len(df)} 条记录")
        
        # 处理可能的中文列名或别名
        column_map = {
            "date": "date", "日期": "date",
            "open": "open", "开盘价": "open", "开盘": "open",
            "high": "high", "最高价": "high", "最高": "high",
            "low": "low", "最低价": "low", "最低": "low",
            "close": "close", "收盘价": "close", "收盘": "close",
            "volume": "volume", "成交量": "volume",
            "amount": "amount", "成交额": "amount"
        }
        
        df = df.reset_index()
        # 统一列名
        df.columns = [column_map.get(col.lower(), col) for col in df.columns]
        
        # 如果依然缺少 amount，尝试计算 (假定 volume * close * 100 左右，或者设为0)
        if 'amount' not in df.columns:
            print("⚠️ 缺少成交额字段，尝试使用 volume * close 估算...")
            df['amount'] = df['volume'] * df['close'] 

    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        return

    # 2. 存入 MySQL
    print("💾 正在写入 MySQL 数据库...")
    conn = mysql_connect(settings.mysql, autocommit=True)
    try:
        with conn.cursor() as cur:
            data = []
            for _, row in df.iterrows():
                # 转换日期格式
                d_val = row['date']
                if isinstance(d_val, str):
                    d_str = d_val[:10]
                else:
                    d_str = d_val.strftime('%Y-%m-%d')
                    
                data.append((
                    "sh000300",
                    d_str,
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    float(row['volume']),
                    float(row.get('amount', 0))
                ))
            
            sql = """
                REPLACE INTO stock_history 
                (stock_code, date, open, high, low, close, volume, amount) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            batch_size = 1000
            for i in range(0, len(data), batch_size):
                cur.executemany(sql, data[i:i+batch_size])
                print(f"  - 已同步 {min(i+batch_size, len(data))}/{len(data)} 条记录")

    finally:
        conn.close()

    print("✨ MySQL 数据补全完成。")

    # 3. 触发 Qlib 同步
    print("🔄 正在刷新 Qlib 二进制缓存...")
    sync_benchmarks()

if __name__ == "__main__":
    backfill_csi300()
