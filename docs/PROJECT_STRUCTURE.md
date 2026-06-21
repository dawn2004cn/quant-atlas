# 项目结构

本文档详细描述了A股量化监控系统的项目结构，帮助开发者了解代码组织和模块关系。

## 项目根目录

```
quant-atlas/
├── scripts/                 # 主脚本目录
├── references/              # 参考文档
├── CHANGELOG.md             # 项目更新记录
├── USAGE.md                 # 使用说明
├── docs/USAGE_GUIDE.md      # 使用指南
├── README.md                # 项目说明
├── SKILL.md                 # 技能说明
├── OPTIMIZATION_SUMMARY.md  # 优化总结
├── PROJECT_STRUCTURE.md     # 项目结构
└── _meta.json               # 元数据
```

## 脚本目录 (scripts/)

### 核心文件

```
scripts/
├── web_app.py              # Web应用入口
├── market_sentiment.py     # 市场情绪分析
├── backtest_engine.py      # 回测引擎
├── fundamental_data.py     # 基本面数据分析
├── data_fetchers.py        # 数据源实现
├── smart_data_source.py    # 智能数据源选择
├── enhanced_data_fetcher.py # 增强型数据获取器
├── cache_factory.py        # 缓存工厂
├── stock_cache_db.py       # SQLite缓存实现
├── redis_cache.py          # Redis缓存实现
├── config.py               # 配置文件
├── architecture.md         # 架构设计文档
└── stock_code.csv          # 股票代码列表
```

### 服务层 (services/)

```
scripts/services/
├── service_container.py    # 服务容器
├── stock_service.py        # 股票服务
├── market_service.py       # 市场服务
├── watchlist_service.py    # 监控列表服务
├── selector_service.py     # 选股服务
└── user_service.py         # 用户服务
```

### 股票数据目录 (stock_data/)

```
scripts/stock_data/
├── 000004.csv              # 股票历史数据
├── 000006.csv              # 股票历史数据
└── ...                     # 其他股票历史数据文件
```

### 测试脚本

```
scripts/
├── check_cache.py          # 缓存检查
├── check_movements.py      # 市场异动检查
├── check_self_stocks.py    # 监控股票检查
├── check_zixuang.py        # 选股结果检查
├── test_enhanced_fetcher.py # 增强型数据获取器测试
└── test_cache_consistency.py # 缓存一致性测试
```

### 数据初始化脚本

```
scripts/
├── initialize_data.py      # 初始化数据
├── import_stock_data.py    # 导入股票数据
├── init_self_stocks.py     # 初始化监控股票
└── is_trading_time.py      # 交易时间检查
```

### 虚拟环境和配置

```
scripts/
├── .venv/                  # 虚拟环境
├── .idea/                  # IDE配置
└── cookies.txt             #  cookies文件
```

## 参考文档目录 (references/)

```
references/
├── API.md                  # API文档
├── CHANGELOG.md            # 变更记录
├── EXAMPLES.md             # 示例
├── FINAL_SUMMARY.md        # 最终总结
├── FIX_SUMMARY.md          # 修复总结
└── INSTALL.md              # 安装说明
```

## 模块关系

### 核心模块依赖关系

1. **Web应用层** (`web_app.py`)
   - 依赖服务层：`stock_service`, `market_service`, `watchlist_service`, `selector_service`
   - 依赖分析模块：`market_sentiment`

2. **服务层** (`services/`)
   - 依赖数据获取模块：`enhanced_data_fetcher`, `data_fetchers`
   - 依赖缓存系统：`cache_factory`, `stock_cache_db`, `redis_cache`

3. **数据获取模块** (`enhanced_data_fetcher.py`, `data_fetchers.py`)
   - 依赖外部API：akshare, yfinance, 腾讯财经, 搜狐财经

4. **缓存系统** (`cache_factory.py`, `stock_cache_db.py`, `redis_cache.py`)
   - 依赖存储：SQLite, Redis

5. **分析模块** (`market_sentiment.py`, `backtest_engine.py`)
   - 依赖数据：股票历史数据, 实时数据

### 数据流

1. **数据获取流程**
   - `web_app.py` → `services/*` → `enhanced_data_fetcher.py` → 外部API
   - 数据 → `cache_factory.py` → `redis_cache.py`/`stock_cache_db.py`

2. **数据展示流程**
   - 缓存 → `services/*` → `web_app.py` → 前端模板

3. **分析流程**
   - 缓存 → `market_sentiment.py`/`backtest_engine.py` → 分析结果 → `web_app.py` → 前端模板

## 配置文件

### 主要配置文件

1. **scripts/config.py**
   - Redis配置
   - SQLite配置
   - 数据获取配置
   - 缓存配置

### 环境变量

- `REDIS_HOST`：Redis主机地址
- `REDIS_PORT`：Redis端口
- `REDIS_DB`：Redis数据库
- `SQLITE_DB_PATH`：SQLite数据库路径

## 部署说明

1. **开发环境**
   - 本地开发：直接运行 `python scripts/web_app.py`
   - 依赖：Python 3.12+, Flask, pandas, numpy, requests, akshare

2. **生产环境**
   - 推荐使用Gunicorn或uWSGI部署
   - 配置Nginx作为反向代理
   - 启用Redis缓存提高性能

## 维护说明

1. **数据更新**
   - 定期运行 `python scripts/import_stock_data.py` 更新历史数据
   - 定期运行 `python scripts/initialize_data.py` 更新股票代码列表

2. **缓存管理**
   - 定期检查缓存状态：`python scripts/check_cache.py`
   - 清理过期缓存：`python scripts/clear_cache.py`

3. **日志管理**
   - 系统日志存储在 `scripts/` 目录下的 `.log` 文件中
   - 定期清理日志文件，避免占用过多空间

## 扩展指南

1. **添加新数据源**
   - 在 `data_fetchers.py` 中添加新的数据源实现
   - 在 `enhanced_data_fetcher.py` 中集成新数据源

2. **添加新服务**
   - 在 `services/` 目录下创建新的服务文件
   - 在 `service_container.py` 中注册新服务

3. **添加新功能**
   - 在 `web_app.py` 中添加新的路由和视图
   - 在 `templates/` 目录下创建新的模板文件

4. **优化性能**
   - 调整缓存策略：`config.py` 中的缓存过期时间
   - 优化数据获取：`enhanced_data_fetcher.py` 中的并发策略
   - 优化数据库查询：`stock_cache_db.py` 中的查询语句

## 总结

A股量化监控系统采用模块化设计，清晰的目录结构和模块划分使得代码易于理解和维护。系统通过服务容器模式管理依赖，通过智能缓存工厂优化性能，通过多数据源备选提高稳定性。

这种结构设计不仅便于当前功能的实现，也为未来的扩展和维护提供了良好的基础。