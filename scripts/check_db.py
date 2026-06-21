import sqlite3
import os

db_path = r'E:\project\workspace\myrepo\quant-atlas\instance\stock_cache.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('Tables:', tables)

if ('stocks',) in tables:
    cur.execute('SELECT COUNT(*) FROM stocks')
    print('Stock count:', cur.fetchone()[0])

    cur.execute('SELECT code, name, price FROM stocks LIMIT 3')
    print('Sample:', cur.fetchall())
else:
    print('No stocks table')