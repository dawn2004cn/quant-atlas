# Grafana 可观测性（阶段二 R11）

## 前置条件

应用已暴露 Prometheus 指标（`app/core/metrics.py`），健康端点：

- `GET /system/health`
- `GET /metrics`（若已挂载 prometheus_client exporter）

## 本地启动（可选 profile）

```bash
docker compose --profile observability up -d prometheus grafana
```

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 （默认 `admin` / `admin`）

## 推荐面板

| 面板 | 指标 |
|------|------|
| 请求 P95 | `histogram_quantile(0.95, rate(app_request_duration_seconds_bucket[5m]))` |
| 错误率 | `rate(app_request_errors_total[5m])` |
| Rust 指标延迟 | `quant_rust_indicator_latency_seconds` |
| 同步吞吐 | `quant_sync_rows_processed_total` |

## 仪表盘

预置 JSON：`deploy/grafana/dashboards/quant-atlas-overview.json`

导入路径：Grafana → Dashboards → Import → Upload JSON。

## 告警建议

- P95 > 2s 持续 5 分钟
- `app_request_errors_total` 5 分钟增长率 > 10/min
- `/system/health` 返回 `degraded` 状态
