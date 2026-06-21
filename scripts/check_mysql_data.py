# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect
import pandas as pd

settings = AppSettings.from_env()
ms = settings.mysql
conn = mysql_connect(ms)
if conn is None:
    print("Cannot connect to MySQL")
    exit(1)

# Check stock_history table schema
try:
    df = pd.read_sql("DESCRIBE stock_history", conn)
    print("stock_history schema:")
    print(df.to_string())
except Exception as e:
    print(f"Error describing: {e}")

# Check a specific stock
try:
    df2 = pd.read_sql("SELECT stock_code, date, close FROM stock_history WHERE stock_code='sh000001' ORDER BY date DESC LIMIT 10", conn)
    print("\nsh000001 latest 10 rows:")
    print(df2.to_string())
except Exception as e:
    print(f"Error: {e}")

conn.close()