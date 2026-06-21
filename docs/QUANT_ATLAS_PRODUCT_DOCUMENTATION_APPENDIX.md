# Quant Atlas 产品文档附录
## 深度技术细节、API参考与最佳实践

---

## 第七部分：API接口参考

### 7.1 核心API一览

Quant Atlas提供**200+ RESTful API接口**，覆盖所有业务功能。以下列出核心接口：

#### 7.1.1 市场数据API

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/quotes` | GET | 批量获取股票实时行情 |
| `/api/v1/quotes/{symbol}` | GET | 获取单只股票行情 |
| `/api/v1/kline` | GET | 获取K线数据（日/周/月/分钟） |
| `/api/v1/panorama` | GET | 获取市场全景数据 |
| `/api/v1/sentiment` | GET | 获取市场情绪数据 |
| `/api/v1/longhub` | GET | 获取龙虎榜数据 |
| `/api/v1/fund-flow` | GET | 获取资金流向数据 |
| `/api/v1/sector-rotation` | GET | 获取板块轮动数据 |

#### 7.1.2 自选股与组合API

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/watchlist` | GET/POST | 获取/添加自选股 |
| `/api/v1/watchlist/{symbol}` | DELETE | 删除自选股 |
| `/api/v1/portfolio` | GET | 获取组合列表 |
| `/api/v1/portfolio/{id}` | GET | 获取组合详情 |
| `/api/v1/portfolio/optimize` | POST | 组合优化 |
| `/api/v1/position` | GET | 获取持仓明细 |

#### 7.1.3 信号与选股API

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/signal-flag` | GET | 获取信号旗列表 |
| `/api/v1/signal-flag/scan` | POST | 触发信号扫描 |
| `/api/v1/observations` | GET | 获取观察单 |
| `/api/v1/recommendations` | GET | 获取AI推荐 |

#### 7.1.4 量化研究API

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/strategy` | GET/POST | 获取/创建策略 |
| `/api/v1/backtest` | POST | 执行回测 |
| `/api/v1/factor` | GET | 获取因子列表 |
| `/api/v1/factor/validate` | POST | 验证因子有效性 |
| `/api/v1/因子/orthogonalize` | POST | 因子正交化 |

#### 7.1.5 AI Agent API

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/agent-swarm/swarm/run` | POST | 运行Swarm团队 |
| `/api/v1/agent-swarm/swarm/status/{id}` | GET | 获取任务状态 |
| `/api/v1/agent-swarm/capabilities` | GET | 列出所有Agent能力 |
| `/api/v1/ai-committee/analyze` | POST | AI投资委员会分析 |
| `/api/v1/ai-chat/chat` | POST | AI对话 |
| `/api/v1/nl-strategy/generate` | POST | 自然语言生成策略 |

#### 7.1.6 用户与权限API

| 接口路径 | 方法 | 功能说明 |
|---------|------|---------|
| `/api/v1/auth/login` | POST | 用户登录 |
| `/api/v1/auth/logout` | POST | 用户登出 |
| `/api/v1/user/profile` | GET | 获取用户资料 |
| `/api/v1/user/investment-profile` | GET/POST | 投资画像 |
| `/api/v1/trade-journal` | GET/POST | 交易日记 |

### 7.2 API请求示例

#### 示例1：获取股票行情

```bash
# 请求
GET /api/v1/quotes?symbols=600519,000858&market=CN

# 响应
{
  "data": {
    "600519": {
      "symbol": "600519",
      "name": "贵州茅台",
      "price": 1680.50,
      "change_pct": 1.25,
      "volume": 1250000,
      "amount": 2080000000,
      "amplitude": 2.15,
      "turnover": 0.85,
      "update_time": "2026-05-03 14:30:00"
    },
    "000858": {
      "symbol": "000858",
      "name": "五粮液",
      "price": 148.20,
      "change_pct": 0.88,
      "volume": 850000,
      "amount": 125400000,
      "update_time": "2026-05-03 14:30:00"
    }
  }
}
```

#### 示例2：运行AI投资委员会

```bash
# 请求
POST /api/v1/ai-committee/analyze
Content-Type: application/json

{
  "symbol": "600519",
  "market": "CN"
}

# 响应
{
  "symbol": "600519",
  "market": "CN",
  "timestamp": "2026-05-03T14:35:22",
  "steps": [
    {
      "agent_id": "buffett",
      "agent_name": "巴菲特Agent",
      "signal": "bullish",
      "reasoning": "贵州茅台具有强大的品牌护城河，ROE持续保持在30%以上，现金流充裕..."
    },
    {
      "agent_id": "lynch",
      "agent_name": "彼得·林奇Agent",
      "signal": "neutral",
      "reasoning": "技术面上股价处于历史高位，RSI指标显示超买..."
    }
    // ... 其他5个Agent
  ],
  "consensus": {
    "final_action": "bullish",
    "confidence": "68.5%",
    "votes": {
      "bullish": "45%",
      "neutral": "30%",
      "bearish": "15%",
      "risk": "10%"
    }
  }
}
```

#### 示例3：自然语言生成策略

```bash
# 请求
POST /api/v1/nl-strategy/generate
Content-Type: application/json

{
  "description": "当MACD金叉且成交量放大超过1.5倍，同时股价位于20日均线上方时买入，止损设为买入价的5%",
  "name": "MACD金叉策略"
}

# 响应
{
  "strategy_id": "strat_20260503_001",
  "name": "MACD金叉策略",
  "code": "import pandas as pd\nimport numpy as np\n...\n# 完整的Python策略代码",
  "language": "python",
  "estimated_return": "年化15-25%",
  "risk_level": "中等",
  "parameters": [
    {"name": "fast_period", "default": 12, "description": "快线周期"},
    {"name": "slow_period", "default": 26, "description": "慢线周期"},
    {"name": "volume_threshold", "default": 1.5, "description": "成交量放大倍数"}
  ]
}
```

---

## 第八部分：数据结构字典

### 8.1 核心实体

#### 8.1.1 用户表 (users)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| username | VARCHAR(50) | 用户名 |
| email | VARCHAR(100) | 邮箱 |
| password_hash | VARCHAR(255) | 密码哈希 |
| risk_preference | ENUM | 风险偏好(保守/平衡/激进) |
| created_at | DATETIME | 创建时间 |
| last_login | DATETIME | 最后登录 |

#### 8.1.2 自选股表 (watchlist)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| user_id | INT | 用户ID |
| symbol | VARCHAR(20) | 股票代码 |
| market | ENUM | 市场(CN/HK/US/CRYPTO) |
| added_at | DATETIME | 添加时间 |
| notes | TEXT | 备注 |

#### 8.1.3 组合表 (portfolios)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| user_id | INT | 用户ID |
| name | VARCHAR(100) | 组合名称 |
| initial_capital | DECIMAL | 初始资金 |
| current_value | DECIMAL | 当前价值 |
| created_at | DATETIME | 创建时间 |

#### 8.1.4 持仓表 (positions)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| portfolio_id | INT | 组合ID |
| symbol | VARCHAR(20) | 股票代码 |
| shares | INT | 持仓数量 |
| avg_cost | DECIMAL | 平均成本 |
| current_price | DECIMAL | 当前价格 |
| unrealized_pnl | DECIMAL | 未实现盈亏 |

#### 8.1.5 交易记录表 (trades)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| portfolio_id | INT | 组合ID |
| symbol | VARCHAR(20) | 股票代码 |
| direction | ENUM | 方向(买入/卖出) |
| shares | INT | 数量 |
| price | DECIMAL | 价格 |
| amount | DECIMAL | 金额 |
| trade_at | DATETIME | 交易时间 |
| strategy_id | INT | 策略ID |

#### 8.1.6 信号表 (signals)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| symbol | VARCHAR(20) | 股票代码 |
| signal_type | VARCHAR(50) | 信号类型 |
| strength | FLOAT | 信号强度(0-1) |
| ic_value | FLOAT | IC值 |
| generated_at | DATETIME | 生成时间 |
| expires_at | DATETIME | 过期时间 |

#### 8.1.7 因子表 (factors)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| name | VARCHAR(100) | 因子名称 |
| expression | TEXT | 因子表达式 |
| category | VARCHAR(50) | 类别 |
| ic_mean | FLOAT | IC均值 |
| ic_ir | FLOAT | IR值 |
| created_at | DATETIME | 创建时间 |

#### 8.1.8 策略表 (strategies)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT | 主键 |
| user_id | INT | 用户ID |
| name | VARCHAR(100) | 策略名称 |
| code | TEXT | 策略代码 |
| language | VARCHAR(20) | 语言(pythonpine) |
| status | ENUM | 状态(草稿/回测/实盘/停用) |
| created_at | DATETIME | 创建时间 |

---

## 第九部分：部署与运维

### 9.1 环境要求

#### 9.1.1 基础环境

| 组件 | 版本要求 | 说明 |
|------|---------|------|
| Python | >= 3.10 | 推荐3.12 |
| MySQL | >= 8.0 | 主从架构 |
| Redis | >= 6.0 | 缓存与消息队列 |
| Celery | >= 5.0 | 异步任务 |

#### 9.1.2 可选组件

| 组件 | 用途 | 说明 |
|------|------|------|
| Ollama | 本地LLM | 支持gemma4/qwen3/llama3 |
| Qlib | 量化研究 | 因子计算与回测 |
| Nginx | Web服务器 | 反向代理与负载均衡 |

### 9.2 部署步骤

#### 步骤1：环境准备

```bash
# 克隆项目
git clone https://github.com/quant-atlas/quant-atlas.git
cd quant-atlas

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 步骤2：配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置（关键项）
vim .env

# 数据库配置
DATABASE_BACKEND=mysql
MYSQL_HOST=192.168.1.100
MYSQL_PORT=3306
MYSQL_USER=admin
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=quant_atlas

# LLM配置
LLM_PROVIDER=ollama
LANGCHAIN_MODEL_NAME=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434
```

#### 步骤3：初始化数据库

```bash
# 执行迁移
flask db upgrade

# 或运行初始化脚本
python scripts/init_db.py
```

#### 步骤4：启动服务

```bash
# 启动Web服务
python run.py

# 启动Celery Worker（可选）
celery -A app.tasks worker --loglevel=info

# 启动Celery Beat（可选）
celery -A app.tasks beat --loglevel=info
```

### 9.3 Docker部署（推荐）

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_BACKEND=mysql
      - MYSQL_HOST=db
      - LLM_PROVIDER=ollama
    depends_on:
      - db
      - redis

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: quant_atlas
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data

  worker:
    build: .
    command: celery -A app.tasks worker --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis

volumes:
  mysql_data:
  redis_data:
```

```bash
# 启动
docker-compose up -d
```

### 9.4 运维监控

#### 9.4.1 日志管理

```bash
# 查看应用日志
tail -f logs/quant_atlas.log

# 查看Celery日志
celery -A app.tasks inspect active

# 查看Nginx日志
tail -f /var/log/nginx/access.log
```

#### 9.4.2 健康检查

```bash
# API健康检查
curl http://localhost:5000/api/v1/health

# 数据库连接
flask db check

# Redis连接
redis-cli ping
```

#### 9.4.3 性能监控

- **响应时间**: Prometheus + Grafana
- **错误追踪**: Sentry
- **日志聚合**: ELK Stack

---

## 第十部分：安全性设计

### 10.1 认证与授权

#### 10.1.1 用户认证

- **密码加密**: 使用bcrypt或Argon2进行密码哈希
- **会话管理**: JWT Token + Redis Session存储
- **双因素认证**: 支持TOTP（时间同步验证码）
- **登录保护**: 5次失败锁定15分钟

#### 10.1.2 API认证

```python
# 请求头格式
Authorization: Bearer <jwt_token>

# Token包含信息
{
  "user_id": 123,
  "exp": 1715000000,
  "permissions": ["read", "trade"]
}
```

#### 10.1.3 角色权限

| 角色 | 权限 |
|------|------|
| 游客 | 浏览行情 |
| 注册用户 | 自选股、信号、基础分析 |
| 付费用户 | AI分析、策略实验室、组合优化 |
| 管理员 | 用户管理、系统配置 |

### 10.2 数据安全

#### 10.2.1 传输安全

- 全站HTTPS强制
- API签名验证
- 请求参数加密

#### 10.2.2 存储安全

- 数据库敏感字段加密
- 定期备份（每日增量、每周全量）
- 备份加密存储

#### 10.2.3 隐私保护

- 个人信息脱敏显示
- 交易记录隐私保护
- 数据导出权限控制

### 10.3 风控机制

#### 10.3.1 交易风控

- 单日最大亏损限制
- 单笔最大仓位限制
- 交易频率限制
- 异常交易行为拦截

#### 10.3.2 系统风控

- 接口调用频率限制（Rate Limiting）
- SQL注入防护
- XSS攻击防护
- CSRF Token验证

---

## 第十一部分：性能优化指南

### 11.1 数据库优化

#### 11.1.1 索引优化

```sql
-- 自选股查询
CREATE INDEX idx_watchlist_user ON watchlist(user_id);

-- 信号查询
CREATE INDEX idx_signal_symbol_time ON signals(symbol, generated_at DESC);

-- 持仓查询
CREATE INDEX idx_position_portfolio ON positions(portfolio_id, symbol);
```

#### 11.1.2 查询优化

```python
# 使用批量查询代替循环
# 错误
for symbol in symbols:
    quote = get_quote(symbol)  # N次查询

# 正确
quotes = batch_get_quotes(symbols)  # 1次查询
```

#### 11.1.3 缓存策略

| 数据类型 | 缓存时间 | 策略 |
|---------|---------|------|
| 实时行情 | 10秒 | Redis |
| K线数据 | 5分钟 | Redis |
| 用户自选 | 1小时 | Redis |
| 组合数据 | 30秒 | Redis |
| 因子数据 | 1天 | MySQL |

### 11.2 应用优化

#### 11.2.1 异步处理

```python
# 耗时操作使用Celery
@celery.task
def generate_backtest_report(strategy_id):
    # 回测计算
    # 生成报告
    pass

# API立即返回
@app.route('/api/v1/backtest', methods=['POST'])
def start_backtest():
    task = generate_backtest_report.delay(strategy_id)
    return {'task_id': task.id}
```

#### 11.2.2 连接池

```python
# 数据库连接池
engine = create_engine(
    "mysql://user:pass@host/db",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

# Redis连接池
redis_pool = ConnectionPool(
    max_connections=50,
    decode_responses=True
)
```

### 11.3 前端优化

#### 11.3.1 资源优化

- CSS/JS压缩合并
- 图片懒加载
- 静态资源CDN部署
- 浏览器缓存策略

#### 11.3.2 请求优化

- API批量请求
- 请求去重与防抖
- 分页加载

---

## 第十二部分：故障排查指南

### 12.1 常见问题与解决方案

#### 问题1：登录失败，提示"用户不存在"

**可能原因**：
- 用户名输入错误
- 数据库连接失败

**排查步骤**：
1. 检查数据库连接配置
2. 验证users表是否有数据
3. 检查密码哈希算法是否一致

#### 问题2：行情数据不更新

**可能原因**：
- 数据源API限制
- 定时任务未运行

**排查步骤**：
1. 检查Celery任务状态：`celery -A app.tasks inspect scheduled`
2. 查看数据同步日志
3. 测试数据源API连通性

#### 问题3：AI分析无响应

**可能原因**：
- LLM服务未启动
- 模型加载失败

**排查步骤**：
1. 检查Ollama服务状态：`ollama list`
2. 验证模型是否安装：`ollama run qwen3:8b`
3. 检查.env中LLM配置

#### 问题4：回测运行缓慢

**可能原因**：
- 数据量过大
- 策略代码效率低
- 服务器资源不足

**优化方案**：
1. 减少回测时间范围
2. 使用向量化计算替代循环
3. 增加服务器内存

### 12.2 日志分析

#### 关键日志位置

| 日志 | 路径 |
|------|------|
| 应用日志 | `logs/app.log` |
| 错误日志 | `logs/error.log` |
| 访问日志 | `logs/access.log` |
| Celery日志 | `logs/celery.log` |

#### 日志级别

| 级别 | 说明 |
|------|------|
| DEBUG | 详细调试信息 |
| INFO | 正常业务流程 |
| WARNING | 警告但不影响功能 |
| ERROR | 错误导致功能异常 |
| CRITICAL | 系统级严重错误 |

---

## 第十三部分：版本历史与路线图

### 13.1 版本历史

| 版本 | 日期 | 主要更新 |
|------|------|---------|
| v1.0.0 | 2025-06 | 初始版本发布 |
| v1.1.0 | 2025-09 | AI投资委员会、多Agent系统 |
| v1.2.0 | 2025-12 | 自然语言策略、因子工厂 |
| v1.3.0 | 2026-02 | 组合优化、交易机器人 |
| v1.4.0 | 2026-04 | RD-Agent集成、Qlib深度支持 |
| v1.5.0 | 2026-05 | 本地LLM支持、哨兵预警系统 |

### 13.2 未来路线图

#### 2026年Q3目标

- [ ] **多模态分析**：支持图片、语音输入
- [ ] **实时流式响应**：WebSocket长连接，AI分析流式输出
- [ ] **策略市场**：用户可上架/订阅策略
- [ ] **模拟交易联赛**：用户间收益排名

#### 2026年Q4目标

- [ ] **实盘交易对接**：支持多家券商API
- [ ] **基金产品化**：组合可包装为基金产品
- [ ] **机构版**：私有化部署方案
- [ ] **量化大赛**：定期举办策略大赛

#### 2027年目标

- [ ] **Foundation Models**：自研金融大模型
- [ ] **强化学习策略**：RL驱动的自适应策略
- [ ] **全球市场**：扩展至亚太、欧洲市场
- [ ] **生态开放**：开放API、插件市场

---

## 第十四部分：术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| Alpha | Alpha | 超额收益，策略相对于基准的收益 |
| IC | Information Coefficient | 信息系数，预测与实际收益的相关性 |
| IR | Information Ratio | 信息比率，Alpha除以跟踪误差 |
| 回测 | Backtest | 用历史数据验证策略 |
| 因子 | Factor | 股票特征的量化指标 |
| 多因子 | Multi-Factor | 多个因子组合的选股模型 |
| 止损 | Stop Loss | 亏损达到阈值时卖出 |
| 止盈 | Take Profit | 盈利达到目标时卖出 |
| 仓位 | Position | 持有的股票数量 |
| 滑点 | Slippage | 期望成交价与实际成交价之差 |
| 波动率 | Volatility | 资产价格变动幅度 |
| 最大回撤 | Max Drawdown | 账户从最高点到最低点的跌幅 |
| 夏普比率 | Sharpe Ratio | 风险调整后收益指标 |
| 卡玛比率 | Calmar Ratio | 年化收益除以最大回撤 |
| 择时 | Timing | 买入卖出时机的选择 |
| 选股 | Stock Selection | 决定买卖哪些股票 |
| Swarm | Swarm | 多智能体协作系统 |
| Agent | Agent | AI智能体 |
| RAG | Retrieval-Augmented Generation | 检索增强生成 |
| LLM | Large Language Model | 大语言模型 |

---

## 第十五部分：附录

### 15.1 配置参数参考

```python
# 核心配置示例

# 交易配置
POSITION_SIZE = 0.1  # 单只股票仓位上限10%
MAX_POSITIONS = 10   # 最大持仓数量
STOP_LOSS = 0.05    # 默认止损5%
TAKE_PROFIT = 0.15  # 默认止盈15%

# 回测配置
INITIAL_CAPITAL = 1000000  # 初始资金100万
COMMISSION = 0.0003       # 手续费万三
SLIPPAGE = 0.001           # 滑点千一

# 因子配置
MIN_IC = 0.02              # 最小IC阈值
MIN_IR = 0.5               # 最小IR阈值
REBALANCE_FREQ = 'W'       # 周频率调仓

# AI配置
LLM_TEMPERATURE = 0.1      # LLM创造性（低=确定性）
MAX_TOKENS = 2000          # 最大输出token
AGENT_TIMEOUT = 300        # Agent超时时间（秒）
```

### 15.2 贡献者指南

```bash
# 提交代码流程
1. Fork项目
2. 创建功能分支：git checkout -b feature/xxx
3. 编写代码并测试
4. 提交代码：git commit -m "feat: add xxx"
5. 推送分支：git push origin feature/xxx
6. 发起Pull Request

# 代码规范
- 使用Black格式化
- 使用Ruff检查
- 遵循PEP 8
- 提交前运行测试
```

### 15.3 许可证

本项目采用 **MIT License**。

---

*附录完成时间：2026-05-03*  
*文档总字数：约25000字*