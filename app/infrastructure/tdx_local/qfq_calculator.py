from __future__ import annotations
"""Shared QFQ (前复权) factor calculation from xdxr corporate action data."""


from typing import Any

import pandas as pd


def compute_qfq_factors_from_xdxr(
    rows: list[dict[str, Any]],
    df_xdxr: pd.DataFrame,
) -> list[dict[str, Any]]:
    """基于除权除息数据计算前复权因子。

    Args:
        rows: OHLCV 行列表，每行包含 "date" 和 "close" 字段
        df_xdxr: 除权除息 DataFrame，index 为 date，包含
                 fenhong, songzhuangu, peigu, peigujia 列

    Returns:
        复权因子列表，每项包含 {"date": str, "factor": float}
        factor <= 1.0，最新日期 factor = 1.0
    """
    if not rows:
        return []

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = df.merge(df_xdxr, left_on="date", right_index=True, how="left")
    df[["fenhong", "songzhuangu", "peigu", "peigujia"]] = df[
        ["fenhong", "songzhuangu", "peigu", "peigujia"]
    ].fillna(0)

    df["pre_close"] = df["close"].shift(1)
    is_xdxr = (df["fenhong"] > 0) | (df["songzhuangu"] > 0) | (df["peigu"] > 0)
    df["theoretical_price"] = df["pre_close"]
    df.loc[is_xdxr, "theoretical_price"] = (
        df.loc[is_xdxr, "pre_close"]
        - df.loc[is_xdxr, "fenhong"] / 10
        + (df.loc[is_xdxr, "peigu"] / 10) * df.loc[is_xdxr, "peigujia"]
    ) / (1 + df.loc[is_xdxr, "songzhuangu"] / 10 + df.loc[is_xdxr, "peigu"] / 10)

    df["factor"] = 1.0
    valid_idx = is_xdxr & (df["pre_close"] > 0)
    df.loc[valid_idx, "factor"] = df.loc[valid_idx, "theoretical_price"] / df.loc[valid_idx, "pre_close"]
    df["cum_factor"] = df["factor"].cumprod()

    latest_cum_factor = df["cum_factor"].iloc[-1]
    if latest_cum_factor > 0:
        df["qfq_factor"] = df["cum_factor"] / latest_cum_factor
    else:
        df["qfq_factor"] = 1.0

    factors = []
    for _, row in df.iterrows():
        factors.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "factor": round(float(row["qfq_factor"]), 6),
        })

    return factors


def apply_qfq_to_rows(
    rows: list[dict[str, Any]],
    factors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """将前复权因子应用到 OHLCV 行。

    Args:
        rows: OHLCV 行列表
        factors: 复权因子列表（来自 compute_qfq_factors_from_xdxr）

    Returns:
        复权后的 OHLCV 行列表
    """
    if not rows or not factors:
        return rows

    factor_map = {f["date"]: f["factor"] for f in factors}
    default_factor = factors[-1]["factor"] if factors else 1.0

    adjusted = []
    for row in rows:
        date = row["date"]
        factor = factor_map.get(date, default_factor)
        if factor <= 0:
            factor = 1.0

        adjusted_row = dict(row)
        adjusted_row["open"] = round(row["open"] * factor, 2)
        adjusted_row["high"] = round(row["high"] * factor, 2)
        adjusted_row["low"] = round(row["low"] * factor, 2)
        adjusted_row["close"] = round(row["close"] * factor, 2)
        if "amount" in row:
            adjusted_row["amount"] = round(row["amount"] / factor, 2) if factor > 0 else row["amount"]
        if "volume" in row:
            adjusted_row["volume"] = round(row["volume"] / factor, 2) if factor > 0 else row["volume"]
        adjusted.append(adjusted_row)

    return adjusted


def apply_hfq_to_rows(
    rows: list[dict[str, Any]],
    factors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """将前复权因子转换为后复权 OHLCV（相对最早因子缩放）。"""
    if not rows or not factors:
        return rows

    factor_map = {f["date"]: f["factor"] for f in factors}
    earliest_factor = float(factors[0]["factor"]) if factors else 1.0
    if earliest_factor <= 0:
        earliest_factor = 1.0

    adjusted: list[dict[str, Any]] = []
    for row in rows:
        date = row["date"]
        factor = float(factor_map.get(date, earliest_factor))
        if factor <= 0:
            factor = 1.0

        adjustment_ratio = factor / earliest_factor
        adjusted_row = dict(row)
        adjusted_row["open"] = round(float(row["open"]) * adjustment_ratio, 2)
        adjusted_row["high"] = round(float(row["high"]) * adjustment_ratio, 2)
        adjusted_row["low"] = round(float(row["low"]) * adjustment_ratio, 2)
        adjusted_row["close"] = round(float(row["close"]) * adjustment_ratio, 2)
        if "amount" in row:
            adjusted_row["amount"] = (
                round(float(row["amount"]) / adjustment_ratio, 2)
                if adjustment_ratio > 0
                else row["amount"]
            )
        if "volume" in row:
            adjusted_row["volume"] = (
                round(float(row["volume"]) / adjustment_ratio, 2)
                if adjustment_ratio > 0
                else row["volume"]
            )
        adjusted.append(adjusted_row)

    return adjusted
