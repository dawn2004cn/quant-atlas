# QMT × Risk Guard × 订单持久化 联调验收清单（DIF P1）

> 用途：仿真/实盘切换前勾选。**自动探针**不宣称实盘通过。

## 自动探针（优先）

```bash
# CLI
python scripts/qmt_risk_guard_probe.py

# 或 API（需登录）
# GET/POST /api/v1/system/qmt-integration-probe
# SPA：观测台 → 执行适配器 →「QMT 联调探针」
```

必过项（`ok=true`）：仿真默认、Risk Guard 开启、单例共用、日回撤阻断、连亏暂停、OrderRequest 仿真下单、Executor 闸门。

## 前置

- [ ] `QMT_ACCOUNT_ID` / `QMT_PATH` 已配置（探针中为可选告警）
- [ ] `QMT_LIVE_SUBMIT=0`（先仿真）再评估开 live
- [ ] `RISK_GUARD_ENABLED=1`
- [ ] Redis 可达（`TASK_MESSAGE_REDIS_URL` 或 `RISK_GUARD_REDIS_URL`）— 探针 `redis_snapshot` 为可选
- [ ] Telegram（可选）：`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
- [ ] `QMT_ORDER_PERSISTENCE=file`（默认）或 `redis`；`off` 关闭落盘

## 风控闸门

- [x] 日回撤≥5% → 阻断（自动探针 `drawdown_gate` / `executor_risk_gate`）
- [x] 连亏≥3 → suspend（`stop_out_gate`）
- [ ] 进程重启后 Redis 快照仍保留（探针 `redis_snapshot`，需 Redis）

## 订单路径

- [x] `OrderRequest` → `QMTExecutor.execute_order_request` → 仿真（`order_request_sim`）
- [x] 与 Risk Guard 单例共用（`risk_guard_singleton`）
- [x] 仿真订单事件落盘 `instance/qmt_orders/`（`QMT_ORDER_PERSISTENCE`）

## 回归命令

```bash
pytest tests/modules/execution/test_qmt_integration_probe.py \
       tests/infrastructure/test_qmt_risk_guard_gate.py \
       tests/modules/execution/test_risk_guard_service.py \
       tests/modules/execution/test_risk_guard_redis_store.py \
       tests/infrastructure/test_borderless_risk_guard_gate.py -q
```

## Telegram 联调

1. 配置 Bot Token / Chat ID
2. 触发 flatten（日回撤）→ 聊天收到 `[QuantAtlas RiskGuard]` 消息
3. 未配置时仅日志，不阻断下单闸门逻辑
