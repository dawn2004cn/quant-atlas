# Repositories 目录布局与数据库后端

**更新日期**：2026-05-23（含阶段 13–16 市场/ TDX / 集成探针仓储）  
**关联**：`REFACTORING_LOG.md`（repositories 目录整理 + TimescaleDB + 阶段 13–16）

## 1. 目录结构

```
app/infrastructure/repositories/
├── common/                    # 共用：工厂、注册、门面、基类
│   ├── factory.py             # RepositoryType + create_repository
│   ├── deps.py                # bootstrap/tasks 唯一工厂入口（推荐）
│   ├── register.py            # 启动时注册 mysql/sqlite/postgres 实现
│   ├── registry.py            # 旧版 DI 注册表（逐步收敛）
│   ├── user_mapper.py
│   ├── bases/                 # 各仓储抽象基类
│   ├── facades/               # 双后端门面（委托 factory 选 mysql/sqlite）
│   │   ├── basic_market_data_repository.py
│   │   ├── investment_manager_repository.py
│   │   ├── moments_repository.py
│   │   ├── news_archive_repository.py
│   │   ├── signal_flag_pool_repository.py
│   │   └── analysis_report_repository.py
│   └── json_repositories.py   # JSON 种子 / 测试兼容
├── mysql/                     # MySQL 实现（命名 mysql_*）
│   ├── mysql_repositories.py  # User / Watchlist / StockGroup（SQLAlchemy）
│   ├── mysql_user_repository.py
│   ├── mysql_watchlist_repository.py
│   ├── mysql_stockgroup_repository.py
│   ├── mysql_stock_metadata_repository.py
│   ├── mysql_sniper_repository.py
│   ├── mysql_hot_sector_repository.py      # 热点板块快照 em_hot_sector_*
│   ├── mysql_tdx_block_repository.py       # TDX 板块只读
│   ├── mysql_tdx_dayk_repository.py        # 日 K 写入 + Qlib 导出只读
│   ├── mysql_tdx_base_data_repository.py   # TDX 基础数据 ingest
│   ├── mysql_integration_probe_repository.py  # 集成栈表 COUNT 探针
│   ├── null_hot_sector_repository.py       # 无 MySQL 时 Null 读
│   ├── async_mysql_repositories.py
│   └── mysql_*.py             # 各业务表实现
├── sqlite/                    # SQLite 实现（命名 sqlite_*）
│   ├── sqlite_repositories.py # User / Watchlist / StockGroup
│   └── sqlite_*.py
├── postgres/                  # PostgreSQL + TimescaleDB
│   └── postgres_timescale_bar_repository.py
├── factor_repository.py       # 因子生命周期（MySQL session）
├── execution_feedback.py      # 执行反馈 / 滑点
├── stock_repository.py        # 领域 stock 仓储
└── *.py                       # 根目录 shim：兼容旧 import 路径
```

### 命名约定

| 类型 | 位置 | 示例 |
|------|------|------|
| MySQL 实现 | `mysql/mysql_<domain>_repository.py` | `mysql_moments_repository.py` |
| SQLite 实现 | `sqlite/sqlite_<domain>_repository.py` | `sqlite_moments_repository.py` |
| 双后端门面 | `common/facades/<domain>_repository.py` | 内部 `create_repository(MYSQL\|SQLITE, ...)` |
| 工厂 / 注册 | `common/deps.py`, `common/register.py` | 禁止 application 层 import |
| 兼容 shim | 根目录同名 `.py` | `from ...common.deps import *` |

**新代码**应优先：

```python
from app.infrastructure.repositories.deps import create_moments_repository
# 或（明确路径）
from app.infrastructure.repositories.common.deps import create_timescale_bar_repository
```

## 2. 数据库后端分工

| 后端 | 用途 | 配置 |
|------|------|------|
| **SQLite** | 本地开发、轻量部署 | `DATABASE_BACKEND=sqlite`（默认） |
| **MySQL** | 事务型主库：用户、自选、业务状态、龙虎榜等 | `DATABASE_BACKEND=mysql` + `MYSQL_*` |
| **TimescaleDB** | 时序 OHLCV（`market_bars` hypertable） | `USE_TIMESCALEDB=1` + `TIMESCALEDB_*`（可与 MySQL 并存） |

### 推荐生产组合

- 主库：**MySQL**（`DATABASE_BACKEND=mysql`）
- 时序：**TimescaleDB**（`USE_TIMESCALEDB=1`，独立连接，不写进 `database_uri` 除非主库切 PG）

## 3. 环境变量（`.env`）

### MySQL（主库）

```env
DATABASE_BACKEND=mysql
MYSQL_HOST=192.168.8.103
MYSQL_PORT=3307
MYSQL_USER=admin
MYSQL_PASSWORD=...
MYSQL_DATABASE=quant_atlas
```

### TimescaleDB（时序，可与 MySQL 并存）

```env
USE_TIMESCALEDB=1
TIMESCALEDB_HOST=192.168.8.103
TIMESCALEDB_PORT=5434
TIMESCALEDB_USER=postgres
TIMESCALEDB_PASSWORD=postgres!#
TIMESCALEDB_DATABASE=quant_atlas
```

兼容别名：`POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DATABASE`。

若 **仅** 使用时序库作主库：`DATABASE_BACKEND=timescaledb`（`database_uri` 变为 `postgresql+psycopg://...`）。

## 4. 工厂 API（`common/deps.py`）

| 工厂 | 说明 |
|------|------|
| `create_user_repository` / `create_watchlist_repository` / `create_stock_group_repository` | Auth 仓储（MySQL session / SQLite 文件） |
| `create_basic_market_data_repository` | 龙虎榜 / 研报 / 基础数据 |
| `create_news_archive_repository` | 新闻归档 |
| `create_signal_flag_pool_repository` | 信号旗池 |
| `create_investment_manager_repository` | 投资经理 |
| `create_moments_repository` | 朋友圈 |
| `create_analysis_report_repository` | AI 分析报告 |
| `create_tdx_gpcw_repository` | TDX 专业财务 |
| `create_stock_cache` | 本地行情缓存 DB |
| `create_postgres_connection_port` | TimescaleDB 连接 Port |
| `create_timescale_bar_repository` | `market_bars` 时序读写 |
| `create_factor_repository` / `create_execution_feedback_repository` | Celery 因子 / 执行反馈 |
| `create_hot_sector_repository` | 热点板块快照（无 MySQL → `NullHotSectorStorageRepository`） |
| `create_tdx_block_repository` | TDX 板块元数据 / 成分股只读 |
| `create_tdx_dayk_repository` | 日 K sync session + history 只读（Qlib bin 导出） |
| `create_tdx_base_data_repository` | TDX 基础数据 bulk ingest |
| `create_integration_probe_repository` | 集成栈表行数探针 |

### Application 侧 Port 绑定（bootstrap，`infrastructure_binding.py`）

| Helper | Port / Repository |
|--------|-------------------|
| `bind_mysql_connection_port` | `MySQLConnectionPort` |
| `bind_tdx_block_read_port` | `TdxBlockReadPort` ← `create_tdx_block_repository` |
| `bind_tdx_dayk_write_port` | `TdxDaykWritePort` ← `create_tdx_dayk_repository` |
| `bind_tdx_base_data_write_port` | `TdxBaseDataWritePort` ← `create_tdx_base_data_repository` |
| `bind_integration_probe_port` | `IntegrationProbePort` ← `create_integration_probe_repository` |

热点板块：`HotSectorStorageService` 由 **presentation 路由** 经 `create_hot_sector_repository` 注入（非 bootstrap 全局绑定）。

## 5. TimescaleDB 使用示例

```python
from app.config import get_settings
from app.infrastructure.repositories.deps import create_timescale_bar_repository

settings = get_settings()
repo = create_timescale_bar_repository(settings)
repo.ensure_schema()
repo.upsert_bars(
    symbol="600519",
    market="CN",
    bars=[{"time": "2026-05-23", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 1000}],
)
rows = repo.get_bars(symbol="600519", market="CN", limit=100)
```

底层表：`market_bars`（Timescale hypertable，主键 `(time, symbol, market)`）。

## 6. 分层边界

- **application 层**：禁止 `import infrastructure.repositories.deps`；经 bootstrap 注入或 Port。
- **bootstrap / tasks**：允许 `deps`；Celery 经 `task_wiring` + `deps`。
- **register**：包导入 `app.infrastructure.repositories` 时自动执行，向 `factory` 注册实现。

## 7. 本地检查

```bash
python -m pytest tests/test_user_repository_port.py tests/test_mysql_repository_ports.py tests/test_layer_boundaries.py -q
python -c "from app.bootstrap import create_app; create_app()"
```
