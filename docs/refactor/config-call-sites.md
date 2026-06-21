# AppSettings.from_env() 调用点基线（2026-05-19）

重构目标：业务代码改用 `from app.config import get_settings`；仅 `app/config/settings_provider.py` 内保留 `from_env()`。

## 统计（初始）

| 区域 | 约计 |
|------|------|
| `presentation/web/pages.py` | 28 |
| `bootstrap_components/service_wiring.py` | 7 |
| `tasks/*.py` | 20+ |
| `application/services` | 10+ |
| 其他 infrastructure | 10+ |

## 已迁移（2026-05-19 完成 `app/` 范围）

- `bootstrap.py`、`service_wiring.py`、`pages.py`
- `hot_sector_service.py` / `hot_sector_storage_service.py`（THS 切片）
- 全部 `app/tasks/*`
- `qlib_pipeline_service.py`、`tdx_*`、`pytdx/*`、`history_adapters.py`
- `mysql_factor_vault.py`、`mysql_tdx_gpcw_repository.py`、`adapters.py`
- `stock_metadata.py`、`integration_hub_service.py`、`investment_committee_db.py`
- `routes_v1_monitoring.py`

## 仍保留 from_env（允许）

- `app/config/settings_provider.py` — 进程单例唯一入口
- `tests/`、`scripts/`、`alembic/` — 独立入口脚本（后续可选迁移）

## 门禁

```bash
rg "AppSettings\.from_env\(\)" app
# 期望：仅 settings_provider.py
```
