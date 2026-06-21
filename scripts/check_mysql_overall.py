# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect
import pandas as pd

settings = AppSettings.from_env()
conn = mysql_connect(settings.mysql)

# Get global max date
df = pd.read_sql("SELECT MAX(date) as max_date, MIN(date) as min_date, COUNT(DISTINCT stock_code) as stock_count FROM stock_history", conn)
print("Overall MySQL stats:")
print(df.to_string())

# Get latest 10 dates across all stocks
df2 = pd.read_sql("SELECT DISTINCT date FROM stock_history ORDER BY date DESC LIMIT 10", conn)
print("\nLatest 10 dates:")
print(df2.to_string())

conn.close()