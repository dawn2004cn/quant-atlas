# Quant Atlas API 测试计划

## 最新测试结果 (2026-05-04 22:50)

### ✅ 已通过的接口 (18/19)
| 接口 | 状态 |
|------|------|
| GET /api/v1/markets/CN/quotes?symbol=600519 | OK |
| GET /api/v1/markets/CN/sentiment | OK |
| GET /api/v1/markets/pulse | OK |
| GET /api/v1/agent-swarm/capabilities | OK |
| GET /api/v1/agent-swarm/runs | OK (已修复) |
| GET /api/v1/agent-swarm/experiments | OK |
| GET /api/v1/alpha-factory/status | OK |
| GET /api/v1/alpha-factory/pipeline | OK |
| GET /api/v1/alpha-factory/model-zoo | OK (已修复) |
| GET /api/v1/alpha-factory/lineage | OK |
| GET /api/v1/daily-workbench | OK |
| GET /api/v1/recommendations/daily?market=CN | OK |
| GET /api/v1/stock-groups | OK |
| GET /api/v1/signal-observations | OK |
| GET /api/v1/user/page-preferences | OK |
| GET /api/v1/user/access-policy | OK |
| GET /api/v1/system/task-messages?limit=10 | OK |
| GET /api/v1/research/pipeline-status | OK |

### ❌ 需要继续修复的接口 (1/19)
| 接口 | 状态 | 问题 |
|------|------|------|
| POST /api/v1/attribution/analyze | ERR(404) | 路由注册问题 |

## 修复历史

### 已修复的问题:
1. **agent-swarm/runs (500→200)** 
   - 修复: 将类方法调用改为实例方法调用
   
2. **alpha-factory/model-zoo (400→200)**
   - 修复: 移除parse_float_param必填验证，改用简单参数解析

3. **url_prefix重复问题**
   - 修复: routes_v1_agent_swarm.py, routes_v1_attribution.py 的 url_prefix

4. **market_service.py 文件损坏**
   - 修复: 重写整个文件，修复重复代码和导入问题

5. **多个__init__.py文件UTF-16 BOM损坏**
   - 修复: dto/__init__.py, adapters/quant/__init__.py

## 待处理
- attribution/analyze 路由404问题 - 需要手动在浏览器测试验证

## 测试方法
```bash
# 启动服务器
python run.py

# 在浏览器访问以下页面测试接口:
- /global-radar (A股数据)
- /ai-committee (AI投资委员会)
- /swarm-dashboard (Swarm仪表板)
- /alpha-factory (因子工厂)
```