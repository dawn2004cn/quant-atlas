import pymysql
import os
from datetime import datetime, timedelta

import sys

# 从环境变量获取 MySQL 配置
MYSQL_HOST = os.getenv("MYSQL_HOST", "192.168.8.103")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "quant_atlas")
if not os.environ.get("MYSQL_PASSWORD"):
    print("WARNING: Using default DB password. Set MYSQL_PASSWORD env var.", file=sys.stderr)

def get_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4"
    )

def main():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 查询当前最新日期
            cursor.execute("SELECT MAX(publish_date) as max_date FROM yanbao_items")
            result = cursor.fetchone()
            max_date = result[0] if result else None
            print(f"当前最新研报日期: {max_date}")
            
            # 计算起始日期 (从最新日期的下一天，或30天前)
            today = datetime.now().strftime("%Y-%m-%d")
            if max_date:
                dt = datetime.strptime(str(max_date), "%Y-%m-%d")
                start_date = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            # 忽略开始日期 = 今天的情况
            if start_date >= today:
                print(f"研报已是最新: {today}")
                return
            
            print(f"抓取范围: {start_date} 到 {today}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()