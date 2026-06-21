import os
from dotenv import load_dotenv
from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect

load_dotenv()
settings = AppSettings.from_env()

def audit_codes():
    conn = mysql_connect(settings.mysql)
    try:
        with conn.cursor() as cur:
            # 1. 统计不带前缀的（假设都是CN市场）
            cur.execute("SELECT COUNT(*) as cnt FROM stocks WHERE code NOT LIKE '%%:%%'")
            no_prefix = cur.fetchone()['cnt']
            
            # 2. 统计带前缀的
            cur.execute("SELECT COUNT(*) as cnt FROM stocks WHERE code LIKE 'CN:%%'")
            with_prefix = cur.fetchone()['cnt']
            
            print(f"Stocks without prefix: {no_prefix}")
            print(f"Stocks with 'CN:' prefix: {with_prefix}")
            
            if no_prefix > 0:
                cur.execute("SELECT code FROM stocks WHERE code NOT LIKE '%%:%%' LIMIT 5")
                samples = [r['code'] for r in cur.fetchall()]
                print(f"Samples without prefix: {samples}")

    finally:
        conn.close()

if __name__ == "__main__":
    audit_codes()
