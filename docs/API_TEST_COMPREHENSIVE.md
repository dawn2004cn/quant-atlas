# Quant Atlas 全面接口测试报告

## 测试日期: 2026-05-04
## 结果: 21/31 通过 (68%)

---

## ✅ 正常工作的接口 (21个)

### 核心功能
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
| GET /api/v1/tdx/watchlists | OK |
| GET /api/v1/alpha-factory/validate | OK |
| GET /api/v1/diagnosis/report | OK |

---

## ❌ 需要修复的接口 (10个)

| 接口 | 状态 | 原因 |
|------|------|------|
| GET /api/v1/global/quote | 连接错误 | 服务崩溃 |
| GET /api/v1/investment-managers/teams | 404 | 路由未注册 |
| GET /api/v1/tdx/sectors | 404 | 路由未注册 |
| GET /api/v1/portfolio/summary | 500 | 服务异常 |
| GET /api/v1/portfolio/positions | 500 | 服务异常 |
| GET /api/v1/signal-flags | 404 | 路由未注册 |
| GET /api/v1/signal-flags/statistics | 404 | 路由未注册 |
| GET /api/v1/factor-repository/list | 404 | 路由未注册 |
| POST /api/v1/attribution/analyze | 500 | 服务异常 |
| POST /api/v1/ai/analyze | 500 | 服务异常 |

---

## 页面功能验证

| 页面 | 功能 | 状态 |
|------|------|------|
| /global-radar | 全球资产透视 | ✅ 正常 |
| /ai-committee | AI投资委员会 | ✅ 正常 |
| /swarm-dashboard | Swarm仪表板 | ✅ 正常 |
| /alpha-factory | 因子工厂 | ✅ 正常 |
| /daily-workbench | 日工作台 | ✅ 正常 |

---

## 优先级修复建议

### 高优先级 (影响主要页面)
1. **global/quote** - 全球市场数据获取
2. **ai/analyze** - AI分析功能

### 中优先级 (影响次要功能)
3. **portfolio** - 组合管理
4. **signal-flags** - 信号标记

### 低优先级 (边缘功能)
5. **tdx/sectors** - TDX板块
6. **factor-repository** - 因子仓库