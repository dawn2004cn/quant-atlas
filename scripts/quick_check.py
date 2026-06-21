import sys; sys.path.insert(0,'.')
from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect
import pandas as pd
s=AppSettings.from_env()
c=mysql_connect(s.mysql)
print("Getting counts...")
print(pd.read_sql("SELECT COUNT(DISTINCT stock_code) as cnt FROM stock_history WHERE date>='2026-04-23'", c).to_string())
print(pd.read_sql("SELECT COUNT(DISTINCT stock_code) as cnt FROM stock_history WHERE date>='2026-04-28'", c).to_string())
print(pd.read_sql("SELECT latest_date, COUNT(*) as cnt FROM (SELECT stock_code, MAX(date) as latest_date FROM stock_history GROUP BY stock_code) t GROUP BY latest_date ORDER BY latest_date DESC LIMIT 5", c).to_string())
c.close()