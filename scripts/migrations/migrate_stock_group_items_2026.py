"""迁移脚本：为 stock_group_items 表添加 added_at 和 is_removed 字段"""

from __future__ import annotations

import pymysql
from sqlalchemy import text
from app.infrastructure.database.orm import get_engine


def up():
    """添加 added_at 和 is_removed 字段"""
    engine = get_engine()
    with engine.connect() as conn:
        # 检查字段是否存在
        conn.execute(text("SET NAMES utf8mb4"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        
        # 添加 added_at 字段
        try:
            conn.execute(text("""
                ALTER TABLE stock_group_items 
                ADD COLUMN added_at DATETIME DEFAULT CURRENT_TIMESTAMP AFTER symbol
            """))
            print("[OK] added_at 字段已添加")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("[SKIP] added_at 字段已存在")
            else:
                print(f"[ERROR] 添加 added_at 失败: {e}")
        
        # 添加 is_removed 字段
        try:
            conn.execute(text("""
                ALTER TABLE stock_group_items 
                ADD COLUMN is_removed TINYINT DEFAULT 0 AFTER added_at
            """))
            print("[OK] is_removed 字段已添加")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("[SKIP] is_removed 字段已存在")
            else:
                print(f"[ERROR] 添加 is_removed 失败: {e}")
        
        conn.commit()
        print("[DONE] 迁移完成")


def down():
    """回滚：删除字段"""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SET NAMES utf8mb4"))
        
        try:
            conn.execute(text("ALTER TABLE stock_group_items DROP COLUMN is_removed"))
            print("[OK] is_removed 字段已删除")
        except Exception as e:
            print(f"[WARN] 删除 is_removed: {e}")
        
        try:
            conn.execute(text("ALTER TABLE stock_group_items DROP COLUMN added_at"))
            print("[OK] added_at 字段已删除")
        except Exception as e:
            print(f"[WARN] 删除 added_at: {e}")
        
        conn.commit()
        print("[DONE] 回滚完成")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        down()
    else:
        up()