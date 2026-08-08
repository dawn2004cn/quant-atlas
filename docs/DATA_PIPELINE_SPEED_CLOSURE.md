# 数据链路速度优化 — 交付收束清单

与 `REFACTORING_LOG.md`（2026-07-28 起「数据链路速度优化」各续轮、至 2026-08-04 续三十三四）对应。  
范围：页面加载/导航对齐、行情 dump 观测与告警、预警推送闭环、Beat 契约。无关功能仅菜单级隐藏。

## 总览

```
行情 quotes/page（首选）
  └─ 全量 /quotes → dump 计数(Redis|内存) + 趋势
       ├─ health_banner / 操盘台 / 观测台徽标
       ├─ AlertCenter（data:quotes:full_dump）
       ├─ Beat: quotes_dump_monitor（可选）→ auto dispatch
       └─ Beat / API: alert dispatch + 渠道探测

历史入库（Celery，2026-08-04 精简）
  TDX lday → Timescale + qlib_export CSV → qlib_bin
  （MySQL / QuestDB / ClickHouse 入库已下线）
```

## 交付对照

| 主题 | 状态 | 关键入口 / 开关 |
|------|------|----------------|
| 分页 / history 合并 / 时序 LIMIT | ✅ | `quotes/page`、history coalesce、QuestDB/龙虎榜分页 |
| SPA ↔ 经典导航对齐 | ✅ | `CoreWorkflowStrip` / `PageQuickNav`；Login/NotFound 刻意跳过 |
| dump 跨进程计数 + 趋势 | ✅ | `quotes_dump_metrics`；观测台趋势条 |
| dump → health banner | ✅ | `/system/health-banner`、操盘台 `health_banner` |
| dump → 预警中心 | ✅ | `AlertCenterService._alerts_from_quotes_dump` |
| 渠道探测 + 多选推送 | ✅ | `GET /system/alerts/channels`；`POST .../dispatch` |
| dump 巡检 Beat + 自动 dispatch | ✅ | `QUOTES_DUMP_MONITOR_CELERY_BEAT`（默认关）；`QUOTES_DUMP_AUTO_DISPATCH` |
| 告警运维快照 | ✅ | observability `alert_ops` |
| BeatRegistry kwargs 扁平 | ✅ | `celery_app` + `_normalize_task_kwargs` |
| 视觉 token（dump/告警语义色） | ✅ | 见下节「视觉」 |

## 环境变量（默认偏关）

| 变量 | 默认 | 作用 |
|------|------|------|
| `QUOTES_FULL_DUMP_WARN_THRESHOLD` | `1` | dump 次数超阈值告警 |
| `ALERT_DISPATCH_CELERY_BEAT` | `0` | 周期推送 Beat |
| `ALERT_DISPATCH_BEAT_MINUTES` | `30` | 推送周期（5–59） |
| `ALERT_DISPATCH_MIN_LEVEL` / `LIMIT` | warning / 20 | Beat 推送参数 |
| `QUOTES_DUMP_MONITOR_CELERY_BEAT` | `0` | dump 巡检 Beat |
| `QUOTES_DUMP_MONITOR_BEAT_MINUTES` | `30` | 巡检周期 |
| `QUOTES_DUMP_AUTO_DISPATCH` | `0` | 巡检超阈值时自动 dispatch |

渠道相关见 `.env.example`（webhook / 钉钉 / 邮件 / 微信）。

## 验证命令

```powershell
python -m pytest tests/tasks/test_quotes_dump_monitor_tasks.py tests/bootstrap/test_phase41_alert_beat.py tests/architecture/test_phase_e_observability.py tests/unit/test_celery_infrastructure.py tests/application/test_scheduled_cn_history_daily.py -q --tb=short
```

手工：观测台看 `全量 quotes` + `告警运维 Beat`；预警中心看 dump 条目与渠道 ·已配置；超阈值后确认 `action=/observability`、`preferred=quotes/page`。

## 视觉 token（SPA ↔ 经典）

| 语义 | 经典 | SPA |
|------|------|-----|
| 正常 | `--positive` / `--tone-ok` | `--quant-positive` / `--quant-accent` |
| 预警 | `--warning` / `--tone-warn` | `--quant-warn` |
| 危险 | `--danger` / `--tone-danger` | `--quant-danger` |
| 信息 | `--brand-2` / `--tone-info` | `--quant-info` |
| 边框/卡片 | `--surface-border` | `--quant-border` → `--quant-surface-border` |
| Banner 工具类 | `.qa-tone-banner--{ok,warn,danger}` | 同名（`index.css`） |

## 刻意不做 / 后续可选

- Login / NotFound 不接主链导航
- 其它 Beat 任务若再传 `kwargs={...}`，由 `BeatRegistry` unwrap 兜底（仍应扁平传参）
- Flask-SocketIO 行情推流与 TaskEventHub Redis Pub/Sub：见 `docs/ui_opt-completion.md`
