import requests

BASE = 'http://localhost:5000'
s = requests.Session()
s.post(f'{BASE}/login', data={'username':'admin','password':'changeme'})

print("=== 全量接口测试 ===\n")

tests = [
    # ===== 页面核心功能 =====
    ("市场", [
        ('GET', '/api/v1/markets/CN/sentiment'),
        ('GET', '/api/v1/markets/pulse'),
    ]),
    ("Agent", [
        ('GET', '/api/v1/agent-swarm/capabilities'),
        ('GET', '/api/v1/agent-swarm/runs'),
    ]),
    ("因子", [
        ('GET', '/api/v1/alpha-factory/status'),
        ('GET', '/api/v1/alpha-factory/pipeline'),
    ]),
    ("工作台", [
        ('GET', '/api/v1/daily-workbench'),
    ]),
    ("组合", [
        ('GET', '/api/v1/portfolio/snapshot'),
        ('GET', '/api/v1/portfolio/holdings'),
    ]),
    ("信号", [
        ('GET', '/api/v1/signal-flag/dates'),
    ]),
    ("时刻", [
        ('POST', '/api/v1/moments', {'content': 'test', 'type': 'text'}),
    ]),
    ("AI", [
        ('GET', '/api/v1/ai/evidence?symbol=600519'),
    ]),

    # ===== 完整功能列表 =====
    ("AlphaFactory", [
        ('GET', '/api/v1/alpha-factory/model-zoo'),
        ('GET', '/api/v1/alpha-factory/lineage'),
        ('GET', '/api/v1/alpha-factory/validate?formula=close>10'),
        ('GET', '/api/v1/alpha-factory/correlation'),
        ('GET', '/api/v1/alpha-factory/online-learning'),
        ('GET', '/api/v1/alpha-factory/knowledge/alphas'),
    ]),
    ("推荐", [
        ('GET', '/api/v1/recommendations/daily?market=CN'),
        ('GET', '/api/v1/recommendations/daily?market=US'),
        ('GET', '/api/v1/recommendations/daily?market=HK'),
    ]),
    ("自选", [
        ('GET', '/api/v1/stock-groups'),
        ('GET', '/api/v1/signal-observations'),
    ]),
    ("用户", [
        ('GET', '/api/v1/user/page-preferences'),
        ('GET', '/api/v1/user/access-policy'),
        ('GET', '/api/v1/user/audit-trail'),
    ]),
    ("系统", [
        ('GET', '/api/v1/system/task-messages?limit=10'),
    ]),
    ("研究", [
        ('GET', '/api/v1/research/pipeline-status'),
    ]),
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
        ('GET', '/api/v1/portfolio/performance'),
        ('GET', '/api/v1/portfolio/attribution'),
    ]),
    ("FinGPT", [
        ('GET', '/api/v1/fingpt/predictions'),
        ('GET', '/api/v1/fingpt/sentiments'),
    ]),
    ("诊断", [
        ('GET', '/api/v1/diagnosis/report?symbol=600519'),
    ]),

    # ===== 更多功能 =====
    ("投资经理详情", [
        ('GET', '/api/v1/investment-managers/me'),
        ('GET', '/api/v1/investment-managers/me/teams'),
    ]),
    ("组合更多", [
        ('GET', '/api/v1/portfolio/history'),
        ('GET', '/api/v1/portfolio/trades'),
    ]),
    ("AI更多", [
        ('POST', '/api/v1/ai/chat', {'message': '分析贵州茅台'}),
        ('GET', '/api/v1/ai-committee/analyze?symbol=600519&market=CN'),
    ]),
    ("因子仓库", [
        ('GET', '/api/v1/factor-repository/factors'),
    ]),
    ("因子服务", [
        ('GET', '/api/v1/factor-orthogonalization/jobs'),
        ('GET', '/api/v1/factor-self-correction/jobs'),
    ]),
    ("记忆", [
        ('GET', '/api/v1/memory/stats'),
    ]),
    ("信号更多", [
        ('GET', '/api/v1/signal-flag/pool'),
    ]),
    ("观察更多", [
        ('GET', '/api/v1/signal-observations/statistics'),
    ]),
    ("工作台", [
        ('GET', '/api/v1/daily-workbench/summary'),
    ]),
]

total = 0
passed = 0
failed = []

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
            elif r.status_code in [401, 403]:
                print(f"  AUTH {ep}")
            else:
                failed.append((ep, r.status_code, r.text[:50] if r.text else ''))
                print(f"  ERR({r.status_code}) {ep}")
        except Exception as e:
            total += 1
            failed.append((ep, 'EXCEPTION', str(e)[:30]))
            print(f"  FAIL {ep}")
    print()

print(f"=== 结果: {passed}/{total} 通过 ===")

if failed:
    print(f"\n失败接口 ({len(failed)}个):")
    for ep, code, msg in failed:
        print(f"  {ep}: {code}")