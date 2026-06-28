from __future__ import annotations
"""Trading metrics calculations for backtest performance evaluation."""


from datetime import datetime
from typing import Any

import pandas as pd

from app.infrastructure.compute.native_compute import (
    calculate_max_drawdown as _rust_max_drawdown,
    calculate_sharpe_ratio as _rust_sharpe_ratio,
    calculate_annual_return as _rust_annual_return,
)


def calculate_trading_metrics(
    initial_capital: float,
    final_value: float,
    portfolio_values: list[float],
    start_date: datetime,
    end_date: datetime,
) -> dict[str, float]:
    """
    Calculate trading performance metrics.

    Args:
        initial_capital: Initial capital amount
        final_value: Final portfolio value
        portfolio_values: List of portfolio values over time
        start_date: Backtest start date
        end_date: Backtest end date

    Returns:
        Dict containing total_return, annual_return, max_drawdown, sharpe_ratio
    """
    total_return = (final_value - initial_capital) / initial_capital * 100

    total_days = (end_date - start_date).days
    annual_return = _rust_annual_return(initial_capital, final_value, float(total_days))

    max_drawdown = _rust_max_drawdown(portfolio_values)

    sharpe_ratio = _rust_sharpe_ratio(portfolio_values)

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
    }


def execute_trading_strategy(
    data: pd.DataFrame,
    signal_column: str,
    initial_capital: float,
    start_idx: int = 1,
) -> dict[str, Any]:
    """
    Execute trading strategy based on signals.

    Args:
        data: DataFrame with columns: date, close, [signal_column]
        signal_column: Column name containing signals (1=buy, -1=sell, 0=hold)
        initial_capital: Initial capital amount
        start_idx: Starting index for execution

    Returns:
        Dict with final_value, trades list, portfolio_values list
    """
    capital = initial_capital
    shares = 0.0
    buy_price = 0.0
    trades = []
    portfolio_values = []

    for i in range(start_idx, len(data)):
        row = data.iloc[i]
        prev_row = data.iloc[i - 1]

        date = row["date"]
        price = row["close"]
        signal = row[signal_column]
        prev_signal = prev_row[signal_column]

        if signal == 1 and prev_signal != 1:
            if capital > 0:
                shares = capital / price
                buy_price = price
                capital = 0.0
                trade_date = date.strftime("%Y-%m-%d") if isinstance(date, datetime) else str(date)
                trades.append(
                    {
                        "date": trade_date,
                        "action": "BUY",
                        "price": price,
                        "qty": shares,
                        "amount": shares * price,
                        "profit": 0.0,
                    }
                )
        elif signal == -1 and prev_signal != -1:
            if shares > 0:
                capital = shares * price
                profit = capital - shares * buy_price
                trade_date = date.strftime("%Y-%m-%d") if isinstance(date, datetime) else str(date)
                trades.append(
                    {
                        "date": trade_date,
                        "action": "SELL",
                        "price": price,
                        "qty": shares,
                        "amount": capital,
                        "profit": profit,
                    }
                )
                shares = 0.0
                buy_price = 0.0

        current_value = capital + shares * price
        portfolio_values.append(current_value)

    final_value = capital + shares * data.iloc[-1]["close"] if shares > 0 else capital

    return {
        "final_value": final_value,
        "trades": trades,
        "portfolio_values": portfolio_values,
    }
