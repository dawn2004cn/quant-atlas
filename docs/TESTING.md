# 测试报告汇总

> 来源：API_TEST_PLAN.md, API_TEST_STATUS.md, API_TEST_FINAL.md, API_TEST_COMPREHENSIVE.md, test_plan.md, testing_strategy.md

## API 全面接口测试报告

### 测试日期: 2026-05-04
### 结果: 21/31 通过 (68%)

### ✅ 正常工作的接口 (21个)

#### 核心功能
| 接口 | 状态 |
|------|------|
| GET /api/v1/markets/CN/sentiment | OK |
| GET /api/v1/markets/pulse | OK |
| GET /api/v1/agent-swarm/capabilities | OK |
| GET /api/v1/agent-swarm/runs | OK |
| GET /api/v1/alpha-factory/status | OK |
| GET /api/v1/alpha-factory/pipeline | OK |
| GET /api/v1/alpha-factory/lineage | OK |
| GET /api/v1/daily-workbench | OK |
| GET /api/v1/recommendations/daily | OK |
| GET /api/v1/stock-groups | OK |
| GET /api/v1/signal-observations | OK |
| GET /api/v1/user/page-preferences | OK |
| GET /api/v1/user/access-policy | OK |
| GET /api/v1/system/task-messages | OK |
| GET /api/v1/research/pipeline-status | OK |
| GET /api/v1/investment-managers | OK |
| GET /api/v1/integration/stack-status | OK |
| GET /api/v1/tdx/blocks | OK |

## 测试策略

### 单元/集成/端对端分层
| 层级 | 工具 | 范围 | 目标 |
|------|------|------|------|
| 单元测试 | pytest | 服务类、domain 逻辑、工具函数 | 快速、无外部依赖 |
| 集成测试 | pytest + test client | 路由 → Service → Repository/Provider | 验证分层组装 |
| 端到端测试 | requests + test client | 登录 → 业务操作 → 数据一致性 | 关键用户旅程 |

### 关键验证点
- SOLID 合规：Application 不直接 import Infrastructure
- 服务分组验证：新服务落在对应分组下
- 接口隔离验证：无依赖不必要接口的方法
- 覆盖策略：核心路径 80%+，新功能 100% 单测

---
*文档生成基于当前仓库代码结构整理；如有出入以源码为准。*
