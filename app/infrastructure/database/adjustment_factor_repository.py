from __future__ import annotations
"""Adjustment Factor Repository - 复权因子数据操作."""


from typing import Any

from .adapters import DatabaseAdapter
from ..mappers.symbol_normalizer import SymbolNormalizer


class AdjustmentFactorRepository:
    """Repository for stock adjustment factors (前复权/后复权因子)."""

    def __init__(self, adapter: DatabaseAdapter):
        self._adapter = adapter
        self._ph = adapter.placeholder

    def save_factors(self, stock_code: str, factors: list[dict[str, Any]]) -> None:
        """批量保存或更新复权因子."""
        if not factors:
            return

        normalized = SymbolNormalizer.to_db_code(stock_code)
        table = "stock_adjustment_factor"
        rows = [
            (normalized, f.get("date"), float(f.get("factor", 1.0)))
            for f in factors
        ]

        ph = self._ph
        if self._ph == "?":
            sql = f"""
                INSERT INTO {table} (stock_code, date, factor)
                VALUES ({ph},{ph},{ph})
                ON CONFLICT(stock_code, date) DO UPDATE SET factor=excluded.factor
            """
        else:
            sql = f"""
                INSERT INTO {table} (stock_code, date, factor)
                VALUES (%s,%s,%s)
                ON DUPLICATE KEY UPDATE factor=VALUES(factor)
            """
        self._adapter.execute_many(sql, rows)

    def get_factors(self, stock_code: str, start_date: str = "", end_date: str = "") -> list[dict[str, Any]]:
        """获取复权因子列表."""
        normalized = SymbolNormalizer.to_db_code(stock_code)
        table = "stock_adjustment_factor"
        ph = self._ph

        if start_date and end_date:
            sql = f"""
                SELECT stock_code, date, factor
                FROM {table}
                WHERE stock_code = {ph} AND date >= {ph} AND date <= {ph}
                ORDER BY date
            """
            params = (normalized, start_date, end_date)
        else:
            sql = f"""
                SELECT stock_code, date, factor
                FROM {table}
                WHERE stock_code = {ph}
                ORDER BY date
            """
            params = (normalized,)

        return self._adapter.execute_select(sql, params)

    def get_latest_factor(self, stock_code: str) -> float | None:
        """获取最新复权因子."""
        normalized = SymbolNormalizer.to_db_code(stock_code)
        table = "stock_adjustment_factor"
        ph = self._ph
        sql = f"""
            SELECT factor FROM {table}
            WHERE stock_code = {ph}
            ORDER BY date DESC LIMIT 1
        """
        result = self._adapter.execute_select(sql, (normalized,))
        if result:
            return float(result[0].get("factor", 1.0))
        return None

    def get_factor_on_date(self, stock_code: str, date: str) -> float:
        """获取指定日期的复权因子."""
        normalized = SymbolNormalizer.to_db_code(stock_code)
        table = "stock_adjustment_factor"
        ph = self._ph
        sql = f"""
            SELECT factor FROM {table}
            WHERE stock_code = {ph} AND date <= {ph}
            ORDER BY date DESC LIMIT 1
        """
        result = self._adapter.execute_select(sql, (normalized, date))
        if result:
            return float(result[0].get("factor", 1.0))
        return 1.0

    def delete_factors_before(self, stock_code: str, date: str) -> int:
        """删除指定日期之前的复权因子."""
        normalized = SymbolNormalizer.to_db_code(stock_code)
        table = "stock_adjustment_factor"
        ph = self._ph
        sql = f"DELETE FROM {table} WHERE stock_code = {ph} AND date < {ph}"
        return self._adapter.execute_update(sql, (normalized, date))
