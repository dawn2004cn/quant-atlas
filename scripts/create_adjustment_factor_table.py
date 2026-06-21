#!/usr/bin/env python
"""创建复权因子表."""

import pymysql
import sys

import os, sys
DB_CONFIG = {
    'host': os.environ.get("MYSQL_HOST", '192.168.8.103'),
    'port': int(os.environ.get("MYSQL_PORT", "3307")),
    'user': os.environ.get("MYSQL_USER", 'admin'),
    'password': os.environ.get("MYSQL_PASSWORD") or "",
    'database': os.environ.get("MYSQL_DATABASE", 'quant_atlas'),
    'connect_timeout': 10,
}
if not os.environ.get("MYSQL_PASSWORD"):
    print("WARNING: Using default DB password. Set MYSQL_PASSWORD env var.", file=sys.stderr)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS stock_adjustment_factor (
    stock_code VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    factor DECIMAL(10, 6) NOT NULL DEFAULT 1.000000,
    PRIMARY KEY (stock_code, date),
    INDEX idx_stock_code (stock_code),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='股票复权因子表 - 用于前后复权计算';
"""

def main():
    print("创建复权因子表...")
    
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute(CREATE_TABLE_SQL)
        conn.commit()
        
        print("[OK] 复权因子表创建成功: stock_adjustment_factor")
        
        # 验证表结构
        cur.execute("DESCRIBE stock_adjustment_factor")
        columns = cur.fetchall()
        print("\n表结构:")
        for col in columns:
            print(f"  {col[0]}: {col[1]}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] 创建失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
