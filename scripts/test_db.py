from app.config import AppSettings
from app.infrastructure.database.adapters import MysqlAdapter

settings = AppSettings.from_env()
db = MysqlAdapter(settings.mysql)

# Check actual stock_code values
rows = db.execute_select("SELECT stock_code FROM stock_history_sh LIMIT 10", ())
print("Sample stock_codes in DB:")
for r in rows:
    print("  " + r["stock_code"])

# Check count
count = db.execute_scalar("SELECT COUNT(*) FROM stock_history_sh")
print(f"Total rows in stock_history_sh: {count}")

count2 = db.execute_scalar("SELECT COUNT(*) FROM stock_history_sz")
print(f"Total rows in stock_history_sz: {count2}")