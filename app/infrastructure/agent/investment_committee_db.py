from __future__ import annotations

"""AI 投资委员会 - MySQL 交易记录"""


from datetime import datetime
from typing import Any

from pymysql.cursors import DictCursor

from app.core.logger import get_logger
from app.core.utils.sql_utils import quote_identifier, validate_identifier
from app.infrastructure.database.mysql_client import mysql_connect
from app.infrastructure.database.mysql_settings import MysqlSettings

logger = get_logger(__name__)

_TABLE_SQL = quote_identifier("ai_trading_records")
def _get_mysql_settings() -> MysqlSettings | None:
    """获取 MySQL 配置"""
    try:
        from app.config import get_settings
        settings = get_settings()
        if settings.mysql:
            return settings.mysql
        return None
    except Exception as e:
        logger.warning("获取 MySQL 配置失败: %s", e, exc_info=True)
        return None


class TradeRecorder:
    """交易记录 MySQL 存储"""

    TABLE_NAME = "ai_trading_records"

    def __init__(self):
        if not validate_identifier(self.TABLE_NAME):
            raise ValueError(f"invalid table name: {self.TABLE_NAME}")
        self._mysql = _get_mysql_settings()
        if self._mysql:
            self._ensure_table()

    def _ensure_table(self) -> None:
        """确保表存在"""
        if not self._mysql:
            logger.info("MySQL 未配置，跳过创建表")
            return
        conn = mysql_connect(self._mysql)
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {_TABLE_SQL} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    committee_id VARCHAR(50) DEFAULT 'default',
                    symbol VARCHAR(20) NOT NULL,
                    name VARCHAR(100),
                    strategy VARCHAR(50) NOT NULL,
                    direction VARCHAR(10) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    quantity INT NOT NULL,
                    amount DECIMAL(15, 2) NOT NULL,
                    trade_time DATETIME NOT NULL,
                    pnl DECIMAL(15, 2) DEFAULT 0,
                    pnl_pct DECIMAL(10, 2) DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'holding',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_symbol (symbol),
                    INDEX idx_status (status),
                    INDEX idx_trade_time (trade_time)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
        except Exception as e:
            logger.warning("创建交易记录表失败: %s", e, exc_info=True)
        finally:
            cur.close()
            conn.close()

    def save_trade(self, trade: dict[str, Any], committee_id: str = "default") -> int:
        """保存交易记录"""
        if not self._mysql:
            logger.info("MySQL 未配置，跳过保存交易")
            return -1
        conn = mysql_connect(self._mysql)
        if not conn:
            return -1
        try:
            cur = conn.cursor()
            cur.execute(f"""
                INSERT INTO {_TABLE_SQL}
                (committee_id, symbol, name, strategy, direction, price, quantity, amount, trade_time, pnl, pnl_pct, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                committee_id,
                trade.get("symbol", ""),
                trade.get("name", ""),
                trade.get("strategy", ""),
                trade.get("direction", ""),
                trade.get("price", 0),
                trade.get("quantity", 0),
                trade.get("amount", 0),
                trade.get("trade_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                trade.get("pnl", 0),
                trade.get("pnl_pct", 0),
                trade.get("status", "holding"),
            ))
            conn.commit()
            return cur.lastrowid
        except Exception as e:
            logger.warning("保存交易记录失败: %s", e, exc_info=True)
            return -1
        finally:
            cur.close()
            conn.close()

    def get_open_positions(self, committee_id: str = "default") -> list[dict]:
        """获取当前持仓"""
        if not self._mysql:
            return []
        conn = mysql_connect(self._mysql)
        if not conn:
            return []
        try:
            cur = conn.cursor(DictCursor)
            cur.execute(f"""
                SELECT * FROM {_TABLE_SQL}
                WHERE committee_id = %s AND status = 'holding'
                ORDER BY trade_time DESC
            """, (committee_id,))
            return cur.fetchall()
        except Exception as e:
            logger.warning("获取持仓失败: %s", e, exc_info=True)
            return []
        finally:
            cur.close()
            conn.close()

    def get_trade_history(self, symbol: str = None, limit: int = 100) -> list[dict]:
        """获取交易历史"""
        if not self._mysql:
            return []
        conn = mysql_connect(self._mysql)
        if not conn:
            return []
        try:
            cur = conn.cursor(DictCursor)
            if symbol:
                cur.execute(f"""
                    SELECT * FROM {_TABLE_SQL}
                    WHERE symbol = %s
                    ORDER BY trade_time DESC
                    LIMIT %s
                """, (symbol, limit))
            else:
                cur.execute(f"""
                    SELECT * FROM {_TABLE_SQL}
                    ORDER BY trade_time DESC
                    LIMIT %s
                """, (limit,))
            return cur.fetchall()
        except Exception as e:
            logger.warning("获取交易历史失败: %s", e, exc_info=True)
            return []
        finally:
            cur.close()
            conn.close()

    def get_summary(self, committee_id: str = "default") -> dict:
        """获取交易汇总"""
        if not self._mysql:
            return {}
        conn = mysql_connect(self._mysql)
        if not conn:
            return {}
        try:
            cur = conn.cursor(DictCursor)
            cur.execute(f"""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN direction = 'buy' THEN amount ELSE 0 END) as total_buy,
                    SUM(CASE WHEN direction = 'sell' THEN amount ELSE 0 END) as total_sell,
                    SUM(pnl) as total_pnl,
                    AVG(pnl_pct) as avg_pnl_pct
                FROM {_TABLE_SQL}
                WHERE committee_id = %s AND status LIKE 'closed_%%'
            """, (committee_id,))
            return cur.fetchone() or {}
        except Exception as e:
            logger.warning("获取汇总失败: %s", e, exc_info=True)
            return {}
        finally:
            cur.close()
            conn.close()


class MarketDataProvider:
    """市场数据提供者 - 为投资委员会提供数据"""

    def __init__(self):
        self._tdx_provider = None
        self._akshare_history = None
        self._tdx_initialized = False

    def _init_tdx(self):
        if not self._tdx_initialized:
            try:
                from app.infrastructure.providers.cn_tdx_provider import create_tdx_provider
                self._tdx_provider = create_tdx_provider()
                self._tdx_initialized = True
            except Exception as e:
                logger.warning("investment_committee_db.py._init_tdx: %s", e)

    def get_index_data(self, index_code: str, days: int = 250) -> Any:
        """获取指数数据"""
        from datetime import datetime, timedelta

        # 优先从 TDX 获取
        try:
            self._init_tdx()
            if self._tdx_provider:
                # 提取代码
                code = index_code.split(".")[0][-6:]
                start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                rows = self._tdx_provider.get_stock_history(
                    symbol=code,
                    start=start_date
                )
                if rows:
                    return self._rows_to_df(rows)
        except Exception as e:
            logger.warning("TDX 获取失败: %s", e, exc_info=True)

        # 备选：AkShare
        try:
            from datetime import datetime, timedelta

            from app.infrastructure.providers.cn_akshare_history import fetch_cn_daily_hfq

            rows, status = fetch_cn_daily_hfq(
                index_code[-6:],
                (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
                datetime.now().strftime("%Y-%m-%d")
            )
            if rows:
                return self._rows_to_df(rows)
        except Exception as e:
            logger.warning("AkShare 获取失败: %s", e, exc_info=True)

        return None

    def _rows_to_df(self, rows: list[dict]) -> Any:
        """转换为 DataFrame 格式"""
        import pandas as pd
        df = pd.DataFrame(rows)
        # 添加技术指标计算需要的列
        if "high" not in df.columns and "Open" in df.columns:
            df["High"] = df["Open"]
            df["Low"] = df["Open"]
            df["Close"] = df["Close"]
        return df

    def get_stock_pool(self, limit: int = 100) -> list[dict]:
        """获取候选股票池"""
        try:
            from app.infrastructure.providers.cn_tdx_provider import create_tdx_provider
            if not self._tdx_provider:
                self._tdx_provider = create_tdx_provider()

            from app.domain.enums import MarketCode
            symbols = self._tdx_provider.get_all_symbols(MarketCode.CN)

            pool = []
            for sym in symbols[:limit]:
                rows = self._tdx_provider.get_stock_history(sym, limit=1)
                if rows:
                    pool.append({
                        "symbol": sym,
                        "name": sym,
                        "market": sym[:2],
                        "close": rows[-1].get("close", 0),
                        "volume": rows[-1].get("volume", 0),
                    })
            return pool
        except Exception as e:
            logger.warning("获取股票池失败: %s", e, exc_info=True)
            return []


# 导出
__all__ = ["TradeRecorder", "MarketDataProvider"]
