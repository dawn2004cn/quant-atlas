import os
from dotenv import load_dotenv
from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect

load_dotenv()
settings = AppSettings.from_env()

def unify_table_column(cur, table, column, market_prefix="CN"):
    """通用表列统一化工具"""
    print(f"🚀 Processing {table}.{column}...")
    
    # 1. 删除重复项（如果加上前缀后与已有项冲突）
    # 对于有联合主键的表（如 stock_history: code+date），逻辑需稍作调整
    if table == "stock_history":
        join_cond = f"CONCAT('{market_prefix}:', s1.{column}) = s2.{column} AND s1.date = s2.date"
    elif table == "stock_group_items":
        join_cond = f"CONCAT('{market_prefix}:', s1.{column}) = s2.{column} AND s1.group_id = s2.group_id"
    elif table == "manager_holdings_snap":
        join_cond = f"CONCAT('{market_prefix}:', s1.{column}) = s2.{column} AND s1.manager_id = s2.manager_id AND s1.snap_date = s2.snap_date"
    else:
        join_cond = f"CONCAT('{market_prefix}:', s1.{column}) = s2.{column}"

    cur.execute(f"DELETE s1 FROM {table} s1 INNER JOIN {table} s2 ON {join_cond} WHERE s1.{column} NOT LIKE '%:%'")
    print(f"  - Deleted {cur.rowcount} redundant records.")
    
    # 2. 分批更新剩余项
    total_updated = 0
    while True:
        cur.execute(f"UPDATE {table} SET {column} = CONCAT('{market_prefix}:', {column}) WHERE {column} NOT LIKE '%%:%%' LIMIT 5000")
        rows = cur.rowcount
        total_updated += rows
        if rows > 0:
            print(f"  - Updated {total_updated} records...", end="\r")
        if rows < 5000:
            break
    print(f"\n  - Total updated in {table}: {total_updated}")

def cleanup_all_tables():
    if not settings.use_mysql:
        print("Not in MySQL mode.")
        return

    conn = mysql_connect(settings.mysql, autocommit=True)
    try:
        with conn.cursor() as cur:
            # 基础行情
            unify_table_column(cur, "stocks", "code")
            unify_table_column(cur, "stock_history", "stock_code")
            
            # 用户与分组
            unify_table_column(cur, "watchlist", "symbol")
            unify_table_column(cur, "stock_group_items", "symbol")
            
            # 基础数据
            unify_table_column(cur, "longhu_daily", "code")
            unify_table_column(cur, "yanbao_items", "stock_code")
            unify_table_column(cur, "archived_news", "symbol")
            unify_table_column(cur, "news_symbol_meta", "symbol")
            
            # 信号与策略
            unify_table_column(cur, "signal_flag_pool", "code")
            
            # 投资经理与竞赛
            unify_table_column(cur, "manager_trades", "symbol")
            unify_table_column(cur, "manager_holdings_snap", "symbol")
            unify_table_column(cur, "manager_positions_state", "symbol")
            unify_table_column(cur, "user_race_trades", "symbol")

            print("\n✨ ALL TABLES UNIFIED SUCCESSFULLY!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_all_tables()
