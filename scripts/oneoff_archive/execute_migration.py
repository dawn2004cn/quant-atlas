import sys
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect

settings = AppSettings.from_env()
conn = mysql_connect(settings.mysql)
cur = conn.cursor()

with open("scripts/migrations/unify_all_stock_codes.sql", "r", encoding="utf-8") as f:
    sql = f.read()
    statements = sql.split(";")
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
        retries = 3
        while retries > 0:
            try:
                cur.execute(stmt)
                break
            except Exception as e:
                if "Lock wait timeout" in str(e) and retries > 0:
                    print(f"Lock timeout on: {stmt[:80]}... Retrying...")
                    conn.rollback()
                    time.sleep(5)
                    retries -= 1
                    continue
                else:
                    print(f"Error executing: {e}")
                    print(f"Statement: {stmt[:100]}...")
                    raise
    else:
        conn.commit()
        print("Migration completed successfully.")

cur.close()
conn.close()