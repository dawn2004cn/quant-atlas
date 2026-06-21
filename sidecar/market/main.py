"""FastAPI read-only market sidecar — proxies Flask monolith for OpenAPI/async edge.

Run:
  pip install -r sidecar/market/requirements.txt
  FLASK_UPSTREAM=http://127.0.0.1:5000 uvicorn sidecar.market.main:app --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

FLASK_UPSTREAM = os.getenv("FLASK_UPSTREAM", "http://127.0.0.1:5000").rstrip("/")
REQUEST_TIMEOUT = float(os.getenv("SIDECAR_HTTP_TIMEOUT", "10"))

app = FastAPI(
    title="Quant Atlas Market Sidecar",
    version="0.1.0",
    description="Read-only quote edge; upstream is Flask /api/v1",
)


class PriceQuote(BaseModel):
    symbol: str
    market: str = "CN"
    quote: dict[str, Any] = Field(default_factory=dict)
    source: str = "flask_upstream"


class HealthResponse(BaseModel):
    status: str
    upstream: str
    upstream_ok: bool


async def _fetch_json(path: str) -> dict[str, Any]:
    url = f"{FLASK_UPSTREAM}{path}"
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=502, detail="upstream_invalid_json")
        return payload


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    upstream_ok = False
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(f"{FLASK_UPSTREAM}/system/health")
            upstream_ok = r.status_code == 200
    except httpx.HTTPError:
        upstream_ok = False
    return HealthResponse(
        status="ok" if upstream_ok else "degraded",
        upstream=FLASK_UPSTREAM,
        upstream_ok=upstream_ok,
    )


@app.get("/price/{symbol}", response_model=PriceQuote)
async def price(
    symbol: str,
    market: str = Query(default="CN", pattern="^(CN|US|HK)$"),
) -> PriceQuote:
    sym = symbol.strip().upper()
    if not sym:
        raise HTTPException(status_code=400, detail="symbol_required")

    try:
        data = await _fetch_json(f"/api/v1/markets/{market}/quotes?symbol={sym}&limit=1")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail="upstream_error") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="upstream_unreachable") from exc

    stocks = data.get("data", {}).get("stocks") if isinstance(data.get("data"), dict) else data.get("stocks")
    if not stocks:
        stocks = data.get("stocks", [])
    quote = stocks[0] if isinstance(stocks, list) and stocks else {}

    return PriceQuote(symbol=sym, market=market, quote=quote if isinstance(quote, dict) else {})
