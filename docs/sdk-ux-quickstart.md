# SDK & UX 快速上手

Quant Atlas 在阶段 33–43 落地了四项 UX 能力，可通过 **HTTP API**、**Web 看板** 或 **`app.sdk`** 脚本访问。

## SDK 入口

```python
from app.sdk import create_client

client = create_client()
```

## 1. 统一归因

```python
report = client.attribution.report(
    strategy_name="demo",
    period="30d",
    positions=[{"symbol": "600519", "value": 100000, "return_pct": 2.0, "sector": "白酒"}],
    factor_exposures={"momentum": 0.15},
    factor_returns={"momentum": 0.04},
    include_slippage=False,
)
print(report.summary)
```

- API：`GET /api/v1/attribution/report?period=30d`
- 看板：`/attribution-dashboard`

## 2. 智能预警中心

```python
feed = client.alerts.list(min_level="warning")
summary = client.alerts.summary()

# 推送到 Webhook / 钉钉 / 邮件 / 微信
client.alerts.dispatch(min_level="critical", channel_names=["dingtalk"])
```

- API：`GET /api/v1/system/alerts`、`POST /api/v1/system/alerts/dispatch`
- 看板：`/alert-center`
- Beat：`ALERT_DISPATCH_CELERY_BEAT=1`

## 3. 策略快照与回滚

```python
snap = client.snapshots.capture(strategy_name="momentum_v1", label="prod")
result = client.snapshots.rollback(snap.id, apply_settings=True, apply_code=False)
```

- API：`POST/GET /api/v1/strategy/snapshots`、`POST .../<id>/rollback`
- 看板：`/strategy-snapshots`
- 部署钩子：投资经理 deploy 后自动快照（`STRATEGY_SNAPSHOT_ON_DEPLOY=1`）
- 代码回滚：需 `STRATEGY_SNAPSHOT_ALLOW_CODE_CHECKOUT=1`（prod 另需 `FORCE` 开关）

## 环境变量摘要

| 能力 | 关键变量 |
|------|----------|
| 预警推送 | `ALERT_WEBHOOK_URL`, `DINGTALK_WEBHOOK_URL`, `SMTP_*`, `WECHAT_ALERT_*` |
| Beat 定时 | `ALERT_DISPATCH_CELERY_BEAT`, `ALERT_DISPATCH_BEAT_MINUTES` |
| 快照 | `STRATEGY_SNAPSHOT_ON_DEPLOY`, `STRATEGY_SNAPSHOT_ALLOW_CODE_CHECKOUT` |

## 冒烟测试

```bash
pytest tests/test_phase44_ux_smoke.py -q
```
