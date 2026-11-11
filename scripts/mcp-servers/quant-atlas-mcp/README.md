# quant-atlas-mcp

Local FastMCP server for Quant Atlas. CN daily K-line and realtime quotes prefer Tongdaxin (`vipdoc` lday, then HQ). HTTP (`QUANT_ATLAS_API_URL`) and in-process Sina/Timescale are fallbacks.

| Tool | Purpose |
|------|---------|
| `get_cn_quotes` | Paginated A-share quotes (TDX HQ universe first) |
| `get_market_panorama` | Gainers / losers / amount / turnover |
| `get_stock_quote` | Single-symbol quote (TDX HQ first) |
| `get_historical_kline` | OHLCV; CN daily prefers TDX lday/HQ |
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
