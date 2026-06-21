# 使用说明

本文档提供A股量化监控系统的详细使用说明，包括系统安装、配置、运行和功能使用。

## 目录

1. [系统安装](#系统安装)
2. [配置说明](#配置说明)
3. [系统运行](#系统运行)
4. [功能使用](#功能使用)
5. [常见问题](#常见问题)

## 系统安装

### 环境要求

- Python 3.12+
- Redis (可选，用于高性能缓存)
- 网络连接（用于数据获取）

### 安装步骤

1. **克隆项目**

```bash
git clone <项目地址>
cd quant-atlas
```

2. **创建虚拟环境**

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

3. **安装依赖**

```bash
# 安装基本依赖
pip install flask flask-login pandas numpy requests akshare

# 安装可选依赖（Redis支持）
pip install redis

# 安装可选依赖（数据获取）
pip install yfinance

# 安装可选依赖（数据处理）
pip install tqdm
```

## 配置说明

### 配置文件

编辑 `scripts/config.py` 文件，配置以下参数：

```python
# Redis配置
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0
}

# SQLite配置
SQLITE_CONFIG = {
    'db_path': 'stock_cache.db'
}

# 数据获取配置
DATA_FETCH_CONFIG = {
    'max_retries': 3,
    'retry_interval': 2,
    'timeout': 20
}

# 缓存配置
CACHE_CONFIG = {
    'market_cache_expiry': 30,  # 分钟
    'stock_cache_expiry': 7 * 24 * 60,  # 分钟
    'fund_flow_expiry': 24 * 60,  # 分钟
    'tech_indicators_expiry': 24 * 60  # 分钟
}
```

### 环境变量

系统支持通过环境变量覆盖配置：

- `REDIS_HOST`：Redis主机地址
- `REDIS_PORT`：Redis端口
- `REDIS_DB`：Redis数据库
- `SQLITE_DB_PATH`：SQLite数据库路径

## 系统运行

### 初始化数据

首次运行系统前，需要初始化股票数据：

```bash
# 初始化股票代码列表
python scripts/initialize_data.py

# 更新股票历史数据
python scripts/import_stock_data.py
```

### 启动Web应用

```bash
# 启动Web应用
python scripts/web_app.py
```

系统会在 `http://localhost:5000` 启动。

### 定时任务

建议设置定时任务，定期更新股票数据：

```bash
# 每天更新股票历史数据
0 0 * * * cd /path/to/quant-atlas && python scripts/import_stock_data.py

# 每小时更新市场数据
0 * * * * cd /path/to/quant-atlas && python scripts/initialize_data.py
```

## 功能使用

### 1. 登录系统

- 访问 `http://localhost:5000`
- 默认账号：admin / admin123
- 登录后进入系统首页

### 2. 实时股票监控

- **监控列表**：在首页查看已添加的监控股票
- **添加股票**：点击"添加股票"按钮，输入股票代码
- **移除股票**：点击股票旁边的"移除"按钮
- **刷新数据**：点击"刷新数据"按钮，实时更新股票数据

### 3. 市场分析

- **市场总览**：查看市场整体情况
- **市场异动**：查看实时市场异动
- **排行榜**：查看涨幅榜、跌幅榜、成交榜、换手榜
- **市场情绪**：查看市场情绪评分

### 4. 选股功能

- **中长线选股**：选择"选股中心" → "中长线选股"
- **技术指标选股**：选择"选股中心" → "技术指标选股"
- **基本面选股**：选择"选股中心" → "基本面选股"
- **自定义策略**：在 `scripts/services/selector_service.py` 中添加自定义策略

### 5. 技术分析

- **股票详情**：点击股票名称，进入股票详情页
- **技术指标**：查看MA、RSI、MACD等技术指标
- **K线图表**：查看股票K线图
- **技术信号**：查看金叉死叉等技术信号

### 6. 系统设置

- **用户管理**：添加、编辑、删除用户
- **角色管理**：管理用户角色和权限
- **系统配置**：修改系统配置参数

## 数据管理

### 导入数据

```bash
# 导入股票历史数据
python scripts/import_stock_data.py

# 导入自定义股票列表
python scripts/init_self_stocks.py
```

### 导出数据

```bash
# 导出监控列表
python scripts/export_watchlist.py

# 导出选股结果
python scripts/export_selection.py
```

### 数据清理

```bash
# 清理旧数据
python scripts/clear_old_data.py

# 重建缓存
python scripts/rebuild_cache.py
```

## API 接口

### 股票数据接口

- `GET /api/stocks`：获取监控股票列表
- `POST /api/stocks`：添加股票到监控列表
- `DELETE /api/stocks/<code>`：从监控列表移除股票
- `GET /api/stocks/<code>`：获取股票详情

### 市场数据接口

- `GET /api/market/movements`：获取市场异动
- `GET /api/market-rankings`：获取市场排行榜
- `GET /api/market/sentiment`：获取市场情绪

### 选股接口

- `GET /api/selector/long-term`：获取中长线选股结果
- `GET /api/selector/tech`：获取技术指标选股结果
- `GET /api/selector/fundamental`：获取基本面选股结果

## 常见问题

### 1. 数据获取失败

**问题**：系统显示"数据获取失败"

**解决方案**：
- 检查网络连接
- 检查数据源API是否正常
- 查看系统日志，了解具体错误信息
- 系统会自动尝试其他数据源

### 2. Redis连接失败

**问题**：系统显示"Redis连接失败"

**解决方案**：
- 检查Redis服务是否运行
- 检查Redis配置是否正确
- 系统会自动切换到SQLite缓存

### 3. 股票数据不更新

**问题**：股票数据长时间不更新

**解决方案**：
- 点击"刷新数据"按钮
- 检查网络连接
- 检查数据源是否正常
- 重启系统

### 4. 选股结果为空

**问题**：选股策略返回空结果

**解决方案**：
- 调整选股参数
- 检查股票数据是否完整
- 尝试其他选股策略

### 5. 系统运行缓慢

**问题**：系统响应缓慢

**解决方案**：
- 启用Redis缓存
- 优化系统配置
- 减少监控股票数量
- 定期清理旧数据

## 故障排除

### 查看日志

系统日志存储在 `scripts/` 目录下的 `.log` 文件中。

### 检查缓存

```bash
# 检查缓存状态
python scripts/check_cache.py

# 检查市场异动数据
python scripts/check_movements.py

# 检查监控股票
python scripts/check_self_stocks.py
```

### 重启系统

```bash
# 停止系统
Ctrl+C

# 清理缓存
python scripts/clear_cache.py

# 重启系统
python scripts/web_app.py
```

## 性能优化

1. **启用Redis**：Redis缓存比SQLite快10-100倍
2. **减少监控股票**：建议监控股票数量不超过50只
3. **定期更新数据**：设置定时任务，避免高峰时段更新
4. **优化网络**：确保网络连接稳定
5. **调整缓存过期时间**：根据数据类型设置合理的过期时间

## 安全注意事项

1. **修改默认密码**：首次登录后修改默认密码
2. **限制访问**：只允许受信任的IP访问
3. **定期备份**：定期备份数据库和配置文件
4. **更新依赖**：定期更新Python依赖包
5. **监控系统**：监控系统运行状态，及时发现异常

## 联系支持

如遇到问题，请：

1. 查看本使用说明
2. 检查系统日志
3. 尝试重启系统
4. 联系技术支持
