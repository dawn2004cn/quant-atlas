
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复 tdx_dayk_sync_service.py 中的 get_mysql_latest_date 函数"""

from pathlib import Path

file_path = Path("app/application/services/tdx_dayk_sync_service.py")
content = file_path.read_text(encoding='utf-8')

old_func = '''    def get_mysql_latest_date(self) -> str | None:
        """获取MySQL中最新的日期"""
        if not self._settings.use_mysql or self._settings.mysql is None:
            return None
        
        conn = mysql_connect(self._settings.mysql)
        try:
            cur = conn.cursor()
            max_dates = []
            # 查询所有市场表的最新日期
            for table in ["stock_history_sh", "stock_history_sz", "stock_history_bj", "stock_history"]:
                try:
                    cur.execute(f"SELECT MAX(date) as max_date FROM {table}")
                    result = cur.fetchone()
                    if result and result[0]:
                        max_dates.append(str(result[0]))
                except Exception as e:
                    logger.warning(f"查询 {table} 失败: {e}")
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
                pass'''

new_func = '''    def get_mysql_latest_date(self) -> str | None:
        """获取MySQL中最新的有效日期"""
        from datetime import datetime
        if not self._settings.use_mysql or self._settings.mysql is None:
            return None
        
        conn = mysql_connect(self._settings.mysql)
        try:
            cur = conn.cursor()
            max_dates = []
            for table in ["stock_history_sh", "stock_history_sz", "stock_history_bj", "stock_history"]:
                try:
                    cur.execute(f"SELECT MAX(date) as max_date FROM {table}")
                    result = cur.fetchone()
                    if result and result[0]:
                        date_str = str(result[0])
                        try:
                            datetime.strptime(date_str, "%Y-%m-%d")
                            max_dates.append(date_str)
                        except ValueError:
                            logger.warning(f"Invalid date in {table}: {date_str}")
                except Exception as e:
                    logger.warning(f"查询 {table} 失败: {e}")
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
                pass'''

if old_func in content:
    print("Found the old function, replacing...")
    content = content.replace(old_func, new_func)
    file_path.write_text(content, encoding='utf-8')
    print("Done!")
else:
    print("Could not find the old function.")
    # Let's try to find it by searching for parts
    print("\nLooking for function signature...")
    if "def get_mysql_latest_date" in content:
        print("Found function signature")
