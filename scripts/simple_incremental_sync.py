
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""运行通达信日K线增量同步 - 简化版，不依赖Celery"""

from pathlib import Path
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加项目根目录到路径
base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

# 临时修改 app/__init__.py，避免导入celery_app
init_file = base_dir / "app" / "__init__.py"
if init_file.exists():
    content = init_file.read_text(encoding='utf-8')
    if "celery_app" in content:
        # 备份原始文件
        backup_file = base_dir / "app" / "__init__.py.backup"
        init_file.rename(backup_file)
        # 创建临时版本
        new_content = content.replace(
            "from .celery_app import celery_app",
            "# from .celery_app import celery_app  # Temporarily disabled"
        )
        init_file.write_text(new_content, encoding='utf-8')
        print("Temporarily modified app/__init__.py")
    else:
        print("app/__init__.py already modified")

try:
    # 现在导入我们需要的模块
    from app.config import AppSettings
    from app.core.logger import get_logger
    from app.domain.enums import MarketCode
    from app.infrastructure.database.mysql_client import ensure_mysql_schema, mysql_connect
    from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer
    from app.infrastructure.tdx_local.lday_reader import read_lday_file
    from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root

    # 复制tdx_dayk_sync_service.py的核心逻辑
    import csv
    from collections import defaultdict
    from typing import Any, Iterable
    import pandas as pd


    def _get_stock_history_table(stock_code: str) -&gt; str:
        normalized = SymbolNormalizer.to_db_code(stock_code)
        code_part = normalized
        if ":" in code_part:
            code_part = code_part.split(":", 1)[1]
        if code_part.startswith("sh"):
            return "stock_history_sh"
        elif code_part.startswith("sz"):
            return "stock_history_sz"
        elif code_part.startswith("bj"):
            return "stock_history_bj"
        elif code_part.startswith("hk"):
            return "stock_history_hk"
        elif code_part.startswith("us"):
            return "stock_history_us"
        elif code_part.startswith("btc"):
            return "stock_history_btc"
        else:
            return "stock_history"


    def _mysql_upsert_chunk_by_code(conn: Any, data: list[tuple[Any, ...]], *, cursor: Any) -&gt; int:
        if not data:
            return 0
        by_code = defaultdict(list)
        for row in data:
            stock_code = row[0]
            by_code[stock_code].append(row)

        total = 0
        sub_batch_size = 500

        for stock_code, rows in by_code.items():
            table_name = _get_stock_history_table(stock_code)
            for i in range(0, len(rows), sub_batch_size):
                sub_rows = rows[i:i + sub_batch_size]
                try:
                    cursor.executemany(
                        f"""
                        INSERT INTO {table_name}(stock_code, date, open, high, low, close, volume, amount)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                            open=VALUES(open),
                            high=VALUES(high),
                            low=VALUES(low),
                            close=VALUES(close),
                            volume=VALUES(volume),
                            amount=VALUES(amount)
                        """,
                        sub_rows,
                    )
                    total += len(sub_rows)
                except Exception as e:
                    print(f"Batch insert failed for {stock_code}: {e}")
        return total


    class SimpleTdxDaykSync:
        def __init__(self):
            self.settings = AppSettings.from_env()
            self.tdx_root = resolve_tdx_root(self.settings.tdx_root_path)

        def get_mysql_latest_date(self) -&gt; str | None:
            if not self.settings.use_mysql or self.settings.mysql is None:
                return None
            conn = mysql_connect(self.settings.mysql)
            try:
                cur = conn.cursor()
                max_dates = []
                for table in ["stock_history_sh", "stock_history_sz", "stock_history_bj", "stock_history"]:
                    try:
                        cur.execute(f"SELECT MAX(date) as max_date FROM {table}")
                        result = cur.fetchone()
                        if result and result[0]:
                            max_dates.append(str(result[0]))
                    except Exception as e:
                        print(f"Warning: Query {table} failed: {e}")
                if max_dates:
                    return max(max_dates)
                return None
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass

        def scan_codes(self):
            paths = TdxLocalPaths(self.tdx_root)
            out = set()
            for sub, prefix in (("sh", "sh"), ("sz", "sz"), ("bj", "bj")):
                d = paths.root / "vipdoc" / sub / "lday"
                if not d.is_dir():
                    continue
                for p in d.glob(f"{prefix}[0-9][0-9][0-9][0-9][0-9][0-9].day"):
                    stem = p.stem.lower()
                    code = stem.replace(prefix, "")[-6:]
                    if len(code) == 6 and code.isdigit():
                        out.add(f"{prefix}{code}")
            return sorted(out)

        @staticmethod
        def normalize_rows(rows: list[dict[str, Any]]) -&gt; list[dict[str, Any]]:
            if not rows:
                return []
            by_date = {}
            for r in rows:
                ds = str(r.get("date") or "")[:10]
                if not ds:
                    continue
                by_date[ds] = r
            out = []
            for ds in sorted(by_date.keys()):
                r = by_date[ds]
                out.append({
                    "date": ds,
                    "open": float(r.get("open") or 0),
                    "high": float(r.get("high") or 0),
                    "low": float(r.get("low") or 0),
                    "close": float(r.get("close") or 0),
                    "volume": float(r.get("volume") or 0),
                    "amount": float(r.get("amount") or 0),
                })
            return out

        def incremental_sync(self, start_date: str | None = None):
            print("=" * 60)
            print("TDX Dayk Incremental Sync")
            print("=" * 60)

            codes = self.scan_codes()
            print(f"Found {len(codes)} codes in TDX")

            if start_date is None:
                start_date = self.get_mysql_latest_date()
            print(f"Start date: {start_date}")

            paths = TdxLocalPaths(self.tdx_root)
            mysql_rows = 0
            codes_ok = 0
            gmin = None
            gmax = None

            mysql_conn = None
            mysql_cur = None
            mysql_buf = []
            mysql_chunk = 120000
            if self.settings.use_mysql and self.settings.mysql is not None:
                mysql_conn = mysql_connect(self.settings.mysql)
                ensure_mysql_schema(mysql_conn)
                mysql_cur = mysql_conn.cursor()

            try:
                for idx, cn_symbol in enumerate(codes, start=1):
                    cn_symbol = SymbolNormalizer.normalize_cn_symbol(cn_symbol)
                    mkt = cn_symbol[:2]
                    code6 = cn_symbol[-6:]
                    p = paths.lday_file_by_market(market=mkt, code6=code6)
                    if not p.is_file():
                        continue
                    rows_raw = read_lday_file(p, tail=None)
                    rows = self.normalize_rows(rows_raw)
                    if not rows:
                        continue

                    if start_date:
                        filtered_rows = [r for r in rows if r["date"] &gt; start_date]
                    else:
                        filtered_rows = rows

                    if not filtered_rows:
                        continue

                    stock_code = SymbolNormalizer.to_db_code(cn_symbol, market="CN")

                    if mysql_conn is not None and mysql_cur is not None:
                        for r in filtered_rows:
                            mysql_buf.append((
                                stock_code, r["date"], r["open"], r["high"], r["low"],
                                r["close"], r["volume"], r["amount"]))
                        if len(mysql_buf) &gt;= mysql_chunk:
                            mysql_rows += _mysql_upsert_chunk_by_code(mysql_conn, mysql_buf, cursor=mysql_cur)
                            mysql_buf.clear()
                            mysql_conn.commit()

                    dates = [r["date"] for r in filtered_rows]
                    current_min = min(dates)
                    current_max = max(dates)
                    if gmin is None or current_min &lt; gmin:
                        gmin = current_min
                    if gmax is None or current_max &gt; gmax:
                        gmax = current_max

                    codes_ok += 1

                    if idx % 100 == 0:
                        print(f"Processed {idx}/{len(codes)}, mysql_rows={mysql_rows}")

                if mysql_conn is not None:
                    if mysql_cur is not None and mysql_buf:
                        mysql_rows += _mysql_upsert_chunk_by_code(mysql_conn, mysql_buf, cursor=mysql_cur)
                    mysql_conn.commit()

            finally:
                try:
                    if mysql_cur is not None:
                        mysql_cur.close()
                except Exception:
                    pass
                try:
                    if mysql_conn is not None:
                        mysql_conn.close()
                except Exception:
                    pass

            print("\n" + "=" * 60)
            print("Sync Complete!")
            print(f"Codes processed: {codes_ok}")
            print(f"MySQL rows written: {mysql_rows}")
            print(f"Date range: {gmin} - {gmax}")
            print("=" * 60)

            return {
                "ok": True,
                "codes_processed": codes_ok,
                "mysql_rows": mysql_rows,
                "date_min": gmin,
                "date_max": gmax,
            }


    def main():
        sync = SimpleTdxDaykSync()
        sync.incremental_sync()


    if __name__ == "__main__":
        main()

finally:
    # 恢复原始文件
    backup_file = base_dir / "app" / "__init__.py.backup"
    if backup_file.exists():
        init_file = base_dir / "app" / "__init__.py"
        if init_file.exists():
            init_file.unlink()
        backup_file.rename(init_file)
        print("\nRestored original app/__init__.py")
