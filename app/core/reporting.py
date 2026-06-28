from __future__ import annotations
"""Backtest reporting and analysis tools."""


from typing import Any
from ..domain.entities import BacktestReport

class BacktestAnalyzer:
    """Analyze backtest results and generate metrics."""

    @staticmethod
    def calculate_win_rate(trades: list[dict[str, Any]]) -> float:
        """Calculate the percentage of profitable trades."""
        sell_trades = [t for t in trades if t.get("action") == "SELL"]
        if not sell_trades:
            return 0.0

        wins = len([t for t in sell_trades if t.get("profit", 0) > 0])
        return round((wins / len(sell_trades)) * 100, 2)

    @staticmethod
    def generate_summary_text(report: BacktestReport) -> str:
        """Generate a human-readable text summary of the backtest."""
        m = report.metrics
        win_rate = BacktestAnalyzer.calculate_win_rate(report.trades)

        lines = [
            f"📊 Backtest Report: {report.strategy} on {report.symbol}",
            f"📅 Period: {report.period.get('start')} to {report.period.get('end')}",
            "-" * 40,
            f"💰 Final Value:    {m.get('final_value'):,.2f}",
            f"📈 Total Return:   {m.get('total_return'):.2f}%",
            f"胜 Win Rate:      {win_rate}%",
            f"📉 Max Drawdown:   {m.get('max_drawdown', 0):.2f}%",
            f"🔢 Sharpe Ratio:   {m.get('sharpe_ratio', 0):.2f}",
            f"🤝 Total Trades:   {len(report.trades)}",
            "-" * 40
        ]

        if report.trades:
            last_trade = report.trades[-1]
            lines.append(f"🏁 Last Action: {last_trade.get('action')} @ {last_trade.get('price')}")

        return "\n".join(lines)
