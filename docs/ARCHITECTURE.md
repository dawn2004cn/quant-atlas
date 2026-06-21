# 架构与重构文档

> 来源：refactoring_plan.md, refactoring_plan_phase5/6/9/13.md, ARCHITECTURE_REDESIGN.md, ARCHITECTURE_ANALYSIS.md, APPLICATION_ANALYSIS.md, full-platform-refactor-roadmap*.plan.md, REMAINING_ISSUES.md, NEXT_ENHANCEMENTS.md, PROJECT_STRUCTURE.md, PLATFORM_BOUNDARY.md, REFACTORING_LOG.md

## 当前架构问题

### 项目规模
| 指标 | 数量 |
|------|------|
| 路由 | 325 |
| 测试 | 79 passed, 2 warnings |
| 服务类 | ~109 |
| 领域端口 | 80+ |

### 违反 SOLID 原则

| 原则 | 问题 | 位置 |
|------|------|------|
| **SRP** | 100+服务在扁平结构 | `app/application/services/` |
| **SRP** | 单文件500+行 | `advanced_features_service.py` |
| **OCP** | 硬编码业务逻辑 | 多处service |
| **LSP** | 未定义抽象 | 缺接口 |
| **ISP** | 胖接口 | ports定义 |
| **DIP** | 直接依赖infrastructure | 189处import |

### 分层架构问题
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

---

## 目标架构（清洁架构）

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                     │
│   routes, api, dtos, validators, response_formatter         │
├─────────────────────────────────────────────────────────────┤
│                     Application Layer                       │
│   use_cases, commands, queries, facades, dtos               │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                           │
│   entities, value_objects, domain_services, repositories     │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                     │
│   adapters, repositories, external_apis, messaging          │
└─────────────────────────────────────────────────────────────┘
```

### 服务分组方案
```
app/application/services/
├── trading/              # 下单/持仓/风险管理
├── market_data/         # 行情数据
├── user/                # 用户管理
├── analytics/           # 分析功能
├── ai/                  # AI服务
├── research/            # 研究功能
├── ops/                 # 运维
└── integration/         # 外部集成
```

---

## 重构阶段

### 第一阶段：建立Domain层 (2天)
- 提取核心实体（trading/, market/, user/）
- 定义Value Objects（money, percentage, date_range, symbol）
- 创建Domain Services（trading/, market/）

### 第二阶段：建立Use Cases (3天)
- 创建 Commands（命令模式）
- 创建 Queries（查询模式）
- 实现 Handlers

### 第三阶段：接口隔离 (2天)
- 定义 IQuoteProvider, IOrderRepository, IPositionRepository 等
- Service 依赖接口而非直接 import infrastructure

### 第四阶段：依赖注入容器 (2天)
- 实现 DIContainer
- 注册所有服务
- 迁移到构造函数注入

### 第五阶段：组织优化 (1天)
- 分组服务文件
- 拆分大文件
- 提取重复代码

---

## 完整平台重构路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase A | 完成 scripts 运行时依赖清零 | ✅ completed |
| Phase B | 实现 A/HK/US/Crypto 多市场 provider 与全景/实时/历史落盘 | ✅ completed |
| Phase C | 实现盘中动态股票池与市场状态驱动策略联动 | ✅ completed |
| Phase D | 扩展个股详情为个股新闻+行业新闻+实时指标聚合 | ✅ completed |
| Phase E | 接入 TradingAgents 适配器与本地 Ollama | ✅ completed |
| Phase F | 补齐契约测试、兼容开关验证与迁移收尾 | ✅ completed |

---

## 下一步增强 (Phase 17-20)

### Phase 17: 集成测试
- 添加 domain → app 组装的全量集成测试
- 添加 API 端点测试
- 添加端到端工作流测试

### Phase 18: 生产就绪
- 添加健康检查端点
- 添加优雅关闭处理
- 添加启动诊断

### Phase 19: 性能调优
- 优化热路径
- 添加连接池
- 添加查询优化

### Phase 20: 文档更新
- 更新 API 文档
- 添加使用示例
- 创建迁移指南

---

## 剩余架构问题

| 问题 | 解决方案 |
|------|---------|
| 100+ 服务在扁平结构 | 分组到 trading/market/user/research/ai/analytics/ops |
| 相似模式重复 | 提取共享工具类 |
| 缺少领域事件 | 创建 domain/events/ |
| 缺少聚合根 | 实现 AggregateRoot 模式 |

---

## 重构日志（近期）

### 2026-06-13 — Phase 16/17 Runtime Compatibility & Bootstrap Refactor

**目标**: 完成 Phase 16/17 运行时兼容性清理，聚焦服务 wiring、声明式路由注册、Flask bootstrap 稳定性。

**变更**:
- 为遗留 `app/application/services/*` 导入添加兼容性 shim
- 修复 `create_app()` bootstrap 因局部变量遮蔽和过时 Phase 16 导入导致的失败
- 在声明式路由中替换错误的 `ApiV1Context.services` 用法为全局 `ServiceRegistry`
- 注册缺失的 Phase 16 服务工厂：`data_lake_manager`, `legacy_migration_service`, `strategy_wizard_service`, `immune_agent_service`
- 修复 Phase 16 领域 schema 缺失：`MarketRegime`, `ExecutionProfile`, `PriceTracer`, `StrategySpec`, `SymbioticExecution`, `StressTestService`
- 修复 `ImmunityThreat` 兼容性：添加默认字段、`from_dict()`、`asdict` 导入
- 修复 `ModuleLocalMemory` 兼容性：`remember_lessons()`, `recall_lessons()`, `load_all()`, `get_memory_stats()`
- 修复 Prompt 反馈冷启动：`PromptEvolutionService.record_feedback()` 现在演化前先播种初始 prompt
- 修复 Alpha Marketplace 访问：添加公开 `AlphaMarketplaceService.wallet` 属性
- 修复 `routes_v1_data_lake.py` API 路径
- 添加 Flask/Werkzeug 兼容性 shim

---
*文档生成基于当前仓库代码结构整理；如有出入以源码为准。*
