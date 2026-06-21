# 数据源与 SQLite 库登记

> 2026-06-15 重构 T-3 产物。区分「活跃数据源」与「隔离产物」，避免散落 .db 难辨用途。
> 所有 `.db` 均在 `.gitignore`（`instance/*.db`）忽略范围内，属本地运行产物，不进版本库。

---

## 一、活跃数据源（被代码引用，保留）

| .db 文件 | 用途 | 引用位置 |
|---|---|---|
| `app_state_sqlite.db` | 应用状态默认库（`DEFAULT_DB_PATH`） | `app/config/settings.py:17` |
| `basic_market_data.db` | 龙虎榜/研报等基础行情（AkShare 入库） | `app/infrastructure/repositories/common/deps.py:201`、`sqlite_basic_market_data_repository.py:23` |
| `news_archive.db` | 新闻归档库 | `app/infrastructure/repositories/common/deps.py:182`、`app/tasks/news_backfill_tasks.py:4` |
| `signal_flag_pool.db` | 信号旗标池 | `app/infrastructure/repositories/common/deps.py:191` |
| `moments.db` | 社区/动态库 | `app/infrastructure/repositories/common/deps.py:220` |
| `openbb_cache.db` | OpenBB 行情缓存 | `app/bootstrap_components/service_wiring.py:262`、`app/modules/market_data/module.py:126` |
| `quant_atlas_lake.db` | 统一数据湖（Phase 14 迁移目标） | `app/infrastructure/storage/sqlite_lake.py:18`、`legacy_migration_service.py:28` |
| `stock_cache.db` | 本地行情/历史缓存 | `app/infrastructure/database/adapters.py:295`、`history_adapters.py:133` |

## 二、隔离区（`instance/_archive/`，无代码引用，待确认删除）

这些文件经 `findstr /s /n` 全仓扫描确认**无代码引用**，多为测试残留、版本冗余或调试产物。已移入隔离区保留可恢复性，观察一个周期后可删除。

| 文件 | 来源判断 |
|---|---|
| `app_state.db` | 与 `app_state_sqlite.db` 新旧并存，旧版 |
| `legacy_stock_cache.db` | 已被 `stock_cache.db` 取代 |
| `quant_platform.db` / `quant_platform_v2.db` / `quant_platform_v2_b.db` | 三版本并存，均无引用，疑似旧主库 |
| `fresh_bf00b000bb094371b8c45d30af654c7f.db` | hash 命名，测试临时库 |
| `sqlite_case_memory-journal.db` / `sqlite_case_off-journal.db` / `sqlite_case_plain.db` / `sqlite_case_wal.db` | SQLite journal/WAL 模式测试库 |
| `_im_test.db` / `_im_life.db` / `_im_sched.db` | 投资管理模块测试/调度残留 |
| `zz.db` | 调试命名产物 |
| `orphan_None.db` | 原根目录误命名 `None` 的 SQLite（脚本把 `None` 当文件名写入），已迁入 |

## 三、其他位置

- `tests/stock_cache.db` — 测试用，保留于 `tests/`。
- `scripts/root2.db` — scripts 下，待确认是否测试脚本产物。

## 维护约定

- 新增 SQLite 库：统一置于 `instance/`，并在本文件「活跃数据源」登记用途与引用位置。
- 产物类（cache/journal/test）应走 `instance/` 并通过 `.gitignore` 排除，勿散落根目录。
- 删除隔离区文件前确认一个发布周期无回滚需求。
