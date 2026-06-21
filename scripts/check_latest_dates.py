# -*- coding: utf-8 -*-
"""Check latest dates in MySQL"""
import sys
sys.path.insert(0, '.')

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect
import pandas as pd

settings = AppSettings.from_env()
conn = mysql_connect(settings.mysql)

# Get latest 20 dates
df = pd.read_sql("SELECT DISTINCT date FROM stock_history WHERE stock_code='sh000001' ORDER BY date DESC LIMIT 20", conn)
print("Latest 20 dates in MySQL for sh000001:")
print(df.to_string())

conn.close()