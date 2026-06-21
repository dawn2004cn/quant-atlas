"""Create stock history tables by market using pymysql directly."""

import pymysql
from app.config import AppSettings

def create_stock_history_market_tables():
    """创建按市场划分的股票历史表"""
    settings = AppSettings.from_env()
    
    # 直接使用pymysql连接
    conn = pymysql.connect(
        host=settings.mysql.host,
        port=settings.mysql.port,
        user=settings.mysql.user,
        password=settings.mysql.password,
        database=settings.mysql.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        with conn.cursor() as cursor:
            markets = ['sh', 'sz', 'bj', 'hk', 'us', 'btc']
            for market in markets:
                table_name = f"stock_history_{market}"
                # 创建表SQL
                create_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    stock_code VARCHAR(32) NOT NULL,
                    date VARCHAR(32) NOT NULL,
                    open DOUBLE DEFAULT 0.0,
                    high DOUBLE DEFAULT 0.0,
                    low DOUBLE DEFAULT 0.0,
                    close DOUBLE DEFAULT 0.0,
                    volume DOUBLE DEFAULT 0.0,
                    amount DOUBLE DEFAULT 0.0,
                    PRIMARY KEY (stock_code, date),
                    INDEX idx_date (date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
                cursor.execute(create_sql)
                print(f"Created table: {table_name}")
        conn.commit()
        print("All stock history market tables created successfully!")
    finally:
        conn.close()

if __name__ == "__main__":
    create_stock_history_market_tables()
