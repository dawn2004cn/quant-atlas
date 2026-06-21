import os
from dotenv import load_dotenv
from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect

load_dotenv()
settings = AppSettings.from_env()

def check_counts():
    if not settings.use_mysql:
        print("Current mode is NOT MySQL. Please check .env")
        return

    conn = mysql_connect(settings.mysql)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM stocks")
            print(f"Stocks table count: {cur.fetchone()['cnt']}")
            
            cur.execute("SELECT COUNT(*) as cnt FROM stock_history")
            print(f"Stock history count: {cur.fetchone()['cnt']}")
            
            cur.execute("SELECT COUNT(*) as cnt FROM watchlist")
            print(f"Watchlist count: {cur.fetchone()['cnt']}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_counts()
