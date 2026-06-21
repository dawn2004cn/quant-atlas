import requests

BASE = 'http://localhost:5000'
s = requests.Session()
s.post(f'{BASE}/login', data={'username':'admin','password':'changeme'})

print("=== 最终接口测试 ===\n")

tests = [
    # ===== 核心页面接口 (最重要) =====
    ("市场数据", [
        ('GET', '/api/v1/markets/CN/sentiment'),
        ('GET', '/api/v1/markets/pulse'),
    ]),
    ("Agent Swarm", [
        ('GET', '/api/v1/agent-swarm/capabilities'),
        ('GET', '/api/v1/agent-swarm/runs'),
        ('GET', '/api/v1/agent-swarm/experiments'),
    ]),
    ("Alpha Factory", [
        ('GET', '/api/v1/alpha-factory/status'),
        ('GET', '/api/v1/alpha-factory/pipeline'),
        ('GET', '/api/v1/alpha-factory/model-zoo'),
        ('GET', '/api/v1/alpha-factory/lineage'),
        ('GET', '/api/v1/alpha-factory/validate?formula=close>10'),
    ]),
    ("工作台", [
        ('GET', '/api/v1/daily-workbench'),
        ('GET', '/api/v1/recommendations/daily?market=CN'),
    ]),
    ("自选股", [
        ('GET', '/api/v1/stock-groups'),
        ('GET', '/api/v1/signal-observations'),
    ]),
    ("用户", [
        ('GET', '/api/v1/user/page-preferences'),
        ('GET', '/api/v1/user/access-policy'),
        ('GET', '/api/v1/user/audit-trail'),
    ]),
    ("系统", [
        ('GET', '/api/v1/system/task-messages?limit=5'),
    ]),
    ("研究", [
        ('GET', '/api/v1/research/pipeline-status'),
    ]),
    # ===== 其他功能接口 =====
    ("投资经理", [
        ('GET', '/api/v1/investment-managers'),
    ]),
    ("集成", [
        ('GET', '/api/v1/integration/stack-status'),
    ]),
    ("TDX", [
        ('GET', '/api/v1/tdx/blocks'),
        ('GET', '/api/v1/tdx/watchlists'),
    ]),
    ("组合", [
        ('GET', '/api/v1/portfolio/snapshot'),
        ('GET', '/api/v1/portfolio/holdings'),
        ('GET', '/api/v1/portfolio/performance'),
        ('GET', '/api/v1/portfolio/attribution'),
    ]),
    ("信号", [
        ('GET', '/api/v1/signal-flag/dates'),
        ('GET', '/api/v1/signal-flag/pool'),
    ]),
    ("诊断", [
        ('GET', '/api/v1/diagnosis/report?symbol=600519'),
    ]),
    ("时刻", [
        ('POST', '/api/v1/moments', {}),
    ]),
    ("FinGPT", [
        ('GET', '/api/v1/fingpt/predictions'),
        ('GET', '/api/v1/fingpt/sentiments'),
    ]),
    ("AI分析", [
        ('GET', '/api/v1/ai/evidence?symbol=600519'),
    ]),
]

total = 0
passed = 0

for category, endpoints in tests:
    print(f"[{category}]")
    for method, ep, *body in endpoints:
        try:
            url = BASE + ep
            if method == 'GET':
                r = s.get(url, timeout=5)
            else:
                r = s.post(url, json=body[0] if body else {}, timeout=10)
            
            total += 1
            if r.status_code in [200, 201]:
                passed += 1
                print(f"  OK {ep}")
            else:
                print(f"  ERR({r.status_code}) {ep}")
        except Exception as e:
            total += 1
            print(f"  FAIL {ep}: {str(e)[:30]}")
    print()

print(f"=== 结果: {passed}/{total} 通过 ===")

# 计算百分比
pct = int(passed / total * 100)
print(f"通过率: {pct}%")