# Quant Atlas 修改记录

**日期**: 2026-04-24

---

## 1. Repository 多数据库架构分离

### 1.1 问题背景
原代码中多个 Repository 类同时支持 MySQL 和 SQLite，通过 `if-else` 判断使用哪种数据库，导致代码臃肿且难以维护。

### 1.2 解决方案
采用工厂模式 + 注册机制，将 MySQL 和 SQLite 实现分离到不同目录：

```
app/infrastructure/repositories/
├── bases/
│   ├── __init__.py
│   └── base.py                      # 抽象基类定义
├── mysql/
│   ├── __init__.py
│   ├── mysql_investment_manager_repository.py
│   ├── mysql_basic_market_data_repository.py
│   ├── mysql_news_archive_repository.py
│   ├── mysql_signal_flag_pool_repository.py
│   ├── mysql_moments_repository.py
│   ├── mysql_analysis_report_repository.py
│   ├── mysql_agent_repository.py
│   ├── mysql_trading_repository.py
│   ├── mysql_payment_repository.py
│   ├── mysql_kronos_repository.py
│   ├── mysql_openbb_repository.py
│   └── mysql_quantml_repository.py
├── sqlite/
│   ├── __init__.py
│   ├── sqlite_investment_manager_repository.py
│   ├── sqlite_basic_market_data_repository.py
│   ├── sqlite_news_archive_repository.py
│   ├── sqlite_signal_flag_pool_repository.py
│   ├── sqlite_moments_repository.py
│   ├── sqlite_analysis_report_repository.py
│   ├── sqlite_agent_repository.py
│   ├── sqlite_trading_repository.py
│   ├── sqlite_payment_repository.py
│   ├── sqlite_kronos_repository.py
│   ├── sqlite_openbb_repository.py
│   └── sqlite_quantml_repository.py
├── factory.py                       # 工厂类
├── register.py                     # 自动注册
└── __init__.py
```

### 1.3 核心设计

**工厂模式** (`factory.py`):
```python
class RepositoryType(Enum):
    MYSQL = "mysql"
    SQLITE = "sqlite"
    POSTGRES = "postgres"

class RepositoryRegistry:
    _registry = {}

    @classmethod
    def register(cls, repo_type, model_name, repo_class):
        key = (repo_type.value, model_name)
        cls._registry[key] = repo_class

    @classmethod
    def create(cls, repo_type, model_name, **kwargs):
        key = (repo_type.value, model_name)
        return cls._registry[key](**kwargs)
```

### 1.4 迁移的 Repository

| Repository | MySQL | SQLite | 状态 |
|------------|-------|--------|------|
| InvestmentManagerRepository | ✅ | ✅ | 已完成 |
| BasicMarketDataRepository | ✅ | ✅ | 已完成 |
| NewsArchiveRepository | ✅ | ✅ | 已完成 |
| SignalFlagPoolRepository | ✅ | ✅ | 已完成 |
| MomentsRepository | ✅ | ✅ | 已完成 |
| AnalysisReportRepository | ✅ | ✅ | 已完成 |
| AgentRepository | ✅ | ✅ | 已完成 |
| TradingRepository | ✅ | ✅ | 已完成 |
| PaymentRepository | ✅ | ✅ | 已完成 |
| KronosRepository | ✅ | ✅ | 已完成 |
| OpenBBRepository | ✅ | ✅ | 已完成 |
| QuantMLFactorRepository | ✅ | ✅ | 已完成 |

---

## 2. Stock History 按市场分表

### 2.1 问题背景
`stock_history` 表存储所有股票的历史记录，数据量随时间线性增长，查询性能下降。

### 2.2 分表策略

| 市场 | 表名 | 股票代码前缀 |
|------|------|------------|
| 上海 | `stock_history_sh` | sh |
| 深圳 | `stock_history_sz` | sz |
| 北京 | `stock_history_bj` | bj |
| 香港 | `stock_history_hk` | hk |
| 美国 | `stock_history_us` | us |
| 加密货币 | `stock_history_btc` | btc |

### 2.3 新增文件

**`scripts/create_stock_history_market_tables.py`**:
- 创建按市场划分的股票历史表
- 支持 markets: sh, sz, bj, hk, us, btc

**`scripts/migrate_stock_history_by_market.py`**:
- 数据迁移脚本
- 将现有数据从 `stock_history` 表迁移到对应市场的表
- 自动根据股票代码前缀判断市场

### 2.4 修改的文件

| 文件 | 修改内容 |
|------|---------|
| `app/infrastructure/database/stock_cache_db.py` | 添加 `_get_stock_history_table` 方法 |
| `app/application/services/tdx_dayk_sync_service.py` | MySQL 插入方法使用分表 |
| `app/infrastructure/providers/market_data.py` | 非 A 股使用 AkShare 获取历史数据 |
| `app/application/services/qlib_pipeline_service.py` | UNION 查询所有分表 |

### 2.5 核心函数

```python
def _get_stock_history_table(stock_code: str) -> str:
    """根据股票代码获取对应的市场表"""
    normalized = SymbolNormalizer.to_db_code(stock_code)
    code_part = normalized.split(":", 1)[1] if ":" in normalized else normalized
    if code_part.startswith("sh"):
        return "stock_history_sh"
    elif code_part.startswith("sz"):
        return "stock_history_sz"
    # ... 其他市场
    else:
        return "stock_history"
```

---

## 3. 港股、美股、加密货币历史数据获取

### 3.1 新增文件

**`app/infrastructure/providers/market_history_fetcher.py`**:
- `fetch_hk_daily()` - 获取港股历史数据（使用 AkShare）
- `fetch_us_daily()` - 获取美股历史数据（使用 AkShare）
- `fetch_crypto_daily()` - 获取加密货币历史数据（使用 AkShare）
- `fetch_market_daily()` - 统一的历史数据获取接口
- `to_db_code()` - 将行情代码转换为存储代码

**`app/tasks/market_history_tasks.py`**:
- `fetch_hk_history` - Celery 任务：获取港股历史数据
- `fetch_us_history` - Celery 任务：获取美股历史数据
- `fetch_crypto_history` - Celery 任务：获取加密货币历史数据
- `fetch_all_market_history` - Celery 任务：获取所有市场历史数据

### 3.2 代码转换对照表

| 市场 | 原始代码 | 存储代码 | 分表 |
|------|---------|---------|------|
| 港股 | `0700.HK` | `hk0700` | `stock_history_hk` |
| 美股 | `AAPL` | `usAAPL` | `stock_history_us` |
| 加密货币 | `BTCUSDT` | `btcBTC` | `stock_history_btc` |

---

## 4. 统一 DB Engine 和连接池

### 4.1 问题背景
原代码使用线程局部连接模式（`thread_local`），每次查询创建新连接，导致：
- 连接资源浪费
- "Too many connections" 错误
- 性能不稳定

### 4.2 解决方案
建立统一的 SQLAlchemy 连接池，所有数据库访问通过连接池管理。

### 4.3 新增文件

**`app/infrastructure/database/db_manager.py`**:
- `DatabaseManager` 类 - 单例模式管理引擎和会话工厂
- `get_engine()` - 获取 SQLAlchemy 引擎
- `get_session()` - 获取作用域会话
- `get_connection()` - 从连接池获取 DBAPI 连接
- `bootstrap_schema()` - 引导数据库 schema

**`scripts/bootstrap_database.py`**:
- 数据库初始化引导脚本
- 初始化连接池和 schema

### 4.4 修改的文件

| 文件 | 修改内容 |
|------|---------|
| `app/infrastructure/database/mysql_client.py` | 新增 `mysql_get_connection` 函数 |
| `app/infrastructure/database/stock_cache_db.py` | 使用统一连接池 |
| `app/infrastructure/repositories/mysql/*.py` | 替换为 `mysql_get_connection` |

### 4.5 连接池配置

| 配置项 | 默认值 | 说明 |
|------|-------|------|
| `pool_size` | 5 | 连接池大小 |
| `max_overflow` | 5 | 最大溢出连接数 |
| `pool_recycle` | 1800 | 连接回收时间（秒） |
| `pool_timeout` | 30 | 连接超时时间（秒） |
| `connect_timeout` | 10 | 连接超时时间（秒） |
| `read_timeout` | 60 | 读取超时时间（秒） |
| `write_timeout` | 60 | 写入超时时间（秒） |

### 4.6 架构优势

- **统一管理**：所有数据库连接通过同一连接池管理
- **性能提升**：减少连接创建/销毁开销
- **可靠性**：连接池自动处理连接复用和回收
- **向后兼容**：保持原有 API 不变
- **扩展性**：支持多数据库实例管理

---

## 5. 技术总结

### 5.1 设计模式

1. **工厂模式** - Repository 创建
2. **注册模式** - 自动注册所有实现
3. **单例模式** - DatabaseManager
4. **连接池模式** - SQLAlchemy 连接池

### 5.2 架构原则

1. **开闭原则** - 新增数据库只需添加实现，不修改已有代码
2. **单一职责** - 每个类只关心一种数据库实现
3. **依赖倒置** - 通过抽象基类定义接口
4. **面向接口编程** - 使用工厂模式创建实例

### 5.3 未来扩展

**新增 PostgreSQL 支持**:
1. 创建 `postgres/` 目录和实现文件
2. 在 `register.py` 中注册实现
3. 更新 `RepositoryType` 枚举（如果需要）

**示例**:
```python
# app/infrastructure/repositories/postgres/postgres_investment_manager_repository.py
class PostgresInvestmentManagerRepository:
    ...

# register.py 中添加注册
RepositoryRegistry.register(RepositoryType.POSTGRES, "investment_manager", PostgresInvestmentManagerRepository)
```

---

## 6. 修改的文件清单

### 新增文件 (10)
- `app/infrastructure/database/db_manager.py`
- `app/infrastructure/providers/market_history_fetcher.py`
- `app/tasks/market_history_tasks.py`
- `scripts/create_stock_history_market_tables.py`
- `scripts/migrate_stock_history_by_market.py`
- `scripts/bootstrap_database.py`
- `app/infrastructure/repositories/sqlite/sqlite_agent_repository.py`
- `app/infrastructure/repositories/sqlite/sqlite_trading_repository.py`
- `app/infrastructure/repositories/sqlite/sqlite_payment_repository.py`
- `app/infrastructure/repositories/sqlite/sqlite_kronos_repository.py`
- `app/infrastructure/repositories/sqlite/sqlite_openbb_repository.py`
- `app/infrastructure/repositories/sqlite/sqlite_quantml_repository.py`

### 修改文件 (15+)
- `app/infrastructure/database/mysql_client.py`
- `app/infrastructure/database/stock_cache_db.py`
- `app/application/services/tdx_dayk_sync_service.py`
- `app/infrastructure/providers/market_data.py`
- `app/application/services/qlib_pipeline_service.py`
- `app/infrastructure/repositories/mysql_investment_manager_repository.py`
- `app/infrastructure/repositories/mysql_basic_market_data_repository.py`
- `app/infrastructure/repositories/mysql_news_archive_repository.py`
- `app/infrastructure/repositories/mysql_signal_flag_pool_repository.py`
- `app/infrastructure/repositories/mysql_moments_repository.py`
- `app/infrastructure/repositories/mysql_analysis_report_repository.py`
- `app/infrastructure/repositories/register.py`
- `app/infrastructure/repositories/factory.py`

---

**修改人**: AI Assistant
**日期**: 2026-04-24
