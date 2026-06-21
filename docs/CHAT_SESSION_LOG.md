# 对话与需求记录（工作区归档）

本文件用于把与 **Quant Atlas / quant-atlas** 相关的重要对话与落地结论记在仓库里，便于回溯与交接。  
**说明**：Cursor 里可能另有完整 Agent 转录（JSONL）；此处为**按主题整理的要点**，不保证逐字逐句与 UI 完全一致。后续会话可在文末按日期**追加**新段落。

---

## 2026-04-11 会话摘要

### 1. 首页与页面体验
- **首页右侧四榜**：涨幅、跌幅、资金（成交额）、换手；对接 `panorama.rankings` 的 `gainers / losers / amounts / turnovers`。
- **参数优化页**、**AI 分析页**：从占位改为与全站风格一致的说明、工作流入口与 API 调用（AI 分析保留 `POST /api/v1/ai/analyze`）。

### 2. 策略回测
- 回测页策略下拉按 **`STRATEGY_REGISTRY_GROUPS`** 分组；开启 Qlib 时增加买入持有类选项，走 `/api/v1/qlib/backtest`。
- **修复**：`CCITurningStrategy` 缺少 `CCIIndicator` 导入导致 500；`DefaultBacktestProvider` 改为 **`StrategyFactory`** 按注册键解析策略；`stock_data` 日期 JSON 安全化。
- **修复**：Jinja 中 `g.items` 与 `dict.items` 冲突，改为 `grp["items"]`，循环变量避免使用 `g`（与 Flask `g` 混淆）。

### 3. 信号旗（选股菜单）
- 新菜单 **信号旗**：用内置注册策略 + 可选 Qlib MA5/20 信号扫描；买点为**最后一根 K 线** `Signal==1`（及 Qlib 金叉）；股票池落盘 **`instance/signal_flag_pool.db`**；按日期查询 API 与页面。
- **异步**：`ENABLE_CELERY=1` 时 `POST /signal-flag/scan` 投递 **`signal_flag_pool_scan`**；消息中心 `task_queued` + Worker 内成功推送（`_suppress_default_task_message` 防重复）；失败走全局 `task_failure`。

### 4. 消息中心与 Celery 管理
- **API**：`GET /system/celery/inspect`、`GET /system/celery/task/<id>`、`POST /system/celery/task/<id>/revoke`（`terminate` 仅管理员）。
- **`task-queue-hint`** 增加 `can_revoke_celery_tasks`、`can_terminate_celery_tasks`。
- **消息中心页**：Worker 快照表、按 ID 查状态、撤销/强杀、事件流卡片「查 Celery」。

### 5. 工程类改动索引（便于 grep）
- `app/presentation/web/templates/index.html` — 四榜与 `loadRankings`
- `app/presentation/web/templates/backtest.html` — `optgroup` / `grp["items"]`
- `app/models/mean_reversion.py` — `CCIIndicator` 导入
- `app/infrastructure/providers/strategies.py` — `StrategyFactory`、`stock_data` 日期
- `app/presentation/api/error_handlers.py` — 未捕获异常打日志
- `app/application/services/signal_flag_service.py`、`app/infrastructure/repositories/signal_flag_pool_repository.py`
- `app/tasks/signal_flag_tasks.py`、`app/presentation/api/routes_v1_signal_flag.py`
- `app/infrastructure/adapters/celery_task_admin.py`、`app/presentation/web/templates/message_center.html`
- `app/core/factory.py` — `iter_registered_instances`
- `app/celery_app.py` — 注册 `signal_flag_tasks`
- `app/infrastructure/messaging/task_message_store.py` — 任务中文标签

---

## 维护约定（可选）

1. **每次重要需求闭环后**：在本文件追加 `## YYYY-MM-DD` 小节，3～10 条要点即可。  
2. **若需逐字记录**：使用 Cursor 对话导出或本地 Agent 转录路径，与本摘要并列保存。  
3. **避免敏感信息**：勿将密码、API Key、Cookie 写入本仓库文件。
