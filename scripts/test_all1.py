import requests

BASE = 'http://localhost:5000'
s = requests.Session()

print("1. 登录...")
r = s.post(f'{BASE}/login', data={'username':'admin','password':'changeme'})
print(f"   Login: {r.status_code}")

print("\n2. 测试核心端点:")

endpoints = [
    # 基础
    ('GET', '/api/v1/markets/CN/quotes?symbol=600519'),
    ('GET', '/api/v1/markets/CN/sentiment'),
    ('GET', '/api/v1/markets/pulse'),
    
    # Agent Swarm
    ('GET', '/api/v1/agent-swarm/capabilities'),
    ('GET', '/api/v1/agent-swarm/runs'),
    ('GET', '/api/v1/agent-swarm/experiments'),
    
    # Alpha Factory
    ('GET', '/api/v1/alpha-factory/status'),
    ('GET', '/api/v1/alpha-factory/pipeline'),
    ('GET', '/api/v1/alpha-factory/model-zoo'),
    ('GET', '/api/v1/alpha-factory/lineage'),
    
    # 工作台
    ('GET', '/api/v1/daily-workbench'),
    ('GET', '/api/v1/recommendations/daily?market=CN'),
    
    # 自选股
    ('GET', '/api/v1/stock-groups'),
    ('GET', '/api/v1/signal-observations'),
    
    # 用户
    ('GET', '/api/v1/user/page-preferences'),
    ('GET', '/api/v1/user/access-policy'),
    
    # 消息
    ('GET', '/api/v1/system/task-messages?limit=10'),
    
    # 归因
    ('GET', '/api/v1/attribution/analyze'),
    
    # 研究
    ('GET', '/api/v1/research/pipeline-status'),
]

results = []
for method, ep in endpoints:
    try:
        r = s.get(BASE+ep, timeout=10)
        if r.status_code == 200:
            results.append(('OK', ep))
            print(f"   OK {ep}")
        elif r.status_code == 401:
            results.append(('AUTH', ep))
            print(f"   AUTH {ep}")
        else:
            results.append(('ERR', ep, r.status_code))
            print(f"   ERR({r.status_code}) {ep}")
    except Exception as e:
        results.append(('FAIL', ep, str(e)[:30]))
        print(f"   FAIL {ep}: {str(e)[:30]}")

ok = sum(1 for r in results if r[0] == 'OK')
print(f"\n=== 结果: {ok}/{len(results)} 通过 ===")