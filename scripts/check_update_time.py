import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect

load_dotenv()
settings = AppSettings.from_env()

def check_update_times():
    conn = mysql_connect(settings.mysql)
    try:
        with conn.cursor() as cur:
            # 1. 总数
            cur.execute("SELECT COUNT(*) as cnt FROM stocks")
            total = cur.fetchone()['cnt']
            print(f"Total stocks: {total}")
            
            # 2. 24小时内更新的数量
            cutoff = (datetime.now() - timedelta(minutes=1440)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("SELECT COUNT(*) as cnt FROM stocks WHERE update_time > %s", (cutoff,))
            recent = cur.fetchone()['cnt']
            print(f"Stocks updated in last 24h: {recent}")
            
            # 3. 查看最大的 update_time
            cur.execute("SELECT MAX(update_time) as mx FROM stocks")
            max_time = cur.fetchone()['mx']
            print(f"Latest update_time in DB: {max_time}")
            
            # 4. 如果 update_time > cutoff 很少，看看如果不带时间过滤是多少
            cur.execute("SELECT COUNT(*) as cnt FROM stocks ORDER BY update_time DESC")
            print(f"Total if no time filter: {cur.fetchone()['cnt']}")

    finally:
        conn.close()

if __name__ == "__main__":
    check_update_times()
