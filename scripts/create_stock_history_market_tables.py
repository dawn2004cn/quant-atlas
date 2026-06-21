"""Create stock history tables by market."""

from sqlalchemy import text
from app.infrastructure.database.orm import create_db_engine, mysql_database_uri
from app.config import AppSettings

def create_stock_history_market_tables():
    """创建按市场划分的股票历史表"""
    settings = AppSettings.from_env()
    engine = create_db_engine(mysql_database_uri(settings.mysql))
    
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
        with engine.connect() as conn:
            conn.execute(text(create_sql))
            print(f"Created table: {table_name}")

if __name__ == "__main__":
    create_stock_history_market_tables()
    print("All stock history market tables created successfully!")
