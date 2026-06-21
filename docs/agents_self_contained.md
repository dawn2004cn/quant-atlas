# 多智能体研究（自包含说明）

## 归属

- **实现目录**：`app/agents/research/`
  - `state.py`：图状态、`RESEARCH_GRAPH_NODES`、辩论轮次常量
  - `react_loop.py`：ReAct 工具循环
  - `catalog.py`：策略 id 列表（`StrategyFactory`）
  - `graph.py`：Supervisor → 六 Analyst → Bull/Bear → 风险辩论 → Risk Manager
  - `report.py`：`package_full_report`
- **服务入口**：`app/agents/trading_agents_service.py`（`run_research`）
- **兼容层**：`app/agents/custom_trading_workflow.py` 仅 re-export，旧代码 `from app.agents.custom_trading_workflow import ...` 仍可用

## 与 TradingAgents-CN 的关系

- **运行时**：主应用 **不** `import tradingagents`，也不需将 `TradingAgents-CN-lastest` 加入 `PYTHONPATH`。
- **仓库中的 `TradingAgents-CN-lastest/`**：仅可作参考或后续删除；产品逻辑以 `app/agents/research` 为准。

## 六分析师（业务角色）

| 节点 id | 角色 |
|---------|------|
| `macro_analyst` | 宏观 |
| `fundamental_analyst` | 基本面 |
| `technical_analyst` | 技术面 |
| `sentiment_analyst` | 情绪 / 资金偏好 |
| `backtest_optimizer` | 回测优化（多策略 `run_backtest`） |
| `risk_manager` | 终审风险 |

另含 Supervisor、Bull/Bear、Risk-Seeking/Risk-Averse 辩论节点，见 `RESEARCH_GRAPH_NODES`。

## 基本面与研报数据（A 股）

- **基础层**：`app/infrastructure/providers/cn_akshare_fundamentals.py` + `FundamentalDataAccess`（AkShare 东财财务摘要、三表、研报列表；东财限频/字段变更时可能部分失败）。
- **工具**：`get_cn_financial_statements`、`get_cn_research_reports`（见 `app/tools/quant_tools.py`），由 **Fundamental Analyst** 绑定；非 A 股标的会返回 `market_not_cn`。
- **HTTP**：`/api/v1/stocks/CN/{symbol}/fundamentals` 与 `.../research-reports`（需登录）。

## 新闻与情绪（借鉴 CN）

- **规则相关性分**：`app/services/news/relevance_filter.py`（TradingAgents-CN `news_filter` 思路）。
- **工具**：`get_stock_news` 使用 **SQLite 新闻归档**（`instance/news_archive.db`）与远程 `NewsProvider` 增量合并，并排序打分；`probe_ticker` 用于校验标的覆盖。REST：`/api/v1/stocks/{market}/{symbol}/news-archive`。
