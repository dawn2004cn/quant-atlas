"""生成 MySQL 数据库和所有表的脚本"""

from __future__ import annotations

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from app.infrastructure.database.orm import Base
from app.infrastructure.database.models import market, moments, advanced, investment, trading, auth
from app.infrastructure.database.models import risk
from app.core.config import AppSettings


def get_mysql_url() -> str:
    """从配置获取 MySQL 连接 URL"""
    s = AppSettings.from_env()
    db = s.database
    return f"mysql+pymysql://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}?charset=utf8mb4"


def create_database():
    """创建数据库（如果不存在）"""
    s = AppSettings.from_env()
    db = s.database
    url = f"mysql+pymysql://{db.user}:{db.password}@{db.host}:{db.port}?charset=utf8mb4"
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db.name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        print(f"[OK] 数据库 '{db.name}' 创建完成")
    engine.dispose()


def create_tables():
    """创建所有表"""
    engine = create_engine(get_mysql_url(), echo=False)
    Base.metadata.create_all(bind=engine)
    
    # 列出创建的表
    tables = sorted(Base.metadata.tables.keys())
    for t in tables:
        print(f"[OK] 表 '{t}' 创建完成")
    
    engine.dispose()
    print(f"\n[DONE] 共创建 {len(tables)} 个表")


def create_users_table():
    """创建用户表（MySQL 实现）"""
    from app.infrastructure.database.models.auth import Role, User
    
    engine = create_engine(get_mysql_url(), echo=False)
    Role.__table__.create(engine, checkfirst=True)
    User.__table__.create(engine, checkfirst=True)
    print("[OK] 用户表创建完成")
    engine.dispose()


def drop_all_tables():
    """删除所有表（危险操作）"""
    engine = create_engine(get_mysql_url(), echo=False)
    tables = sorted(Base.metadata.tables.keys(), reverse=True)
    for t in tables:
        try:
            with engine.connect() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {t}"))
                conn.commit()
            print(f"[OK] 表 '{t}' 已删除")
        except Exception as e:
            print(f"[WARN] 删除表 {t}: {e}")
    engine.dispose()
    print(f"\n[DONE] 已删除 {len(tables)} 个表")


def show_tables():
    """显示所有表"""
    engine = create_engine(get_mysql_url(), echo=False)
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result.fetchall()]
    
    print(f"数据库中的表 ({len(tables)} 个):")
    for t in tables:
        print(f"  - {t}")
    engine.dispose()


def show_create_sql(table_name: str):
    """显示建表 SQL"""
    engine = create_engine(get_mysql_url(), echo=False)
    with engine.connect() as conn:
        result = conn.execute(text(f"SHOW CREATE TABLE {table_name}"))
        row = result.fetchone()
        if row:
            print(f"\n-- {table_name}")
            print(row[1])
    engine.dispose()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python generate_schema.py create      - 创建数据库和表")
        print("  python generate_schema.py show    - 显示所有表")
        print("  python generate_schema.py drop   - 删除所有表（危险!）")
        print("  python generate_schema.py sql <表名> - 显示建表 SQL")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "create":
        create_database()
        create_tables()
    elif cmd == "show":
        show_tables()
    elif cmd == "drop":
        confirm = input("确认删除所有表? (yes/no): ")
        if confirm.lower() == "yes":
            drop_all_tables()
        else:
            print("取消操作")
    elif cmd == "sql" and len(sys.argv) > 2:
        show_create_sql(sys.argv[2])
    else:
        print(f"未知命令: {cmd}")