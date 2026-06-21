# 数据库与仓储指南

**更新日期**：2026-05-23  
**详细目录说明**：见 [`docs/refactor/repositories-layout.md`](refactor/repositories-layout.md)

## 1. 后端选型

| 后端 | 变量 | 典型用途 |
|------|------|----------|
| SQLite | `DATABASE_BACKEND=sqlite`（默认） | 本地开发、单文件状态 |
| MySQL | `DATABASE_BACKEND=mysql` | 用户/自选/业务表、主从读写 |
| TimescaleDB | `USE_TIMESCALEDB=1` 或 `DATABASE_BACKEND=timescaledb` | OHLCV 时序（`market_bars` hypertable） |

**推荐生产**：MySQL 主库 + TimescaleDB 时序库并行（见 `.env` 中 `USE_TIMESCALEDB=1`）。

**写入已接通**：`TdxDaykSyncService` 在 `USE_TIMESCALEDB=1` 时，每标的单事务写入：

| 表 | 内容 |
|----|------|
| `market_bars` | 未复权 OHLCV |
| `market_adjustment_factors` | 除权因子（xdxr 推导） |
| `market_bars_qfq` | 前复权 K 线（**物化视图**，由 raw+因子派生） |
| `market_bars_hfq` | 后复权 K 线（**物化视图**） |

同步结束触发 `refresh_adjusted_materialized_views()`（`TIMESCALE_REFRESH_MATVIEWS_ON_SYNC=1`）。

读取：`get_bars(adjust='raw'|'qfq'|'hfq')`、`get_factors()`（经 `PostgresTimescaleBarRepository`）。

## 2. 配置入口

- 类型化配置：`app/config/settings.py` → `AppSettings`
- 切片：`app/config/slices.py` → `DataBackendSettings`（`use_mysql` / `use_timescaledb`）
- 环境文件：项目根目录 `.env`（示例见 `.env.example`）

### MySQL 主库

```env
DATABASE_BACKEND=mysql
MYSQL_HOST=192.168.8.103
MYSQL_PORT=3307
MYSQL_USER=admin
MYSQL_PASSWORD=...
MYSQL_DATABASE=quant_atlas
MYSQL_READ_HOST=...    # 可选读库
```

### TimescaleDB（PostgreSQL 扩展）

```env
USE_TIMESCALEDB=1
TIMESCALEDB_HOST=192.168.8.103
TIMESCALEDB_PORT=5434
TIMESCALEDB_USER=postgres
TIMESCALEDB_PASSWORD=postgres!#
TIMESCALEDB_DATABASE=quant_atlas
```

连接实现：`app/infrastructure/database/postgres_client.py`  
时序仓储：`app/infrastructure/repositories/postgres/postgres_timescale_bar_repository.py`

## 3. 仓储工厂

统一从 **`app/infrastructure/repositories/deps.py`**（shim 指向 `common/deps.py`）创建：

```python
from app.config import get_settings
from app.infrastructure.repositories.deps import (
    create_user_repository,
    create_basic_market_data_repository,
    create_timescale_bar_repository,
)

s = get_settings()
user_repo = create_user_repository(s, session_factory=...)
bars_repo = create_timescale_bar_repository(s)
```

Bootstrap 装配：`app/bootstrap_components/repositories.py` → `create_repositories()`。

## 4. 数据文件与缓存（SQLite 模式 / 辅助）

| 路径 | 用途 |
|------|------|
| `instance/app_state_sqlite.db` | 默认 SQLite 主状态（用户/自选等） |
| `instance/stock_cache.db` | 本地行情快照缓存（`create_stock_cache()`） |
| `instance/*.db` | 各门面仓储 SQLite 文件（news、signal_flag、moments 等） |
| `config/users.json` 等 | MySQL 空库时的 JSON 种子 |

## 5. 目录结构（摘要）

```
repositories/
├── common/     # factory, deps, register, facades, bases
├── mysql/      # mysql_* 实现
├── sqlite/     # sqlite_* 实现
├── postgres/   # TimescaleDB 时序
└── *.py        # 兼容 shim（旧 import 仍可用）
```

## 6. 分层规则

- Application **不得** import `infrastructure.repositories.deps` 或具体 `mysql_*` / `sqlite_*`。
- 新能力：先定义 `domain.ports`，再在 `mysql/` / `sqlite/` / `postgres/` 实现并注册到 `common/register.py`。
- 门禁：`tests/test_layer_boundaries.py`。

## 7. 相关文档

- [`docs/refactor/layer-boundaries.md`](refactor/layer-boundaries.md) — 分层门禁
- [`docs/refactor/structural-debt-roadmap.md`](refactor/structural-debt-roadmap.md) — 阶段 10 验收
- [`REFACTORING_LOG.md`](../REFACTORING_LOG.md) — 变更审计
