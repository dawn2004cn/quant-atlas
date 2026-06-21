# API 测试计划 - Quant Atlas

## 测试目标
确保所有HTML页面调用的API接口不报错、有数据返回。

---

## 测试接口清单

### 1. AI投资委员会 `/ai-committee`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/ai-committee/analyze` | GET | symbol=600519&market=CN | 返回辩论结果 |

### 2. 全球资产透视塔 `/global-radar`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/markets/CN/quotes` | GET | symbol=600519 | 返回A股行情 |
| `/api/v1/global/quote` | GET | symbol=AAPL&market=US | 返回美股行情 |

### 3. 日工作台 `/daily-workbench`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/daily-workbench` | GET | - | 返回工作台数据 |
| `/api/v1/recommendations/daily` | GET | market=CN | 返回推荐 |
| `/api/v1/quotes` | GET | symbol=600519&market=CN | 返回行情 |
| `/api/v1/markets/CN/sentiment` | GET | - | 返回市场情绪 |

### 4. 智能分析 `/ai-analysis`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/ai/analyze` | POST | symbol=600519 | 返回分析结果 |

### 5. AI对冲基金 `/ai-hedge-fund`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/ai-hedge-fund/analyze` | GET | symbol=AAPL | 返回分析 |

### 6. Swarm相关 `/agent-swarm`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/agent-swarm/capabilities` | GET | - | 返回能力列表 |
| `/api/v1/agent-swarm/experiments` | GET | - | 返回实验列表 |
| `/api/v1/agent-swarm/runs` | GET | - | 返回运行列表 |

### 7. 因子工厂 `/alpha-factory`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/alpha-factory/pipeline` | GET | - | 返回流水线 |
| `/api/v1/alpha-factory/model-zoo` | GET | - | 返回模型库 |
| `/api/v1/alpha-factory/status` | GET | - | 返回状态 |
| `/api/v1/alpha-factory/validate` | POST | formula=close>10 | 返回验证结果 |

### 8. 因子演化 `/factor-evolution`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/alpha-factory/lineage` | GET | - | 返回因子血缘 |

### 9. 市场全景 `/market-panorama`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/markets/pulse` | GET | - | 返回市场脉搏 |

### 10. 自选股 `/self-stocks`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/stock-groups` | GET | - | 返回股票组 |
| `/api/v1/stock-groups/{id}/stocks` | GET | - | 返回组内股票 |

### 11. 用户相关 `/user`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/user/page-preferences` | GET | - | 返回页面偏好 |
| `/api/v1/user/access-policy` | GET | - | 返回访问策略 |

### 12. 消息中心 `/message-center`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/system/task-messages` | GET | limit=10 | 返回消息 |

### 13. 信号观察 `/signal-observations`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/signal-observations` | GET | - | 返回观察列表 |

### 14. 研究管线 `/research-pipeline`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/research/pipeline-status` | GET | - | 返回管线状态 |

### 15. 归因分析 `/attribution-dashboard`

| 接口 | 方法 | 测试参数 | 预期结果 |
|------|------|----------|----------|
| `/api/v1/attribution/analyze` | GET | - | 返回归因分析 |

---

## 测试脚本

### 批量测试脚本 (Python)

```python
import requests
import json

BASE_URL = "http://localhost:5000"

# 需要登录的接口（先登录获取session）
LOGIN_REQUIRED = []

# 公开接口（无需登录）
PUBLIC_ENDPOINTS = [
    ("GET", "/api/v1/markets/CN/quotes?symbol=600519"),
    ("GET", "/api/v1/markets/CN/sentiment"),
    ("GET", "/api/v1/markets/pulse"),
    ("GET", "/api/v1/agent-swarm/capabilities"),
    ("GET", "/api/v1/alpha-factory/status"),
    ("GET", "/api/v1/alpha-factory/pipeline"),
]

# 登录后再测试的接口
AUTH_ENDPOINTS = [
    ("GET", "/api/v1/ai-committee/analyze?symbol=600519&market=CN"),
    ("GET", "/api/v1/ai/analyze?symbol=600519"),
    ("GET", "/api/v1/ai-hedge-fund/analyze?symbol=AAPL"),
    ("GET", "/api/v1/agent-swarm/experiments"),
    ("GET", "/api/v1/agent-swarm/runs"),
    ("GET", "/api/v1/daily-workbench"),
    ("GET", "/api/v1/recommendations/daily?market=CN"),
    ("GET", "/api/v1/quotes?symbol=600519&market=CN"),
    ("GET", "/api/v1/stock-groups"),
    ("GET", "/api/v1/signal-observations"),
    ("GET", "/api/v1/alpha-factory/model-zoo"),
    ("GET", "/api/v1/alpha-factory/lineage"),
    ("GET", "/api/v1/user/page-preferences"),
    ("GET", "/api/v1/user/access-policy"),
    ("GET", "/api/v1/system/task-messages?limit=10"),
    ("GET", "/api/v1/research/pipeline-status"),
    ("GET", "/api/v1/attribution/analyze"),
]

def test_endpoint(method, path, session=None):
    url = BASE_URL + path
    try:
        if method == "GET":
            r = session.get(url) if session else requests.get(url)
        else:
            r = session.post(url) if session else requests.post(url)
        
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == 200 or data.get("status") == "ok":
                return "✅ PASS", data
            else:
                return "⚠️  DATA ERROR", data
        elif r.status_code == 401:
            return "🔒  NEED LOGIN", {}
        else:
            return f"❌ ERROR {r.status_code}", {}
    except Exception as e:
        return f"❌ EXCEPTION: {e}", {}

def run_tests():
    print("=" * 60)
    print("公开接口测试 (无需登录)")
    print("=" * 60)
    
    results = []
    for method, path in PUBLIC_ENDPOINTS:
        status, data = test_endpoint(method, path)
        results.append((path, status))
        print(f"{status} {path}")
    
    print("\n" + "=" * 60)
    print("认证接口测试 (需先登录)")
    print("=" * 60)
    
    # 登录
    session = requests.Session()
    login_data = {"username": "admin", "password": "admin123"}
    try:
        r = session.post(f"{BASE_URL}/auth/login", data=login_data)
        print(f"登录状态: {r.status_code}")
    except:
        print("登录失败，使用公开接口测试结果")
    
    for method, path in AUTH_ENDPOINTS:
        status, data = test_endpoint(method, path, session)
        results.append((path, status))
        print(f"{status} {path}")
    
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    pass_count = sum(1 for _, s in results if "PASS" in s)
    error_count = sum(1 for _, s in results if "ERROR" in s or "EXCEPTION" in s)
    login_count = sum(1 for _, s in results if "LOGIN" in s)
    
    print(f"通过: {pass_count}, 错误: {error_count}, 需要登录: {login_count}")
    
    return results

if __name__ == "__main__":
    run_tests()
```

---

## 测试步骤

### 步骤1: 启动服务
```bash
python run.py
```

### 步骤2: 运行测试脚本
```bash
python test_api_endpoints.py
```

### 步骤3: 逐个验证失败的接口

1. 记录失败的接口
2. 检查日志: `app/logs/`
3. 修复代码问题
4. 重新测试

---

## 预期结果

- **通过率目标**: 90%以上
- 公开接口: 100%通过
- 认证接口: 登录后100%通过

---

## 常见问题排查

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| 401 Unauthorized | 需要登录 | 先访问登录页面 |
| 500 Error | 服务端异常 | 查看日志 |
| 空数据 | 数据源问题 | 检查缓存/数据库 |
| 超时 | 第三方API慢 | 增加超时时间 |