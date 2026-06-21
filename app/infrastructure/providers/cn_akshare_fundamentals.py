from __future__ import annotations
"""A 股财务摘要、三表（东财按报告期）与研报列表 —— AkShare 封装（数据基础层）。"""


from typing import Any

import pandas as pd

from ...core.logger import get_logger
from ...infrastructure.mappers.symbol_normalizer import SymbolNormalizer

logger = get_logger(__name__)

DEFAULT_MAX_TABLE_ROWS = 32
DEFAULT_MAX_REPORTS = 40


def _em_exchange_symbol(code_6: str) -> str:
    """东财三表接口使用 ``SH600519`` / ``SZ000001`` 形态。"""
    c = SymbolNormalizer.normalize_code(code_6)
    if SymbolNormalizer.market_id(c) == 1:
        prefix = "SH"
    elif SymbolNormalizer.market_id(c) == 0:
        prefix = "SZ"
    else:
        prefix = "BJ"
    return f"{prefix}{c}"


def _df_to_jsonable_records(df: pd.DataFrame | None, max_rows: int) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    sub = df.head(int(max_rows)).copy()
    for col in sub.columns:
        if pd.api.types.is_datetime64_any_dtype(sub[col]):
            sub[col] = sub[col].dt.strftime("%Y-%m-%d")
    sub = sub.where(pd.notnull(sub), None)
    return sub.to_dict(orient="records")


class CnAkShareFundamentalsProvider:
    """对齐 TradingAgents-CN 思路：AkShare 东财财务 + 研报；失败按表隔离，不拖垮整包。

    Tushare 作为降级备源（当 AkShare 接口失败时按表尝试）。
    """

    def __init__(self, *, max_table_rows: int = DEFAULT_MAX_TABLE_ROWS) -> None:
        self._max_table_rows = max_table_rows
        self._tushare_available = self._check_tushare()

    def _check_tushare(self) -> bool:
        try:
            import os, tushare as ts  # noqa: PLC0415
            token = os.getenv("TUSHARE_TOKEN", "")
            if not token:
                return False
            ts.set_token(token)
            ts.pro_api().trade_cal(exchange="SSE", start_date="20260101", end_date="20260101")
            return True
        except Exception:
            return False

    def _tushare_financial(
        self, code: str, fields_map: dict[str, list[str]]
    ) -> dict[str, list[dict[str, Any]]]:
        """通过 Tushare 按表类型拉取财务数据。返回 {table_name: [rows]}。"""
        import tushare as ts  # noqa: PLC0415
        import os

        results: dict[str, list[dict[str, Any]]] = {}
        try:
            token = os.getenv("TUSHARE_TOKEN", "")
            ts.set_token(token)
            pro = ts.pro_api()
            code6 = SymbolNormalizer.normalize_code(code)
            for table_name, (api_name, fields) in fields_map.items():
                try:
                    if table_name == "balance_sheet":
                        df = pro.balancesheet(ts_code=f"{code6}.SH", fields=",".join(fields))
                    elif table_name == "profit_sheet":
                        df = pro.income(ts_code=f"{code6}.SH", fields=",".join(fields))
                    elif table_name == "cash_flow_sheet":
                        df = pro.cashflow(ts_code=f"{code6}.SH", fields=",".join(fields))
                    else:
                        df = pro.fina_indicator(ts_code=f"{code6}.SH", fields=",".join(fields))
                    results[table_name] = _df_to_jsonable_records(df, self._max_table_rows)
                except Exception:
                    results[table_name] = []
        except Exception as e:
            logger.warning("cn_akshare_fundamentals.py._tushare_financial: %s", e)
        return results

    def fetch_financial_bundle(self, symbol_input: str) -> dict[str, Any]:
        import akshare as ak  # noqa: PLC0415 延迟加载，避免进程冷启动过慢

        code = SymbolNormalizer.normalize_code(symbol_input)
        em_sym = _em_exchange_symbol(code)
        errors: dict[str, str] = {}
        mr = self._max_table_rows

        def _run(key: str, fn: Any) -> list[dict[str, Any]]:
            try:
                df = fn()
                return _df_to_jsonable_records(df, mr)
            except Exception as exc:  # noqa: BLE001
                logger.warning("cn_akshare_fundamentals %s failed for %s: %s", key, code, exc)
                errors[key] = f"{type(exc).__name__}: {exc}"
                return []

        abstract = _run("financial_abstract", lambda: ak.stock_financial_abstract(symbol=code))
        balance = _run("balance_sheet", lambda: ak.stock_balance_sheet_by_report_em(symbol=em_sym))
        profit = _run("profit_sheet", lambda: ak.stock_profit_sheet_by_report_em(symbol=em_sym))
        cash = _run("cash_flow_sheet", lambda: ak.stock_cash_flow_sheet_by_report_em(symbol=em_sym))

        if self._tushare_available:
            if not balance or not profit or not cash:
                tushare_fields = {
                    "balance_sheet": ("balancesheet", ["ann_date", "end_date", "total_assets", "total_liab", "total_curr_assets", "total_fixed_assets"]),
                    "profit_sheet": ("income", ["ann_date", "end_date", "revenue", "biz_cost", "profit_total", "n_income"]),
                    "cash_flow_sheet": ("cashflow", ["ann_date", "end_date", "n_cashflow_act", "n_cashflows_inv_act", "n_cashflows_fin_act"]),
                }
                ts_res = self._tushare_financial(code, tushare_fields)
                if not balance and ts_res.get("balance_sheet"):
                    balance = ts_res["balance_sheet"]
                    errors["balance_sheet_fallback"] = "Tushare"
                if not profit and ts_res.get("profit_sheet"):
                    profit = ts_res["profit_sheet"]
                    errors["profit_sheet_fallback"] = "Tushare"
                if not cash and ts_res.get("cash_flow_sheet"):
                    cash = ts_res["cash_flow_sheet"]
                    errors["cash_flow_sheet_fallback"] = "Tushare"

        source = "akshare_em"
        if "Tushare" in str(errors):
            source = "akshare_em + tushare_fallback"

        return {
            "symbol": code,
            "em_symbol": em_sym,
            "financial_abstract": abstract,
            "balance_sheet": balance,
            "profit_sheet": profit,
            "cash_flow_sheet": cash,
            "errors": errors,
            "source": source,
        }

    def fetch_research_reports(
        self, symbol_input: str, *, limit: int = 10
    ) -> tuple[list[dict[str, Any]], str | None]:
        import akshare as ak  # noqa: PLC0415

        code = SymbolNormalizer.normalize_code(symbol_input)
        cap = max(1, min(int(limit), 100))
        try:
            df = ak.stock_research_report_em(symbol=code)
            
            # Convert DF to list of dicts
            if df is None or df.empty:
                return [], None
            
            rows = df.head(cap).to_dict("records")
            return rows, None
        except Exception as exc:  # noqa: BLE001
            logger.warning("cn_akshare research reports failed for %s: %s", code, exc)
            return [], f"{type(exc).__name__}: {exc}"

    def fetch_stock_industry(self, symbol: str) -> str:
        """Fetch stock industry using AkShare."""
        import akshare as ak
        try:
            code = SymbolNormalizer.normalize_code(symbol)
            df = ak.stock_individual_info_em(symbol=code)
            # Find industry row
            industry_row = df[df['item'] == '行业']
            if not industry_row.empty:
                return str(industry_row.iloc[0]['value'])
            # Sometimes it's '所属行业'
            industry_row = df[df['item'] == '所属行业']
            if not industry_row.empty:
                return str(industry_row.iloc[0]['value'])
            return "未知"
        except Exception as e:
            logger.warning(f"fetch_stock_industry failed for {symbol}: {e}")
            return "未知"

