"""quant-atlas-mcp — local FastMCP tools for kline / backtest / portfolio (REQ-SRS-02).

Run:
  python scripts/mcp-servers/quant-atlas-mcp/server.py

Tools call Quant Atlas application services when the app package is importable;
otherwise they return structured errors (no silent fake fills).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_log = logging.getLogger("quant-atlas-mcp")

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
        "Quant Atlas local tools. CN daily K-line prefers Tongdaxin vipdoc/lday then HQ; "
        "CN realtime prefers Tongdaxin HQ. HTTP / Timescale are fallbacks. Read + backtest only."
    ),
)

_MCP_CATALOG: tuple[dict[str, str], ...] = (
    {"name": "get_cn_quotes", "domain": "market_data", "description": "A股分页行情，优先通达信实时HQ"},
    {"name": "get_market_panorama", "domain": "market_data", "description": "全景行情：涨跌幅/成交额/换手率榜"},
    {"name": "get_stock_quote", "domain": "market_data", "description": "单标的行情，优先通达信实时"},
    {"name": "get_historical_kline", "domain": "market_data", "description": "历史K线，A股日K优先通达信lday/HQ"},
    {"name": "search_capabilities", "domain": "system", "description": "按自然语言检索平台能力与 MCP 工具"},
    {"name": "execute_backtest", "domain": "backtest", "description": "沙箱回测，不实盘下单"},
    {"name": "get_portfolio_status", "domain": "portfolio", "description": "模拟盘组合快照"},
)


def _wrap(ok: bool, data: Any, *, evidence: str, confidence: float) -> dict[str, Any]:
    return {
        "ok": ok,
        "data": data,
        "evidence": evidence,
        "confidence": confidence,
    }


def _api_base() -> str:
    return os.environ.get("QUANT_ATLAS_API_URL", "").strip().rstrip("/")


def _unwrap_envelope(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload and payload.get("data") is not None:
        return payload["data"]
    return payload


def _http_json(path: str, timeout: float = 8.0) -> Any | None:
    """GET JSON from a running Quant Atlas API. None if URL unset or request fails."""
    base = _api_base()
    if not base:
        return None
    url = f"{base}{path if path.startswith('/') else '/' + path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "quant-atlas-mcp"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _http_data(path: str, timeout: float = 8.0) -> Any | None:
    payload = _http_json(path, timeout=timeout)
    if payload is None:
        return None
    return _unwrap_envelope(payload)


def _infer_market(symbol: str) -> str:
    sym = str(symbol or "").strip().upper()
    if sym.endswith(".HK") or (len(sym) == 5 and sym.isdigit()):
        return "HK"
    if any(ch.isalpha() for ch in sym.replace(".", "")) and not sym.isdigit():
        return "US"
    return "CN"


def _is_cn_daily(market: str, timeframe: str) -> bool:
    return market == "CN" and str(timeframe or "1d").lower() in {"1d", "d", "day", "daily"}


def _priced_rows(rows: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            if float(row.get("price") or row.get("close") or 0) > 0:
                out.append(row)
        except (TypeError, ValueError):
            continue
    return out


def _tdx_daily_kline(symbol: str, start: Any, end: Any, limit: int) -> tuple[list[dict[str, Any]], str]:
    """CN 日 K：本地 vipdoc/lday 优先，再通达信 HQ。失败返回空，不抛给调用方。"""
    try:
        from datetime import date as date_cls

        from app.modules.data.services.tdx_ohlcv_reader import fetch_tdx_daily_bars

        start_d = start if isinstance(start, date_cls) else None
        end_d = end if isinstance(end, date_cls) else None
        bars = fetch_tdx_daily_bars(symbol, start_d, end_d) or []
        if bars:
            if limit and len(bars) > limit:
                bars = bars[-limit:]
            for row in bars:
                row.setdefault("source", "tdx_file")
            return bars, "tdx_file"
    except Exception:
        _log.debug("tdx daily lday miss %s", symbol, exc_info=True)
    try:
        from app.modules.data.services.pytdx_market_data_service import get_pytdx_market_data_service

        svc = get_pytdx_market_data_service()
        if svc.is_available():
            raw = svc.get_daily_bars(symbol, count=limit) or []
            if raw:
                return raw, "tdx_hq"
    except Exception:
        _log.debug("tdx daily hq miss %s", symbol, exc_info=True)
    return [], ""


def _tdx_realtime_quotes(symbols: list[str]) -> list[dict[str, Any]]:
    """通达信 HQ 实时。端口已绑定时走 PytdxMarketDataService；否则直连 HQ。"""
    if not symbols:
        return []
    try:
        from app.modules.data.services.pytdx_market_data_service import get_pytdx_market_data_service

        svc = get_pytdx_market_data_service()
        if svc.is_available():
            rows = _priced_rows(svc.get_quotes(symbols) or [])
            if rows:
                for row in rows:
                    row.setdefault("source", "tdx")
                return rows
    except Exception:
        _log.debug("tdx realtime port miss", exc_info=True)
    try:
        from app.infrastructure.providers.cn_tdx_provider import TdxRealTimeProvider

        return _priced_rows(TdxRealTimeProvider().get_quotes(symbols) or [])
    except Exception:
        _log.debug("tdx realtime hq miss", exc_info=True)
        return []


def _cn_quote_universe() -> list[str]:
    try:
        from app.modules.market_data.services.market_service import _CN_PAGE_UNIVERSE

        return list(_CN_PAGE_UNIVERSE)
    except Exception:
        _log.debug("cn quote universe fallback", exc_info=True)
        return ["600519", "000001", "000858", "601318", "600036"]


def _sort_quote_rows(items: list[dict[str, Any]], sort: str, order: str, limit: int) -> list[dict[str, Any]]:
    key = sort if sort in {"change_pct", "price", "amount", "volume"} else "change_pct"
    reverse = str(order).lower() != "asc"
    ranked = sorted(items, key=lambda row: float(row.get(key) or 0), reverse=reverse)
    return ranked[:limit]


@server.tool()
def get_historical_kline(symbol: str, timeframe: str = "1d", limit: int = 100) -> dict[str, Any]:
    """Fetch OHLCV. CN daily bars prefer Tongdaxin lday, then HQ, then HTTP / Timescale."""
    from datetime import date, timedelta

    limit = max(1, min(int(limit or 100), 5000))
    end = date.today()
    days = limit * 2 if str(timeframe).lower() in {"1d", "d", "day", "daily"} else max(limit, 30)
    start = end - timedelta(days=days)
    sym = str(symbol or "").strip()
    market = _infer_market(sym)
    code = "".join(ch for ch in sym if ch.isdigit())[-6:] or sym
    if _is_cn_daily(market, timeframe):
        tdx_bars, tdx_source = _tdx_daily_kline(sym, start, end, limit)
        if tdx_bars:
            return _wrap(
                True,
                {"symbol": code, "market": market, "timeframe": timeframe, "bars": tdx_bars, "source": tdx_source},
                evidence=f"tdx:{tdx_source}",
                confidence=0.92,
            )
    qs = urllib.parse.urlencode({"start": start.isoformat(), "end": end.isoformat(), "max_points": limit})
    http = _http_data(f"/api/v1/stocks/{market}/{code}/history?{qs}")
    if isinstance(http, dict) and (http.get("items") or http.get("bars") or http.get("history")):
        bars = http.get("items") or http.get("bars") or http.get("history") or []
        return _wrap(
            True,
            {"symbol": code, "market": market, "timeframe": timeframe, "bars": bars, "source": "http"},
            evidence="http:/api/v1/stocks/history",
            confidence=0.9 if bars else 0.4,
        )
    try:
        from app.domain.enums import MarketCode
        from app.infrastructure.providers.history_adapters import get_multi_source_history_provider

        provider = get_multi_source_history_provider()
        bars = provider.get_history(sym, MarketCode(market), start, end) or []
        if limit and len(bars) > limit:
            bars = bars[-limit:]
        source = getattr(provider, "last_source", None) or "unknown"
        return _wrap(
            True,
            {"symbol": sym, "market": market, "timeframe": timeframe, "bars": bars, "source": source},
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
def get_cn_quotes(
    limit: int = 40,
    sort: str = "change_pct",
    order: str = "desc",
    board_filter: str = "all",
) -> dict[str, Any]:
    """Paginated A-share quotes. Prefers Tongdaxin HQ on the liquid universe, then HTTP / Sina."""
    limit = max(1, min(int(limit or 40), 200))
    tdx_rows = _sort_quote_rows(_tdx_realtime_quotes(_cn_quote_universe()), sort, order, limit)
    if tdx_rows:
        return _wrap(
            True,
            {"items": tdx_rows, "total": len(tdx_rows), "source": "tdx", "filter": board_filter},
            evidence="tdx:realtime_hq",
            confidence=0.9,
        )
    qs = urllib.parse.urlencode(
        {"page": 1, "page_size": limit, "sort": sort, "order": order, "filter": board_filter}
    )
    http = _http_data(f"/api/v1/markets/CN/quotes/page?{qs}")
    if isinstance(http, dict):
        items = http.get("items") or []
        priced = [row for row in items if isinstance(row, dict) and float(row.get("price") or 0) > 0]
        return _wrap(
            True,
            {**http, "items": priced or items},
            evidence="http:/api/v1/markets/CN/quotes/page",
            confidence=0.9 if priced else 0.45,
        )
    try:
        from types import SimpleNamespace

        from app.modules.market_data.services.cn_quote_snapshot import CnQuoteSnapshot, hydrate_page_snapshot
        from app.modules.market_data.services.market_service import MarketApplicationService

        svc = MarketApplicationService(
            market_provider=SimpleNamespace(),
            industry_provider=SimpleNamespace(),
            stock_cache=None,
        )
        snap = CnQuoteSnapshot(ttl_seconds=45)
        hydrate_page_snapshot(snap, svc)
        page = snap.query_page(
            page=1,
            page_size=limit,
            sort_key=sort,
            sort_order=order,
            board_filter=board_filter,
        )
        items = [row for row in (page.get("items") or []) if isinstance(row, dict)]
        priced = [row for row in items if float(row.get("price") or 0) > 0]
        page["items"] = priced or items
        return _wrap(
            True,
            page,
            evidence="inprocess:hydrate_page_snapshot",
            confidence=0.8 if priced else 0.4,
        )
    except Exception as extra:
        return _wrap(False, {"error": str(extra), "items": []}, evidence="get_cn_quotes_failed", confidence=0.2)


@server.tool()
def get_market_panorama() -> dict[str, Any]:
    """Market panorama rankings (gainers / losers / amount / turnover)."""
    http = _http_data("/api/v1/markets/CN/panorama")
    if isinstance(http, dict):
        rankings = http.get("rankings") or http
        return _wrap(True, http if "rankings" in http else {"rankings": rankings}, evidence="http:/api/v1/markets/CN/panorama", confidence=0.85)
    try:
        from types import SimpleNamespace

        from app.domain.enums import MarketCode
        from app.modules.market_data.services.market_service import MarketApplicationService

        svc = MarketApplicationService(
            market_provider=SimpleNamespace(),
            industry_provider=SimpleNamespace(),
            stock_cache=None,
        )
        dto = svc.get_panorama(MarketCode.CN)
        payload = dto.model_dump() if hasattr(dto, "model_dump") else dict(dto)
        rankings = {
            "gainers": payload.get("gainers") or [],
            "losers": payload.get("losers") or [],
            "amounts": payload.get("amounts") or [],
            "turnovers": payload.get("turnovers") or [],
        }
        return _wrap(True, {"rankings": rankings}, evidence="inprocess:get_panorama", confidence=0.75 if rankings["gainers"] else 0.4)
    except Exception as extra:
        return _wrap(False, {"error": str(extra), "rankings": {}}, evidence="get_market_panorama_failed", confidence=0.2)


@server.tool()
def get_stock_quote(symbol: str, market: str = "CN") -> dict[str, Any]:
    """Single-symbol quote. CN prefers Tongdaxin HQ, then HTTP / delayed book."""
    market = (market or "CN").strip().upper()
    code = str(symbol or "").strip()
    if market == "CN":
        tdx_rows = _tdx_realtime_quotes([code])
        if tdx_rows:
            return _wrap(
                True,
                {"stocks": tdx_rows, "count": len(tdx_rows), "source": "tdx"},
                evidence="tdx:realtime_hq",
                confidence=0.92,
            )
    qs = urllib.parse.urlencode({"symbol": code})
    http = _http_data(f"/api/v1/markets/{market}/quotes?{qs}")
    if isinstance(http, dict):
        return _wrap(True, http, evidence=f"http:/api/v1/markets/{market}/quotes", confidence=0.85)
    try:
        from types import SimpleNamespace

        from app.domain.enums import MarketCode
        from app.modules.market_data.services.cn_quote_snapshot import get_cn_quote_snapshot, hydrate_page_snapshot
        from app.modules.market_data.services.market_service import MarketApplicationService

        svc = MarketApplicationService(
            market_provider=SimpleNamespace(),
            industry_provider=SimpleNamespace(),
            stock_cache=None,
        )
        snap = get_cn_quote_snapshot()
        hydrate_page_snapshot(snap, svc)
        hits, missing = snap.lookup_rows([code])
        if hits:
            return _wrap(True, {"stocks": hits, "count": len(hits)}, evidence="inprocess:quote_snapshot", confidence=0.8)
        extra = svc.list_quotes(MarketCode(market), [code]) or []
        return _wrap(
            bool(extra),
            {"stocks": extra, "count": len(extra), "missing": missing},
            evidence="inprocess:list_quotes",
            confidence=0.7 if extra else 0.35,
        )
    except Exception as extra:
        return _wrap(False, {"error": str(extra), "symbol": code}, evidence="get_stock_quote_failed", confidence=0.2)


@server.tool()
def search_capabilities(query: str = "", limit: int = 12) -> dict[str, Any]:
    """Search MCP tools and in-app CapabilityRegistry by natural language."""
    limit = max(1, min(int(limit or 12), 50))
    q = (query or "").strip().lower()
    items: list[dict[str, str]] = []
    for row in _MCP_CATALOG:
        blob = f"{row['name']} {row['description']} {row['domain']}".lower()
        if not q or q in blob:
            items.append({**row, "source": "mcp"})
    try:
        import app.core.capability_declarations_market_alpha  # noqa: F401
        import app.core.capability_declarations_portfolio_risk  # noqa: F401
        from app.core.capability_registry import get_capability_registry

        caps = get_capability_registry().search(query, limit=limit) if query else get_capability_registry().list_all()[:limit]
        for cap in caps:
            items.append(
                {
                    "name": cap.name,
                    "domain": cap.domain,
                    "description": cap.description,
                    "source": "capability_registry",
                }
            )
    except Exception:
        pass
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in items:
        if item["name"] in seen:
            continue
        seen.add(item["name"])
        unique.append(item)
    return _wrap(True, {"items": unique[:limit], "query": query}, evidence="mcp_catalog+capability_registry", confidence=0.9 if unique else 0.5)


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
