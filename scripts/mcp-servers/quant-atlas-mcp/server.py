"""quant-atlas-mcp — local FastMCP tools for kline / backtest / portfolio (REQ-SRS-02).

Run:
  python scripts/mcp-servers/quant-atlas-mcp/server.py

Tools call Quant Atlas application services when the app package is importable;
otherwise they return structured errors (no silent fake fills).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Ensure repo root on path when launched as a script
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    try:
        from mcp import FastMCP  # type: ignore
    except ImportError:  # pragma: no cover

        class FastMCP:  # type: ignore[no-redef]
            """Minimal stub so tool functions remain importable without mcp installed."""

            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def tool(self) -> Any:
                def _decorator(fn: Any) -> Any:
                    return fn

                return _decorator

            def run(self, **kwargs: Any) -> None:
                raise RuntimeError("mcp package not installed")

server = FastMCP(
    "quant-atlas-mcp",
    instructions=(
        "Local Quant Atlas tools: historical kline (Timescale-first), "
        "sandboxed backtest, and portfolio status. Default is read/backtest only."
    ),
)


def _wrap(ok: bool, data: Any, *, evidence: str, confidence: float) -> dict[str, Any]:
    return {
        "ok": ok,
        "data": data,
        "evidence": evidence,
        "confidence": confidence,
    }


@server.tool()
def get_historical_kline(symbol: str, timeframe: str = "1d", limit: int = 100) -> dict[str, Any]:
    """Fetch OHLCV bars for a symbol (prefers Timescale / local history)."""
    try:
        from datetime import date, timedelta

        from app.domain.enums import MarketCode
        from app.infrastructure.providers.history_adapters import get_multi_source_history_provider

        limit = max(1, min(int(limit or 100), 5000))
        end = date.today()
        # Rough calendar window by timeframe; day default.
        days = limit * 2 if str(timeframe).lower() in {"1d", "d", "day"} else max(limit, 30)
        start = end - timedelta(days=days)
        market = MarketCode.CN
        sym = str(symbol or "").strip().upper()
        if sym.endswith(".HK") or (len(sym) == 5 and sym.isdigit()):
            market = MarketCode.HK
        elif any(c.isalpha() for c in sym.replace(".", "")) and not sym.isdigit():
            market = MarketCode.US
        provider = get_multi_source_history_provider()
        bars = provider.get_history(sym, market, start, end) or []
        if limit and len(bars) > limit:
            bars = bars[-limit:]
        source = getattr(provider, "last_source", None) or "unknown"
        return _wrap(
            True,
            {"symbol": sym, "market": market.value, "timeframe": timeframe, "bars": bars, "source": source},
            evidence=f"multi_source_history:{source}",
            confidence=0.85 if bars else 0.4,
        )
    except Exception as exc:
        return _wrap(
            False,
            {"error": str(exc), "symbol": symbol, "timeframe": timeframe, "limit": limit},
            evidence="get_historical_kline_failed",
            confidence=0.2,
        )


@server.tool()
def execute_backtest(strategy_code: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run strategy code via STRATEGY_SANDBOX (process|docker). Does not place live orders.

    Optional params:
      - bars / ohlcv: list of dicts for strict look-ahead bias gate
      - strategy_id, sharpe, max_drawdown, enroll_tournament: enroll into tournament when set
      - bias_passed: explicit override when bars are not provided
    """
    import tempfile
    from pathlib import Path

    params = dict(params or {})
    try:
        from app.infrastructure.sandbox.strategy_docker_runner import (
            StrategySandboxError,
            run_strategy_sandboxed,
        )

        code = strategy_code or "print({'ok': True})\n"
        with tempfile.TemporaryDirectory(prefix="mcp_bt_") as tmp:
            entry = Path(tmp) / "strategy_entry.py"
            entry.write_text(code, encoding="utf-8")
            try:
                result = run_strategy_sandboxed(entry, workdir=Path(tmp))
            except StrategySandboxError as exc:
                return _wrap(False, {"error": str(exc), "params": params}, evidence="sandbox_error", confidence=0.2)

            bias_report: dict[str, Any] | None = None
            bias_passed = bool(params.get("bias_passed"))
            bars = params.get("bars") or params.get("ohlcv")
            if bars is not None:
                try:
                    import pandas as pd

                    from app.domain.backtest.bias_detector import validate_backtest_data

                    df = bars if hasattr(bars, "empty") else pd.DataFrame(bars)
                    report = validate_backtest_data(df, strict=True)
                    bias_passed = report.passed
                    bias_report = {
                        "passed": report.passed,
                        "warnings": report.warnings,
                        "errors": report.errors,
                    }
                except Exception as exc:
                    bias_passed = False
                    bias_report = {"passed": False, "errors": [str(exc)], "warnings": []}

            payload: dict[str, Any] = {
                "status": "completed" if result.success else "failed",
                "sandbox": result.mode,
                "exit_code": result.exit_code,
                "stdout": (result.stdout or "")[:4000],
                "stderr": (result.stderr or "")[:2000],
                "params": {k: v for k, v in params.items() if k not in {"bars", "ohlcv"}},
                "bias_passed": bias_passed,
                "bias_report": bias_report,
            }

            enroll = bool(params.get("enroll_tournament"))
            if enroll and result.success:
                strategy_id = str(params.get("strategy_id") or "mcp.backtest").strip()
                try:
                    from app.modules.strategy.services.tournament.enrollment import (
                        enroll_tournament_candidate,
                    )

                    verdict = enroll_tournament_candidate(
                        strategy_id=strategy_id,
                        sharpe=float(params.get("sharpe") or params.get("estimated_sharpe") or 0.0),
                        max_drawdown=float(params.get("max_drawdown") or 0.0),
                        bias_passed=bias_passed,
                        win_rate=float(params["win_rate"]) if params.get("win_rate") is not None else None,
                        total_return=float(params.get("total_return") or 0.0),
                        sample_start=params.get("sample_start"),
                        sample_end=params.get("sample_end"),
                        metadata={"source": "quant_atlas_mcp"},
                    )
                    payload["tournament"] = {
                        "accepted": verdict.accepted,
                        "reason": verdict.reason,
                        "strategy_id": verdict.strategy_id,
                    }
                except Exception as exc:
                    payload["tournament"] = {"accepted": False, "error": str(exc)}

            return _wrap(
                bool(result.success),
                payload,
                evidence=f"strategy_sandbox:{result.mode}",
                confidence=0.75 if result.success else 0.35,
            )
    except Exception as exc:
        return _wrap(False, {"error": str(exc)}, evidence="execute_backtest_failed", confidence=0.2)


@server.tool()
def get_portfolio_status() -> dict[str, Any]:
    """Return paper/live portfolio snapshot when services are available."""
    try:
        from app.domain.alpha.paper_trading import get_paper_trading_scheduler

        scheduler = get_paper_trading_scheduler()
        accounts = []
        for model_id, account in list(scheduler._accounts.items()):  # noqa: SLF001
            positions = [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_price": p.avg_price,
                    "unrealized_pnl": p.current_pnl,
                }
                for p in account._positions.values()  # noqa: SLF001
            ]
            accounts.append(
                {
                    "model_id": model_id,
                    "status": account.status.value,
                    "cash": account.current_capital,
                    "initial_capital": account.initial_capital,
                    "positions": positions,
                }
            )
        return _wrap(
            True,
            {"accounts": accounts, "queue": scheduler.get_queue_status()},
            evidence="paper_trading_scheduler",
            confidence=0.7 if accounts else 0.5,
        )
    except Exception as exc:
        return _wrap(
            False,
            {"error": str(exc), "positions": [], "pnl": None},
            evidence="get_portfolio_status_unavailable",
            confidence=0.3,
        )

def main() -> None:
    parser = argparse.ArgumentParser(description="Quant Atlas FastMCP server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.transport == "sse":
        server.run(transport="sse", host=args.host, port=args.port)
    else:
        server.run()


if __name__ == "__main__":
    main()
