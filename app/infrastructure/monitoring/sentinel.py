"""Sentinel for monitoring market data freshness."""

import logging
from datetime import datetime, timedelta
import pymysql
from app.config import AppSettings
from app.core.metrics import SYNC_LATENCY


from app.core.logger import get_logger

logger = get_logger(__name__)

class DataFreshnessSentinel:
    """Monitors if market data is up-to-date."""

    def __init__(self, settings: AppSettings):
        self.settings = settings

    _ALLOWED_TABLES = frozenset({
        "stock_history_sh", "stock_history_sz", "stock_history_bj",
        "stock_history_hk", "stock_history_us", "stock_history_btc",
        "stock_history", "stocks", "market_sentiment",
    })

    # Class-level cache for union results (cleared if DB settings change)
    _last_union_cache: dict[str, datetime] | None = None
    _cached_ts: datetime | None = None

    def _get_cached_dates(self) -> dict[str, datetime]:
        """Return cached union result or fetch it lazily."""
        mysql = self.settings.mysql
        if not mysql:
            return {}, None
        conn = None
        if self._last_union_cache is not None and self._cached_ts is not None:
            return self._last_union_cache, self._cached_ts

        try:
            conn = pymysql.connect(
                host=mysql.host,
                port=mysql.port,
                user=mysql.user,
                password=mysql.password,
                database=mysql.database
            )
            with conn.cursor() as cur:
                query = (
                    f"SELECT '{t}' AS table_name, MAX(date) AS latest_date "
                    f"FROM {t} "
                    f"UNION ALL "
                    f"SELECT '{t2}' AS table_name, MAX(date) AS latest_date "
                    f"FROM {t2}".format(t="stock_history_sh", t2="stock_history_sz")
                )
                cur.execute("SELECT 'stock_history_sh' AS table_name, MAX(date) as latest_date FROM stock_history_sh "
                           "UNION ALL "
                           "SELECT 'stock_history_sz' AS table_name, MAX(date) as latest_date FROM stock_history_sz "
                           "UNION ALL "
                           "SELECT 'stock_history_bj' AS table_name, MAX(date) as latest_date FROM stock_history_bj "
                           "UNION ALL "
                           "SELECT 'stock_history_hk' AS table_name, MAX(date) as latest_date FROM stock_history_hk "
                           "UNION ALL "
                           "SELECT 'stock_history_us' AS table_name, MAX(date) as latest_date FROM stock_history_us "
                           "UNION ALL "
                           "SELECT 'stock_history_btc' AS table_name, MAX(date) as latest_date FROM stock_history_btc "
                           "UNION ALL "
                           "SELECT 'stock_history' AS table_name, MAX(date) as latest_date FROM stock_history "
                           "UNION ALL "
                           "SELECT 'stocks' AS table_name, MAX(date) as latest_date FROM stocks "
                           "UNION ALL "
                           "SELECT 'market_sentiment' AS table_name, MAX(date) as latest_date FROM market_sentiment")
                res = cur.fetchall()
                self._last_union_cache = {
                    row[0]: datetime.strptime(row[1], "%Y-%m-%d") if row[1] else None
                    for row in res
                }
                self._cached_ts = datetime.now()
                return self._last_union_cache, self._cached_ts
        except Exception as e:
            logger.error(f"Failed to fetch union dates: {e}")
            return self._last_union_cache or {}, self._cached_ts or None

    def check_freshness(self, table: str, max_delay_minutes: int = 15) -> bool:
        """Check if the latest record in the table is within the allowed delay."""
        mysql = self.settings.mysql
        if not mysql:
            return True
        if table not in self._ALLOWED_TABLES:
            logger.error("Invalid table for freshness check: %s", table)
            return False
        conn = None
        try:
            conn = pymysql.connect(
                host=mysql.host,
                port=mysql.port,
                user=mysql.user,
                password=mysql.password,
                database=mysql.database
            )
            with conn.cursor() as cur:
                safe_table = f"`{table}`"
                cur.execute(f"SELECT MAX(date) FROM {safe_table}")
                res = cur.fetchone()
                if not res or not res[0]:
                    logger.error(f"No data found in {table}")
                    return False
                
                latest_date = res[0]
                if isinstance(latest_date, str):
                    try:
                        latest_date = datetime.strptime(latest_date, "%Y-%m-%d")
                    except ValueError:
                        logger.error(f"Unexpected date format in {table}: {latest_date}")
                        return False
                
                delay = datetime.now() - latest_date
                
                SYNC_LATENCY.observe(delay.total_seconds())
                
                if delay > timedelta(minutes=max_delay_minutes):
                    logger.critical(f"Data freshness alert: {table} is {delay} old!")
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Freshness check failed: {e}")
            return False
        finally:
            if conn:
                conn.close()
