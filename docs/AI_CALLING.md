# AI 如何调用 Quant Atlas

推荐顺序：**MCP（Cursor / Claude / ChatGPT）→ 进程内 CapabilityRegistry → REST**。不要让模型自己拼爬虫。

## 1. MCP（首选）

本仓库已有本地 FastMCP：`scripts/mcp-servers/quant-atlas-mcp/server.py`。

| 工具 | 用途 |
|------|------|
| `get_cn_quotes` | A 股分页行情（与全景扫描表同源） |
| `get_market_panorama` | 涨跌幅 / 成交额 / 换手率榜 |
| `get_stock_quote` | 单标的行情 |
| `get_historical_kline` | 历史 K 线 |
| `search_capabilities` | 按自然语言发现 MCP + 平台能力 |
| `execute_backtest` | 沙箱回测，不实盘下单 |
| `get_portfolio_status` | 模拟盘快照 |

A 股日 K / 实时：**通达信优先**（本地 `vipdoc/*/lday/*.day`，再 HQ），HTTP / Timescale / 新浪为后备。全景涨跌榜仍走全市场扫描（HTTP），因为 HQ 单次最多 80 只。

先起 Flask，再挂 MCP（K 线与单票行情先 TDX，失败才 HTTP / in-process）：

```bash
# 终端 1
CN_QUOTE_LIVE_PULL=1 python -c "from app import create_app; create_app().run(host='127.0.0.1', port=5000)"

# 终端 2
export QUANT_ATLAS_API_URL=http://127.0.0.1:5000
python3 scripts/mcp-servers/quant-atlas-mcp/server.py
```

Cursor：把 `scripts/mcp-servers/quant-atlas-mcp/cursor.mcp.json` 合并进本机 MCP 配置（项目 `.cursor/` 目录被 gitignore）。Claude Desktop 同样用 `mcpServers.quant-atlas`。

## 2. 进程内工具（本应用 Agent）

LangGraph / Jarvis 走 `CapabilityRegistry` + `CapabilityBridge`（LangChain `@tool`）。MCP 的 `search_capabilities` 会同时检索这份注册表。

新增能力：`@register_capability(...)`，不要再给 Agent 硬编码函数名。

## 3. REST

MCP 未接入时，模型可调：

- `GET /api/v1/markets/CN/quotes/page`
- `GET /api/v1/markets/CN/panorama`
- `GET /api/v1/markets/CN/quotes?symbol=000001`
- `GET /api/v1/stocks/CN/{symbol}/history`

信封：`{success, data, meta}`。生产 `CN_QUOTE_LIVE_PULL=1`。服务端历史读链对 A 股日 K 同样是通达信 lday / HQ 优先。

## 4. 不要用的路径

- 页面路径不要 AkShare / 东财 clist（易 502）
- 不要把零价种子当行情
- `akshare-mcp` / `wind-mcp` / `ifind-mcp` 是外部数据代理，不是本平台交易面
