import os
import pandas as pd
from datetime import datetime
from mootdx.reader import Reader
from questdb import Sender
from tqdm import tqdm
import time

# ====================== 配置区域 ======================
TDX_DATA_DIR = r"E:\tdx\通达信金融终端(开心果交易版)V2024.02\vipdoc"  # ←←← 改成你通达信安装目录
import os

QUESTDB_HOST = os.getenv("QUESTDB_HOST", "192.168.8.103")
QUESTDB_PORT = int(os.getenv("QUESTDB_ILP_PORT", os.getenv("QUESTDB_PORT", "9009")))

# 支持沪深 + 北交所
MARKETS = {
    'sh': 'lday',  # 上海
    'sz': 'lday',  # 深圳
    'bj': 'lday'  # 北交所（如果有）
}

TABLE_NAME = "stock_history"


# ====================== QuestDB 写入函数 ======================
def write_to_questdb(df: pd.DataFrame):
    """使用 Line Protocol 高速写入"""
    with Sender(QUESTDB_HOST, QUESTDB_PORT, buffer_size=100_000) as sender:
        for _, row in df.iterrows():
            sender.row(
                TABLE_NAME,
                symbols={'stock_code': row['stock_code']},
                columns={
                    'trade_date': pd.to_datetime(row['trade_date']).date(),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume']),
                    'amount': float(row['amount']),
                },
                at=pd.to_datetime(row['trade_date']).value  # timestamp
            )
        sender.flush()


# ====================== 主程序 ======================
def import_all_tdx_to_questdb():
    reader = Reader.factory(tdxdir=TDX_DATA_DIR)

    for market, folder in MARKETS.items():
        day_dir = os.path.join(TDX_DATA_DIR, market, folder)
        if not os.path.exists(day_dir):
            print(f"目录不存在: {day_dir}")
            continue

        files = [f for f in os.listdir(day_dir) if f.endswith('.day')]

        print(f"\n开始处理 {market.upper()} 市场，共 {len(files)} 只股票...")

        for filename in tqdm(files):
            stock_code = filename[:6]  # 如 600000
            full_path = os.path.join(day_dir, filename)

            try:
                # 使用 mootdx 读取 .day 文件
                df = reader.daily(symbol=stock_code, market=market)

                if df is None or len(df) == 0:
                    continue

                # 准备数据
                df = df.reset_index()
                df['stock_code'] = stock_code

                # 字段重命名（适应 QuestDB）
                df = df.rename(columns={
                    'date': 'trade_date',
                    'vol': 'volume'  # mootdx 返回的成交量字段通常是 vol
                })

                # 确保字段存在
                for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                    if col not in df.columns:
                        df[col] = 0.0

                # 写入 QuestDB
                write_to_questdb(df)

                # 避免太快（可选）
                # time.sleep(0.01)

            except Exception as e:
                print(f"处理 {stock_code} 失败: {e}")
                continue

    print("\n=== 全部导入完成！===")


if __name__ == "__main__":
    import_all_tdx_to_questdb()