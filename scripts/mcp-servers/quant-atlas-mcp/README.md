# quant-atlas-mcp

Local FastMCP server exposing Quant Atlas tools (SRS REQ-SRS-02):

| Tool | Purpose |
|------|---------|
| `get_historical_kline` | OHLCV via market facade / history stack |
| `execute_backtest` | Sandboxed backtest entry (`STRATEGY_SANDBOX`) |
| `get_portfolio_status` | Paper/live portfolio snapshot |

## Run

```bash
pip install mcp
python scripts/mcp-servers/quant-atlas-mcp/server.py
```

Cursor `mcpServers` example:

```json
{
  "quant-atlas": {
    "command": "python",
    "args": ["scripts/mcp-servers/quant-atlas-mcp/server.py"]
  }
}
```

Default is **read + backtest only** (no live order tool).
