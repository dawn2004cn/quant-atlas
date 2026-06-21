import sqlite3

conn = sqlite3.connect('data/watchlist.db')
cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('Tables:', tables)

if 'stock_groups' in tables:
    print('\n=== stock_groups ===')
    cur = conn.execute('SELECT * FROM stock_groups')
    for row in cur.fetchall():
        print(row)

if 'stock_group_items' in tables:
    print('\n=== stock_group_items ===')
    cur = conn.execute('SELECT * FROM stock_group_items LIMIT 20')
    for row in cur.fetchall():
        print(row)

conn.close()