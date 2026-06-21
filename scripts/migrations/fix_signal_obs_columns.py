#!/usr/bin/env python
"""Fix missing columns in signal_observations table"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text

mysql_user = os.environ.get("MYSQL_USER", "admin")
mysql_pass = os.environ.get("MYSQL_PASSWORD") or ""
mysql_host = os.environ.get("MYSQL_HOST", "192.168.8.103")
mysql_port = os.environ.get("MYSQL_PORT", "3307")
mysql_db = os.environ.get("MYSQL_DATABASE", "quant_atlas")
mysql_url = f"mysql+pymysql://{mysql_user}:{mysql_pass}@{mysql_host}:{mysql_port}/{mysql_db}"
engine = create_engine(mysql_url)

with engine.connect() as conn:
    # Add return_pct column
    try:
        conn.execute(text("ALTER TABLE signal_observations ADD COLUMN return_pct DECIMAL(10,4) DEFAULT 0"))
        conn.commit()
        print("[OK] Added return_pct column")
    except Exception as e:
        if "Duplicate" in str(e):
            print("return_pct column already exists")
        else:
            print(f"Error: {e}")

    # Add change_pct column for compatibility
    try:
        conn.execute(text("ALTER TABLE signal_observations ADD COLUMN change_pct DECIMAL(10,4) DEFAULT 0"))
        conn.commit()
        print("[OK] Added change_pct column")
    except Exception as e:
        if "Duplicate" in str(e):
            print("change_pct column already exists")
        else:
            print(f"Error: {e}")

print("Done!")