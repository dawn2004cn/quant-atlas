# quant-atlas-mcp

Local FastMCP server for Quant Atlas. Prefer a running Flask API via `QUANT_ATLAS_API_URL`; otherwise tools fall back to in-process services.

| Tool | Purpose |
|------|---------|
| `get_cn_quotes` | Paginated A-share quotes (same path as panorama table) |
| `get_market_panorama` | Gainers / losers / amount / turnover |
| `get_stock_quote` | Single-symbol quote |
| `get_historical_kline` | OHLCV via API or history stack |
| `search_capabilities` | Discover MCP tools + CapabilityRegistry |
| `execute_backtest` | Sandboxed backtest (`STRATEGY_SANDBOX`) |
| `get_portfolio_status` | Paper/live portfolio snapshot |

## Run

```bash
pip install mcp
export QUANT_ATLAS_API_URL=http://127.0.0.1:5000
python scripts/mcp-servers/quant-atlas-mcp/server.py
```

Cursor / Claude `mcpServers`: see `cursor.mcp.json`. Copy into your local MCP config.

Default is **read + backtest only** (no live order tool).
