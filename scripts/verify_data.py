# -*- coding: utf-8 -*-
"""Verify inserted data"""
import sys
sys.path.insert(0, '.')

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect
import pandas as pd

settings = AppSettings.from_env()
conn = mysql_connect(settings.mysql)

df = pd.read_sql("SELECT stock_code, date, close FROM stock_history WHERE date>='2026-04-23' ORDER BY stock_code, date", conn)
print("Data from 2026-04-23:")
print(df.to_string())

conn.close()