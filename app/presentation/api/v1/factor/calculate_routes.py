"""Factor online calculation routes.

Computes common technical factors (SMA, EMA, RSI, MACD, Bollinger)
from historical bar data on the fly.
"""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

import numpy as np
import pandas as pd

from app.application.errors import ValidationError
from app.presentation.api.common import ok_resource
from app.presentation.api.v1_context import ApiV1Context
from app.presentation.api.decorators import service_fallback, require_role


def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=1).mean()


def _ema(series: pd.Series, window: int) -> pd.Series:
    return series.ewm(span=window, adjust=False, min_periods=1).mean()


def _rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def _macd(series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema12 = _ema(series, 12)
    ema26 = _ema(series, 26)
    macd_line = ema12 - ema26
    signal_line = _ema(macd_line, 9)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bollinger(
    series: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = _sma(series, window)
    std = series.rolling(window=window, min_periods=1).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


_DEFAULT_PERIOD = 60
_SUPPORTED_FACTORS = frozenset({"sma", "ema", "rsi", "macd", "bollinger"})


def register_factor_calculate_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    @blueprint.get("/factor/calculate")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("factor_orthogonalization_service")
    def factor_calculate():
        symbol = (request.args.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required", details={"param": "symbol"})

        raw_factors = (request.args.get("factors") or "").strip()
        period = int(request.args.get("period", str(_DEFAULT_PERIOD)))
        market = (request.args.get("market") or "CN").strip()

        selected = [f.strip().lower() for f in raw_factors.split(",") if f.strip()]
        if not selected:
            selected = sorted(_SUPPORTED_FACTORS)
        unknown = [f for f in selected if f not in _SUPPORTED_FACTORS]
        if unknown:
            raise ValidationError(
                "unsupported_factors",
                details={"unsupported": unknown, "supported": sorted(_SUPPORTED_FACTORS)},
            )

        market_service = getattr(ctx, "market_service", None)
        if market_service is None:
            from app.infrastructure.database.history_repository import HistoryRepository
            from app.infrastructure.database.adapter import get_adapter

            adapter = get_adapter()
            repo = HistoryRepository(adapter)
            bars = repo.get_history_latest(symbol, limit=max(period, 120))
        else:
            bars = market_service.get_history_bars(
                symbol=symbol,
                market=market,
                start_date=None,
                end_date=None,
                count=max(period, 120),
            )

        if not bars:
            raise ValidationError(
                "no_data",
                details={"symbol": symbol, "message": "No history bars found"},
            )

        df = pd.DataFrame(bars)
        col_map = {}
        for c in df.columns:
            cl = c.strip().lower()
            if cl in ("close", chr(25910), chr(30424), chr(20215)):
                col_map[c] = "close"
            elif cl in ("open", chr(24320), chr(30424), chr(24320)):
                col_map[c] = "open"
            elif cl in ("high", chr(26368), chr(39640), chr(26368)):
                col_map[c] = "high"
            elif cl in ("low", chr(26368), chr(20302), chr(26368)):
                col_map[c] = "low"
            elif cl in ("volume", chr(25104), chr(37327), chr(20132), "vol"):
                col_map[c] = "volume"
            elif cl in ("date", chr(26085), chr(26399), chr(20132), chr(26131), chr(26399), "trade_date", "datetime"):
                col_map[c] = "date"
        df.rename(columns=col_map, inplace=True)

        if "close" not in df.columns:
            raise ValidationError(
                "missing_close_column",
                details={"columns": list(df.columns)},
            )

        close = pd.to_numeric(df["close"], errors="coerce").dropna().tail(period)
        if len(close) < 2:
            raise ValidationError(
                "insufficient_data",
                details={"symbol": symbol, "count": len(close)},
            )

        result: dict[str, list] = {}
        dates = df.get("date", pd.Series([], dtype=str)).astype(str).tolist()

        if "sma" in selected:
            for w in (5, 10, 20, 60):
                label = f"sma_{w}"
                vals = _sma(close, w)
                result[label] = _round_list(vals.tolist())

        if "ema" in selected:
            for w in (5, 12, 20, 26):
                label = f"ema_{w}"
                vals = _ema(close, w)
                result[label] = _round_list(vals.tolist())

        if "rsi" in selected:
            vals = _rsi(close, 14)
            result["rsi_14"] = _round_list(vals.tolist())

        if "macd" in selected:
            macd_line, signal, hist = _macd(close)
            result["macd_line"] = _round_list(macd_line.tolist())
            result["macd_signal"] = _round_list(signal.tolist())
            result["macd_histogram"] = _round_list(hist.tolist())

        if "bollinger" in selected:
            upper, mid, lower = _bollinger(close)
            result["bollinger_upper"] = _round_list(upper.tolist())
            result["bollinger_mid"] = _round_list(mid.tolist())
            result["bollinger_lower"] = _round_list(lower.tolist())

        return ok_resource(
            resource={
                "symbol": symbol,
                "market": market,
                "period": period,
                "dates": dates[-len(close):],
                "close": _round_list(close.tolist()),
                "factors": result,
            },
            resource_key="factor_calculation",
            enable_legacy_alias=False,
        )


def _round_list(values: list, decimals: int = 4) -> list:
    return [round(v, decimals) if isinstance(v, float) and not np.isnan(v) else None for v in values]
