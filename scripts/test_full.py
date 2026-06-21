import requests

BASE = 'http://localhost:5000'
s = requests.Session()
s.post(f'{BASE}/login', data={'username':'admin','password':'changeme'})

print("=== 全面接口测试 ===\n")

tests = [
    # ===== 核心页面接口 =====
    ("全局市场", [
        ('GET', '/api/v1/markets/CN/sentiment'),
        ('GET', '/api/v1/markets/pulse'),
        ('GET', '/api/v1/global/quote?symbol=NVDA&market=US'),
    ]),
    ("Agent Swarm", [
        ('GET', '/api/v1/agent-swarm/capabilities'),
        ('GET', '/api/v1/agent-swarm/runs'),
    ]),
    ("Alpha Factory", [
        ('GET', '/api/v1/alpha-factory/status'),
        ('GET', '/api/v1/alpha-factory/pipeline'),
        ('GET', '/api/v1/alpha-factory/lineage'),
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
    ]),
    ("系统", [
        ('GET', '/api/v1/system/task-messages?limit=5'),
    ]),
    ("研究", [
        ('GET', '/api/v1/research/pipeline-status'),
    ]),
    # ===== 更多接口 =====
    ("投资经理", [
        ('GET', '/api/v1/investment-managers'),
        ('GET', '/api/v1/investment-managers/teams'),
    ]),
    ("集成", [
        ('GET', '/api/v1/integration/stack-status'),
    ]),
    ("TDX", [
        ('GET', '/api/v1/tdx/blocks'),
        ('GET', '/api/v1/tdx/watchlists'),
        ('GET', '/api/v1/tdx/sectors'),
    ]),
    ("因子", [
        ('GET', '/api/v1/alpha-factory/validate?formula=close>10'),
    ]),
    ("组合", [
        ('GET', '/api/v1/portfolio/snapshot'),
        ('GET', '/api/v1/portfolio/holdings'),
    ]),
    ("信号", [
        ('GET', '/api/v1/signal-flag/dates'),
        ('GET', '/api/v1/signal-flag/pool'),
    ]),
    ("因子仓库", [
        ('GET', '/api/v1/factor-repository/list'),
    ]),
    ("归因", [
        ('POST', '/api/v1/attribution/analyze', {'trades': [], 'factors': []}),
    ]),
    ("AI分析", [
        ('POST', '/api/v1/ai/analyze', {'symbol': '600519', 'market': 'CN'}),
    ]),
    ("诊断", [
        ('GET', '/api/v1/diagnosis/report?symbol=600519'),
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
                r = s.post(url, json=body[0] if body else {}, timeout=5)
            
            total += 1
            if r.status_code == 200:
                passed += 1
                print(f"  OK {ep}")
            else:
                print(f"  ERR({r.status_code}) {ep}")
        except Exception as e:
            total += 1
            print(f"  FAIL {ep}: {str(e)[:40]}")
    print()

print(f"=== 结果: {passed}/{total} 通过 ===")