from __future__ import annotations
"""Multi-market history data fetcher using AkShare."""



from typing import Any

import pandas as pd


from app.core.logger import get_logger

logger = get_logger(__name__)


def fetch_hk_daily(symbol: str, start: str, end: str) -> tuple[list[dict[str, Any]], str]:
    """获取港股历史日K数据（前复权）

    Args:
        symbol: 股票代码，如 "0700.HK"
        start: 开始日期 "YYYY-MM-DD"
        end: 结束日期 "YYYY-MM-DD"

    Returns:
        (数据列表, 错误信息)
    """
    try:
        import akshare as ak

        df = ak.hk_stock_hist(
            symbol=symbol,
            start_date=start.replace("-", ""),
            end_date=end.replace("-", ""),
            adjust="qfq",
        )
        if df is None or df.empty:
            return [], "AkShare返回空数据"

        df = df.rename(
            columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
            }
        )
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        records = df[["date", "open", "high", "low", "close", "volume", "amount"]].to_dict("records")
        return records, ""
    except Exception as e:
        logger.warning("fetch_hk_daily failed for %s: %s", symbol, e)
        return [], str(e)


def fetch_us_daily(symbol: str, start: str, end: str) -> tuple[list[dict[str, Any]], str]:
    """获取美股历史日K数据（前复权）

    Args:
        symbol: 股票代码，如 "AAPL", "TSLA"
        start: 开始日期 "YYYY-MM-DD"
        end: 结束日期 "YYYY-MM-DD"

    Returns:
        (数据列表, 错误信息)
    """
    try:
        import akshare as ak

        df = ak.stock_us_hist(
            symbol=symbol,
            period="daily",
            start_date=start.replace("-", ""),
            end_date=end.replace("-", ""),
            adjust="qfq",
        )
        if df is None or df.empty:
            return [], "AkShare返回空数据"

        df = df.rename(
            columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
            }
        )
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        records = df[["date", "open", "high", "low", "close", "volume", "amount"]].to_dict("records")
        return records, ""
    except Exception as e:
        logger.warning("fetch_us_daily failed for %s: %s", symbol, e)
        return [], str(e)


def fetch_crypto_daily(symbol: str, start: str, end: str) -> tuple[list[dict[str, Any]], str]:
    """获取加密货币历史日K数据

    Args:
        symbol: 交易对，如 "BTCUSDT", "ETHUSDT"
        start: 开始日期 "YYYY-MM-DD"
        end: 结束日期 "YYYY-MM-DD"

    Returns:
        (数据列表, 错误信息)
    """
    try:
        import akshare as ak

        # 提取基础币种，如 "BTC" from "BTCUSDT"
        base = symbol.replace("USDT", "").replace("USD", "")

        df = ak.currency_hist(
            symbol=base,
            start_date=start.replace("-", ""),
            end_date=end.replace("-", ""),
        )
        if df is None or df.empty:
            return [], "AkShare返回空数据"

        df = df.rename(
            columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
            }
        )
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        records = df[["date", "open", "high", "low", "close", "volume", "amount"]].to_dict("records")
        return records, ""
    except Exception as e:
        logger.warning("fetch_crypto_daily failed for %s: %s", symbol, e)
        return [], str(e)


def fetch_market_daily(
    market: str,
    symbol: str,
    start: str,
    end: str,
) -> tuple[list[dict[str, Any]], str]:
    """统一的历史数据获取接口

    Args:
        market: 市场代码 "HK", "US", "CRYPTO"
        symbol: 股票/交易对代码，如 "0700.HK", "AAPL", "BTCUSDT"
        start: 开始日期
        end: 结束日期

    Returns:
        (数据列表, 错误信息)
    """
    if market == "HK":
        return fetch_hk_daily(symbol, start, end)
    elif market == "US":
        return fetch_us_daily(symbol, start, end)
    elif market == "CRYPTO":
        return fetch_crypto_daily(symbol, start, end)
    else:
        return [], f"不支持的市场: {market}"


def to_db_code(symbol: str, market: str) -> str:
    """将行情代码转换为存储代码

    Args:
        symbol: 原始代码，如 "0700.HK", "AAPL", "BTCUSDT"
        market: 市场代码 "HK", "US", "CRYPTO"

    Returns:
        存储代码，如 "hk0700", "usAAPL", "btcBTC"
    """
    if market == "HK":
        code = symbol.replace(".HK", "")
        return f"hk{code}"
    elif market == "US":
        return f"us{symbol}"
    elif market == "CRYPTO":
        code = symbol.replace("USDT", "").replace("USD", "")
        return f"btc{code}"
    return symbol
