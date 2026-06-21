# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect
import pandas as pd

settings = AppSettings.from_env()
conn = mysql_connect(settings.mysql)

# Get count of stocks by their latest date
df = pd.read_sql("""
    SELECT latest_date, COUNT(*) as stock_count
    FROM (
        SELECT stock_code, MAX(date) as latest_date
        FROM stock_history
        GROUP BY stock_code
    ) t
    GROUP BY latest_date
    ORDER BY latest_date DESC
    LIMIT 20
""", conn)
print("Stocks by latest date:")
print(df.to_string())

# Count stocks with recent data (2026-04-23 or later)
df2 = pd.read_sql("""
    SELECT COUNT(DISTINCT stock_code) as count
    FROM stock_history
    WHERE date >= '2026-04-23'
""", conn)
print(f"\nStocks with data >= 2026-04-23: {df2['count'].iloc[0]}")

# Count total distinct stocks
df3 = pd.read_sql("SELECT COUNT(DISTINCT stock_code) as count FROM stock_history", conn)
print(f"Total distinct stocks: {df3['count'].iloc[0]}")

conn.close()