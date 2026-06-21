"""研报数据更新脚本 - 直接使用 AkShare 而不导入整个应用"""

import pymysql
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import sys

# MySQL 配置
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
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

def insert_yanbao(conn, category: str, items: list[dict], batch_id: str) -> int:
    """批量插入研报数据"""
    if not items:
        return 0
    
    with conn.cursor() as cursor:
        values = []
        for item in items:
            title = item.get("title", "")[:512]
            publisher = item.get("publisher", item.get("org_name", ""))[:256]
            publish_date = item.get("publish_date", item.get("pub_date", ""))
            symbol = item.get("symbol", item.get("stock_code", ""))[:16]
            em_url = item.get("em_url", item.get("url", ""))[:512]
            
            values.append((
                title, category, publish_date, publisher, symbol, em_url, batch_id
            ))
        
        sql = """
            INSERT INTO yanbao_items 
            (title, category, publish_date, publisher, symbol, em_url, batch_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            title=VALUES(title), publisher=VALUES(publisher), em_url=VALUES(em_url)
        """
        cursor.executemany(sql, values)
        conn.commit()
        return len(values)

def fetch_yanbao_from_akshare(begin_date: str, end_date: str) -> dict[str, list]:
    """使用 AkShare 抓取研报"""
    try:
        from akshare import stock_research_report_em
    except ImportError:
        logger.warning("akshare 未安装")
        return {}
    
    result = {}
    categories = [
        ("个股研报", "stock_individual"),
        ("行业研报", "industry"),
    ]
    
    for cat_name, cat_key in categories:
        try:
            logger.info(f"抓取 {cat_name}...")
            df = stock_research_report_em(symbol="all", date=end_date)
            if df is not None and not df.empty:
                items = df.to_dict("records")
                result[cat_name] = items
                logger.info(f"  {cat_name}: {len(items)} 条")
        except Exception as e:
            logger.warning(f"  {cat_name} 失败: {e}")
    
    return result

def fetch_yanbao_from_eastmoney(begin_date: str, end_date: str) -> dict[str, list]:
    """使用东方财富 API 抓取研报"""
    import requests
    
    result = {}
    categories = {
        "个股研报": "https://data.eastmoney.com/report/stock.jshtml",
        "行业研报": "https://data.eastmoney.com/report/industry.jshtml",
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for cat_name, url in categories.items():
        try:
            logger.info(f"抓取 {cat_name}...")
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            
            # 解析 JSON 数据
            text = resp.text
            # 东财返回格式特殊，需要提取 data=... 中的内容
            import re
            match = re.search(r'data\s*=\s*(\[.+\])', text)
            if match:
                import json
                data = json.loads(match.group(1))
                result[cat_name] = data[:100]  # 限制数量
                logger.info(f"  {cat_name}: {len(data)} 条")
        except Exception as e:
            logger.warning(f"  {cat_name} 失败: {e}")
    
    return result

def main():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 查询当前最新日期
            cursor.execute("SELECT MAX(publish_date) as max_date FROM yanbao_items")
            result = cursor.fetchone()
            max_date = result["max_date"] if result else None
            print(f"当前最新研报日期: {max_date}")
            
            # 计算日期范围
            today = datetime.now().strftime("%Y-%m-%d")
            if max_date:
                dt = datetime.strptime(str(max_date), "%Y-%m-%d")
                start_date = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            # 已经是最新
            if start_date >= today:
                print(f"研报已是最新: {today}")
                return
            
            print(f"抓取范围: {start_date} -> {today}")
            batch_id = f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 尝试使用东方财富 HTML
            yanbao_data = fetch_yanbao_from_eastmoney(start_date, today)
            
            # 如果失败，尝试 AkShare
            if not yanbao_data:
                logger.info("尝试 AkShare...")
                yanbao_data = fetch_yanbao_from_akshare(start_date, today)
            
            # 插入数据
            total = 0
            for category, items in yanbao_data.items():
                if items:
                    n = insert_yanbao(conn, category, items, batch_id)
                    total += n
                    print(f"插入 {category}: {n} 条")
            
            print(f"总共插入: {total} 条")
            
            # 验证
            cursor.execute("SELECT MAX(publish_date) as max_date FROM yanbao_items")
            new_max = cursor.fetchone()["max_date"]
            print(f"更新后最新日期: {new_max}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()