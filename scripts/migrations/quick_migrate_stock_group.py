"""简单的迁移脚本：添加自选股表新字段"""

import pymysql
import os
import sys

# 连接 MySQL
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'root'),
    'database': os.getenv('DB_NAME', 'quant_atlas'),
    'charset': 'utf8mb4'
}

def migrate():
    conn = pymysql.connect(**db_config)
    cur = conn.cursor()
    
    # 添加 added_at 字段
    try:
        cur.execute("""
            ALTER TABLE stock_group_items 
            ADD COLUMN added_at DATETIME DEFAULT CURRENT_TIMESTAMP
        """)
        print("[OK] added_at 字段已添加")
    except pymysql.err.OperationalError as e:
        if "Duplicate column" in str(e):
            print("[SKIP] added_at 字段已存在")
        else:
            print(f"[ERROR] added_at: {e}")
    
    # 添加 is_removed 字段  
    try:
        cur.execute("""
            ALTER TABLE stock_group_items 
            ADD COLUMN is_removed TINYINT DEFAULT 0
        """)
        print("[OK] is_removed 字段已添加")
    except pymysql.err.OperationalError as e:
        if "Duplicate column" in str(e):
            print("[SKIP] is_removed 字段已存在")
        else:
            print(f"[ERROR] is_removed: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("[DONE] 迁移完成")
    print("\n请重启应用后刷新页面")

if __name__ == "__main__":
    migrate()