"""Migrate stock history data to market-specific tables."""

from sqlalchemy import text
from app.infrastructure.database.orm import create_db_engine
from app.config import AppSettings

def migrate_stock_history_by_market():
    """按市场迁移股票历史数据"""
    settings = AppSettings.from_env()
    engine = create_db_engine(settings.mysql)
    
    # 从旧表读取数据
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM stock_history"))
        rows = result.fetchall()
    
    print(f"Found {len(rows)} rows to migrate")
    
    # 按市场分组
    rows_by_market = {}
    for row in rows:
        stock_code = row.stock_code
        if stock_code.startswith("sh"):
            table = "stock_history_sh"
        elif stock_code.startswith("sz"):
            table = "stock_history_sz"
        elif stock_code.startswith("bj"):
            table = "stock_history_bj"
        elif stock_code.startswith("hk"):
            table = "stock_history_hk"
        elif stock_code.startswith("us"):
            table = "stock_history_us"
        elif stock_code.startswith("btc"):
            table = "stock_history_btc"
        else:
            table = "stock_history"
        
        if table not in rows_by_market:
            rows_by_market[table] = []
        rows_by_market[table].append(row)
    
    # 插入到分表
    for table_name, table_rows in rows_by_market.items():
        if table_rows:
            insert_sql = f"""
            INSERT IGNORE INTO {table_name} 
            (stock_code, date, open, high, low, close, volume, amount)
            VALUES (:stock_code, :date, :open, :high, :low, :close, :volume, :amount)
            """
            with engine.connect() as conn:
                conn.execute(text(insert_sql), [dict(row._asdict()) for row in table_rows])
                conn.commit()
                print(f"Migrated {len(table_rows)} rows to {table_name}")

if __name__ == "__main__":
    migrate_stock_history_by_market()
    print("Stock history data migration completed!")
