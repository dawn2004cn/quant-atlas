# 代码重构优化方案

## 一、现状分析

### 1.1 项目规模

| 指标 | 数量 |
|------|------|
| 路由 | 325 |
| 测试 | 79 passed, 2 warnings |
| 服务类 | ~109 |
| 领域端口 | 80+ |

### 1.2 当前架构问题

#### 违反SOLID原则

| 原则 | 问题 | 位置 |
|------|------|------|
| **SRP** | 100+服务在扁平结构 | `app/application/services/` |
| **SRP** | 单文件500+行 | `advanced_features_service.py` |
| **SRP** | 多类聚合一文件 | `ai_service.py` |
| **OCP** | 硬编码业务逻辑 | 多处service |
| **LSP** | 未定义抽象 | 缺接口 |
| **ISP** | 胖接口 | ports定义 |
| **DIP** | 直接依赖infrastructure | 189处import |

#### 分层架构问题

```
当前层级:
presentation/  (routes, api)
    ↓ tight coupling
application/    (services - 109个)
    ↓ tight coupling  
infrastructure/ (repositories, adapters)
    ↓
domain/         (ports定义不够)
```

**问题**: 
- Application层直接依赖Infrastructure层
- Domain层太弱，ports定义不足
- 缺少Domain Service层
- 缺少Use Case层

---

## 二、目标架构

### 2.1 清洁架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                     │
│   routes.py, api_v1/, dtos/, validators, response_formatter  │
├─────────────────────────────────────────────────────────────┤
│                     Application Layer                       │
│   use_cases/, commands/, queries/, facades/, dtos/           │
│   (仅编排domain逻辑,不包含业务规则)                              │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                           │
│   entities/, value_objects/, domain_services/, repositories/  │
│   (核心业务逻辑,与框架无关)                                 │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                     │
│   adapters/, repositories/, external_apis/, messaging/     │
│   (技术实现细节)                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 服务分组方案

```
app/application/services/
├── trading/              # 下单/持仓/风险管理
│   ├── order_service.py
│   ├── position_service.py
│   ├── risk_check_service.py
│   └── __init__.py
├── market_data/         # 行情数据
│   ├── quote_service.py
│   ├── history_service.py
│   └── __init__.py
├── user/                # 用户管理
│   ├── auth_service.py
│   ├── profile_service.py
│   └── __init__.py
├── analytics/           # 分析功能
├── ai/                  # AI服务
├── research/            # 研究功能
├── ops/                 # 运维
├── integration/        # 外部集成
├── helpers/            # 已存在
├── immune/             # 已存在
├��─ orchestration/     # 已存在
├── scanner/            # 已存在
├── sentinel/            # 已存在
└── __init__.py
```

---

## 三、重构方案

### 3.1 第一阶段：建立Domain层 (2天)

#### 3.1.1 提取核心实体

```
app/domain/entities/
├── trading/
│   ├── order.py        # Order entity
│   ├── position.py     # Position entity
│   └── portfolio.py   # Portfolio entity
├── market/
│   ├── quote.py        # Quote entity
│   ├── kline.py       # K-line entity
│   └── security.py    # Security entity
├── user/
│   ├── user.py         # User entity
│   ├── watchlist.py    # Watchlist entity
│   └── preferences.py # Preferences entity
└── base.py            # BaseEntity
```

#### 3.1.2 定义Value Objects

```
app/domain/value_objects/
├── money.py           # Money(amount, currency)
├── percentage.py      # Percentage(value)
├── date_range.py      # DateRange(start, end)
├── symbol.py         # Symbol(code, market)
└── trade_signal.py   # TradeSignal(type, strength)
```

#### 3.1.3 创建Domain Services

```
app/domain/services/
├── trading/
│   ├── order_validation.py    # 订单验证逻辑
│   ├── position_calculator.py # 持仓计算
│   └── risk_calculator.py    # 风险计算
├── market/
│   ├── indicator_calculator.py
│   └── sentiment_analyzer.py
└── __init__.py
```

**关键**: Domain Service只包含纯业务逻辑,不依赖任何外部设施

### 3.2 第二阶段：建立Use Cases (3天)

#### 3.2.1 命令模式

```python
# app/application/commands/trading/
class PlaceOrderCommand:
    def __init__(self, symbol, quantity, price, order_type):
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.order_type = order_type

class PlaceOrderHandler:
    def __init__(self, order_repo, risk_checker):
        self._order_repo = order_repo
        self._risk_checker = risk_checker
    
    def handle(self, cmd: PlaceOrderCommand) -> OrderResult:
        # 1. 验证
        # 2. 风控检查
        # 3. 创建订单
        # 4. 保存
        # 5. 返回结果
        pass
```

#### 3.2.2 查询模式

```python
# app/application/queries/trading/
class GetPortfolioQuery:
    def __init__(self, user_id):
        self.user_id = user_id

class GetPortfolioHandler:
    def __init__(self, portfolio_repo):
        self._repo = portfolio_repo
    
    def handle(self, query) -> dict:
        pass
```

#### 3.2.3 文件组织

```
app/application/
├── commands/
│   ├── trading/
│   │   ├── place_order.py
│   │   ├── cancel_order.py
│   │   └── __init__.py
│   ├── user/
│   │   └── __init__.py
│   └── __init__.py
├── queries/
│   ├── trading/
│   │   ├── get_portfolio.py
│   │   └── __init__.py
│   └── __init__.py
└── use_case_registry.py  # 命令注册中心
```

### 3.3 第三阶段：接口隔离 (2天)

#### 3.3.1 当前DIP违规

```python
# Bad: 直接依赖基础设施
from app.infrastructure.database.stock_cache_db import StockCache

class MarketService:
    def get_quote(self, symbol):
        cache = StockCache()  # ❌ 违反DIP
        return cache.get(symbol)
```

#### 3.3.2 修复后

```python
# Good: 依赖抽象接口
from app.domain.ports import QuotePort

class MarketService:
    def __init__(self, quote_port: QuotePort):
        self._quote_port = quote_port
    
    def get_quote(self, symbol):
        return self._quote_port.get_quote(symbol)
```

#### 3.3.3 需创建的接口

| 接口名 | 用途 | 服务 |
|--------|------|------|
| `IQuoteProvider` | 行情数据 | market_service |
| `IOrderRepository` | 订单持久化 | order_service |
| `IPositionRepository` | 持仓持久化 | position_service |
| `IRiskChecker` | 风控检查 | risk_service |
| `IUserPreferences` | 用户偏好 | user_service |
| `IWatchlistRepository` | 自选股持久化 | watchlist_service |

### 3.4 第四阶段：依赖注入容器 (2天)

#### 3.4.1 创建Container

```python
# app/infrastructure/di/container.py
from typing import Type, Callable
from dataclasses import dataclass

@dataclass
class ServiceDescriptor:
    interface: Type
    factory: Callable
    scope: str = "singleton"

class DIContainer:
    def __init__(self):
        self._descriptors: dict[Type, ServiceDescriptor] = {}
        self._singletons: dict[Type, object] = {}
    
    def register(self, interface: Type, factory: Callable, scope="singleton"):
        self._descriptors[interface] = ServiceDescriptor(interface, factory, scope)
    
    def resolve(self, interface: Type) -> object:
        if interface in self._singletons:
            return self._singletons[interface]
        
        desc = self._descriptors.get(interface)
        if not desc:
            raise ValueError(f"Not registered: {interface}")
        
        instance = desc.factory(self)
        if desc.scope == "singleton":
            self._singletons[interface] = instance
        return instance
```

#### 3.4.2 模块注册

```python
# app/infrastructure/di/modules.py
def register_trading(container: DIContainer):
    container.register(IOrderRepository, MySQLOrderRepository)
    container.register(IPositionRepository, MySQLPositionRepository)
    container.register(IRiskChecker, RiskChecker)

def register_market_data(container: DIContainer):
    container.register(IQuoteProvider, AkShareProvider)
    container.register(IHistoryProvider, TushareProvider)
```

#### 3.5 第五阶段：移动服务到分组 (1天)

按照Domain分组移动服务文件:

```
移动规则:
trading/*_service.py → app/application/services/trading/
market_data/*_service.py → app/application/services/market_data/
user/*_service.py → app/application/services/user/
watchlist*_service.py → app/application/services/user/
strategy*_service.py → app/application/services/research/
analysis*_service.py → app/application/services/analytics/
ai_*_service.py → app/application/services/ai/
signal*_service.py → app/application/services/analytics/
```

---

## 四、设计模式应用

### 4.1 创建型

| 模式 | 用途 | 位置 |
|------|------|------|
| Factory | 创建Repository实例 | infrastructure/repositories/factory.py |
| Builder | 构建复杂Query | application/queries/builder.py |
| Prototype | 复制Entity | domain/entities/base.py |
| Singleton | Container单例 | infrastructure/di/container.py |

### 4.2 结构型

| 模式 | 用途 | 位置 |
|------|------|------|
| Adapter | 外部API适配 | infrastructure/adapters/ |
| Facade | 简单接口 | application/facades/ |
| Proxy | 缓存代理 | infrastructure/caching/ |

### 4.3 行为型

| 模式 | 用途 | 位置 |
|------|------|------|
| Command | 命令模式 | application/commands/ |
| Query | 查询模式 | application/queries/ |
| Observer | 事件发布 | domain/events/ |
| Strategy | 策略替换 | domain/services/ |
| Template Method | 流水线 | infrastructure/pipeline/ |

---

## 五、实施路线图

### Phase 1: Domain Layer (Week 1-2)
- [ ] 提取Value Objects
- [ ] 提取Entities  
- [ ] 创建Domain Services
- [ ] 定义Domain Events

### Phase 2: Use Cases (Week 3)
- [ ] 创建Commands
- [ ] 创建Queries
- [ ] 实现Handlers

### Phase 3: DIP Compliance (Week 4)
- [ ] 定义更多Ports
- [ ] Service依赖接口
- [ ] 移除直接基础设施引用

### Phase 4: DI Container (Week 5)
- [ ] 实现Container
- [ ] 注册所有服务
- [ ] 迁移到构造函数注入

### Phase 5: 组织优化 (Week 6)
- [ ] 分组服务文件
- [ ] 拆分大文件
- [ ] 提取重复代码

---

## 六、验证标准

### 6.1 架构验证

- [ ] Application不直接import infrastructure
- [ ] Domain层无外部依赖
- [ ] Service通过接口通信

### 6.2 代码质量

- [ ] 单类<300行
- [ ] 单方法<50行
- [ ] 圈复杂度<10

### 6.3 测试覆盖

- [ ] Unit tests: Domain Services
- [ ] Integration tests: Use Cases
- [ ] API tests: Routes

---

## 七、风险控制

### 7.1 回滚计划

每次变更后验证:
```bash
python -m pytest tests/ -v
flask run
```

### 7.2 渐进式迁移

每次迁移一个服务,验证后再迁移下一个

### 7.3 兼容层

保留原接口,标记deprecated,逐步移除