# A股量化监控系统使用指南

## 一、系统简介

A股量化监控系统是一个用于监控和分析A股市场的工具，提供实时数据、历史数据和市场分析功能。系统采用Python开发，基于Flask框架构建Web应用，使用SQLite作为缓存数据库。

## 二、安装与配置

### 2.1 环境要求

- Python 3.7+
- 依赖库：Flask, akshare, pandas, numpy, schedule等

### 2.2 安装步骤

1. **克隆项目**：
   ```bash
   git clone <项目地址>
   cd quant-atlas
   ```

2. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

3. **配置数据库**：
   - 系统会自动在 `instance/stock_cache.db` 创建行情缓存库（与 `app.config.INSTANCE_DIR` 一致）

## 三、系统功能

### 3.1 实时数据监控

- **全市场股票列表**：显示所有A股股票的实时行情数据
- **个股详情**：查看单只股票的详细信息和实时行情
- **市场热点**：展示市场热点板块和个股

### 3.2 历史数据管理

- **历史数据导入**：将CSV格式的历史数据导入到系统
- **历史数据更新**：定期更新历史数据，确保数据的完整性
- **历史数据查询**：查询和分析历史数据

### 3.3 市场分析

- **技术指标分析**：计算和展示各种技术指标
- **趋势分析**：分析市场和个股的趋势
- **风险评估**：评估股票的风险水平

## 四、使用方法

### 4.1 启动系统

1. **进入项目目录**：
   ```bash
   cd c:\Users\dawn2\.openclaw\skills\quant-atlas\scripts
   ```

2. **启动Web服务器**：
   ```bash
   python web_app.py
   ```

3. **访问系统**：
   - 打开浏览器，访问 `http://localhost:5000`
   - 默认账号：admin / admin123

### 4.2 更新全市场数据

#### 4.2.1 手动更新

```bash
python stock_async_fetcher.py --all
```

此命令会获取所有A股股票的实时数据，并保存到缓存数据库中。

#### 4.2.2 自动更新

系统会在主页加载时自动更新全市场数据，也可以设置定时任务定期更新：

```bash
python schedule_history_update.py
```

此命令会启动一个定时任务，每天16:00自动更新历史数据。

### 4.3 查看全市场股票列表

1. **登录系统**：使用默认账号登录
2. **导航到全市场股票列表**：点击左侧菜单中的"市场全景"或"全市场股票列表"
3. **查看数据**：系统会从缓存中加载全市场股票数据，加载速度非常快

### 4.4 管理历史数据

#### 4.4.1 导入历史数据

将CSV格式的历史数据文件放入 `stock_history_data` 目录，然后运行：

```bash
python update_history_data.py
```

此命令会将CSV文件中的历史数据导入到缓存数据库中。

#### 4.4.2 增量更新历史数据

系统会在每天收盘后自动更新历史数据，也可以手动运行：

```bash
python update_history_data.py --update
```

此命令会将当天的股票数据追加到CSV文件中，并更新到缓存数据库。

## 五、API接口

### 5.1 全市场股票数据

- **URL**：`/api/market-all`
- **方法**：GET
- **参数**：无
- **返回**：全市场股票的实时数据

### 5.2 历史数据更新

- **URL**：`/api/update-history`
- **方法**：GET
- **参数**：无
- **返回**：历史数据更新状态

### 5.3 历史数据状态

- **URL**：`/api/history-status`
- **方法**：GET
- **参数**：无
- **返回**：所有股票的历史数据更新状态

## 六、目录结构

```
quant-atlas/
├── scripts/                  # 脚本目录
│   ├── stock_async_fetcher.py      # 异步数据获取器
│   ├── stock_cache_db.py            # 缓存数据库管理
│   ├── web_app.py                   # Web应用
│   ├── update_history_data.py       # 历史数据更新
│   ├── schedule_history_update.py   # 定时任务
│   ├── test_multithread_yfinance.py # 多线程测试
│   ├── test_api_availability.py     # API可用性测试
│   ├── test_adata_api.py            # adata API测试
│   ├── stock_history_data/          # 历史数据目录
│   ├── stock_cache.db               # 缓存数据库
│   └── ...
├── references/              # 参考文档
│   ├── API.md                      # API文档
│   ├── INSTALL.md                  # 安装文档
│   └── ...
├── CHANGELOG.md            # 变更日志
├── SKILL.md                # 技能说明
├── OPTIMIZATION_SUMMARY.md # 优化总结
├── docs/USAGE_GUIDE.md     # 使用指南
└── _meta.json              # 元数据
```

## 七、常见问题

### 7.1 全市场股票列表加载缓慢

**解决方案**：系统已经优化为使用缓存数据，加载速度应该非常快。如果仍然加载缓慢，请检查缓存是否正常更新。

### 7.2 全市场股票列表数据为空

**解决方案**：
1. 手动运行 `python stock_async_fetcher.py --all` 更新全市场数据
2. 检查网络连接是否正常
3. 检查缓存数据库是否正常

### 7.3 历史数据更新失败

**解决方案**：
1. 检查CSV文件格式是否正确
2. 检查文件编码是否为UTF-8
3. 检查网络连接是否正常

### 7.4 系统登录失败

**解决方案**：
1. 检查用户名和密码是否正确（默认：admin / admin123）
2. 检查Web服务器是否正常运行
3. 检查浏览器缓存是否需要清理

## 八、故障排除

### 8.1 检查Web服务器状态

```bash
# 查看Web服务器进程
ps aux | grep web_app.py

# 检查Web服务器日志
python web_app.py
```

### 8.2 检查缓存数据库

```bash
# 查看缓存数据库文件大小
ls -l stock_cache.db

# 检查缓存数据库表结构
sqlite3 stock_cache.db .schema
```

### 8.3 检查数据更新状态

```bash
# 查看历史数据更新状态
python update_history_data.py --status
```

## 九、系统维护

### 9.1 定期备份

- 定期备份 `stock_cache.db` 文件
- 定期备份 `stock_history_data` 目录

### 9.2 清理缓存

```bash
# 清理缓存数据库
rm stock_cache.db
# 重新启动系统，会自动创建新的缓存数据库
python web_app.py
```

### 9.3 更新依赖

```bash
pip install -r requirements.txt --upgrade
```

## 十、总结

A股量化监控系统是一个功能强大的工具，通过优化缓存机制和数据处理流程，提供了快速、稳定的A股市场监控和分析功能。系统支持实时数据监控、历史数据管理和市场分析，为用户提供全面的市场信息和分析工具。

通过本使用指南，用户可以快速上手系统，了解系统的功能和使用方法，从而更好地利用系统进行A股市场的监控和分析。