# IBKR / CTP 联调清单（仿真 + dry-run + 真会话）

> 近中期 **A 股现货执行以 QMT 为准**。IBKR（美股）/ CTP（期货）为 P2 扩展轨。  
> 默认**不放置真券商单**：`*_ALLOW_REAL_ORDERS=0`。实盘 TWS 端口另需 `IBKR_CONFIRM_LIVE_ACCOUNT=1`；CTP 真单另需 `CTP_CONFIRM_LIVE_ACCOUNT=1`。

## 开关

| 变量 | 默认 | 含义 |
|------|------|------|
| `IBKR_ALLOW_SIMULATION` | 1 | 进程内仿真账本 |
| `IBKR_LIVE_SUBMIT` | 0 | live 路径（默认 dry-run 落盘） |
| `IBKR_ALLOW_REAL_ORDERS` | 0 | 真单闸门（`ib_insync.placeOrder` 或注入 session） |
| `IBKR_CONFIRM_LIVE_ACCOUNT` | 0 | 实盘 TWS/Gateway 端口（7496/4001）二次确认 |
| `IBKR_HOST` / `IBKR_PORT` / `IBKR_CLIENT_ID` | 127.0.0.1 / **7497** / 1 | paper TWS；实盘改 7496 并开 CONFIRM |
| `CTP_ALLOW_SIMULATION` | 1 | 仿真 |
| `CTP_LIVE_SUBMIT` | 0 | live dry-run |
| `CTP_ALLOW_REAL_ORDERS` | 0 | 真单闸门（注入 trader/session） |
| `CTP_CONFIRM_LIVE_ACCOUNT` | 0 | CTP 真单二次确认（无 paper 端口启发式） |
| `CTP_MD_FRONT` / `CTP_TD_FRONT` | 空 | `tcp://host:port` 探针 |
| `CTP_BROKER_ID` / `CTP_USER_ID` / `CTP_PASSWORD` | 空 | 凭证是否配置（不落日志明文） |

可选 SDK：`pip install -e ".[brokers]"`（`ib_insync`）。CTP 请注入 `CTPAdapter(session=...)` 或 `trader=`（`ReqOrderInsert`），或后续接 vnpy/openctp 登录工厂。

## 自动探针

```bash
GET/POST /api/v1/system/ibkr-ctp-integration-probe
GET /api/v1/system/execution-adapters
pytest tests/infrastructure/test_ibkr_ctp_contracts.py -q
```

期望：`ok=true`；仿真 `IBKR_SIM_*` / `CTP_SIM_*`；dry-run `IBKR_LIVE_*` / `CTP_LIVE_*`；注入会话 `IBKR_TWS_*` / `CTP_TD_*` 写入 `instance/ibkr_orders/`、`instance/ctp_orders/`。

## 人工验收

1. TWS paper（7497）可达 → `ibkr.detail.connection.tcp_ok=true`
2. CTP 前置可达 → `ctp.detail.connection.td_ok`
3. Risk Guard 对 `ibkr_live` / `ctp_live` 回撤可阻断
4. paper + `ALLOW_REAL=1` + `ib_insync`：可对 TWS paper 下单（小手数）
5. 端口 7496 且未开 `IBKR_CONFIRM_LIVE_ACCOUNT` → `ibkr_live_account_not_confirmed`
6. CTP 未开 `CTP_CONFIRM_LIVE_ACCOUNT` → `ctp_live_account_not_confirmed`

## 边界

- A 股现货：继续 QMT 清单 `docs/ops/QMT_RISK_GUARD_CHECKLIST.md`
- CTP 完整登录握手 / 回报线程：需注入 trader，不内置券商环境脚本
- Telegram：真单成功后尝试告警（未配置 token 则跳过）
