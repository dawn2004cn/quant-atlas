# AI 如何调用 Quant Atlas

推荐顺序：**MCP（Cursor / Claude）→ 进程内 CapabilityRegistry → REST**。不要让模型自己拼爬虫。

页面和 AI 走同一条行情链：Redis 延迟簿先出数（有真实行情立刻返回），通达信日 K / HQ 实时优先，失败再 HTTP / Timescale / 新浪。生产必须 `CN_QUOTE_LIVE_PULL=1`。

---

## 1. MCP（首选）

本地 FastMCP：`scripts/mcp-servers/quant-atlas-mcp/server.py`。

| 工具 | 用途 | 数据优先级 |
|------|------|------------|
| `get_cn_quotes` | A 股分页行情（与全景扫描表同源） | 通达信 HQ → HTTP `/quotes/page` → Redis 簿 |
| `get_market_panorama` | 涨跌幅 / 成交额 / 换手率榜 | HTTP 全市场扫描（HQ 单次最多 80 只） |
| `get_stock_quote` | 单标的行情 | 通达信 HQ → HTTP `/quotes` → 快照 |
| `get_historical_kline` | 历史 K 线 | 通达信 lday → HQ → HTTP `/history` → Timescale |
| `search_capabilities` | 按自然语言发现 MCP + 平台能力 | 本地目录 + CapabilityRegistry |
| `execute_backtest` | 沙箱回测，不实盘下单 | `STRATEGY_SANDBOX` |
| `get_portfolio_status` | 模拟盘快照 | 进程内调度器 |

### 1.1 启动

```bash
# 终端 1：Flask（页面与 REST）
CN_QUOTE_LIVE_PULL=1 python -c "from app import create_app; create_app().run(host='127.0.0.1', port=5000)"

# 终端 2：MCP
export QUANT_ATLAS_API_URL=http://127.0.0.1:5000
python3 scripts/mcp-servers/quant-atlas-mcp/server.py
```

有本机通达信日 K 时再加：`export TDX_ROOT_PATH=/path/to/tdx`（含 `vipdoc/sh/lday`）。

### 1.2 Cursor

把 `scripts/mcp-servers/quant-atlas-mcp/cursor.mcp.json` 合并进本机 MCP 配置（项目 `.cursor/` 被 gitignore）：

```json
{
  "mcpServers": {
    "quant-atlas": {
      "command": "python3",
      "args": ["scripts/mcp-servers/quant-atlas-mcp/server.py"],
      "env": {
        "QUANT_ATLAS_API_URL": "http://127.0.0.1:5000",
        "TDX_ROOT_PATH": "/path/to/tdx"
      }
    }
  }
}
```

Claude Desktop 同样用 `mcpServers.quant-atlas`。

### 1.3 模型侧怎么问

- 「茅台日 K 最近 60 根」→ `get_historical_kline("600519", "1d", 60)`
- 「平安银行现价」→ `get_stock_quote("000001")`
- 「A 股涨幅前 20」→ `get_cn_quotes(limit=20, sort="change_pct")`
- 「全景涨跌榜」→ `get_market_panorama`
- 不知道有什么工具 → `search_capabilities("行情")`

工具返回 `{ok, data, evidence, confidence}`。`evidence` 以 `tdx:` 开头表示通达信命中。

---

## 2. 进程内工具（本应用 Agent）

LangGraph / Jarvis 走 `CapabilityRegistry` + `CapabilityBridge`（LangChain `@tool`）。MCP 的 `search_capabilities` 会同时检索这份注册表。

新增能力：`@register_capability(...)`，不要再给 Agent 硬编码函数名。

---

## 3. REST（MCP 未接入时）

信封 `{success, data, meta}`。页面与 AI 同源。

| 用途 | 方法 |
|------|------|
| 分页行情 | `GET /api/v1/markets/CN/quotes/page?page=1&page_size=40&sort=change_pct` |
| 全景榜 | `GET /api/v1/markets/CN/panorama` |
| 单票 | `GET /api/v1/markets/CN/quotes?symbol=000001` |
| 日 K | `GET /api/v1/stocks/CN/{symbol}/history?start=2024-01-01&end=2026-01-01` |

v2 同样可用：`/api/v2/*`，信封 `{ok, data, meta}`。

---

## 4. 页面有数据、加载快

页面不另走一套爬虫。首屏契约：

1. **Redis / 内存簿** `quant:cn:quote:book`：有真实行情（`price > 0`）立刻返回，不堵在新浪超时上。
2. **盘中过期（>15 分钟）**：先把旧簿给页面，后台刷新。
3. **簿空**：通达信 HQ（≤80 只一批）→ 新浪涨跌停 → 腾讯。
4. **日 K**：本地 `vipdoc/*/lday/*.day` → HQ `get_security_bars`。
5. 生产禁止用零价种子当行情。CI 才允许 `CN_QUOTE_LIVE_PULL=0`。
6. 前端 SWR：`keepPreviousData`、`dedupingInterval=2s`、切页不闪空表；全景过滤 `price > 0`。

环境变量：

| 变量 | 默认 | 作用 |
|------|------|------|
| `CN_QUOTE_LIVE_PULL` | `1` | 允许页面/MCP 拉通达信与新浪 |
| `TDX_ROOT_PATH` | 空 | 本机通达信 vipdoc |
| `QUANT_ATLAS_API_URL` | 空 | MCP 先打运行中的 Flask |
| `HISTORY_PREFER_TIMESERIES` | `1` | 通达信之后才落到 Timescale |

---

## 5. 不要用的路径

- 页面路径不要 AkShare / 东财 clist（易 502）
- 不要把零价种子当行情
- `akshare-mcp` / `wind-mcp` / `ifind-mcp` 是外部数据代理，不是本平台交易面
- 不要让模型直接打通达信 IP；走 MCP / REST / CapabilityRegistry
