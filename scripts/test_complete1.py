import requests

BASE = 'http://localhost:5000'
s = requests.Session()
s.post(f'{BASE}/login', data={'username':'admin','password':'changeme'})

print("=== 完整接口测试 ===\n")

tests = [
    # ===== 市场 =====
    ("市场数据", [
        ('GET', '/api/v1/markets/CN/quotes?symbol=600519'),
        ('GET', '/api/v1/markets/CN/sentiment'),
        ('GET', '/api/v1/markets/pulse'),
        ('GET', '/api/v1/global/quote?symbol=AAPL&market=US'),
        ('GET', '/api/v1/global/quote?symbol=00700&market=HK'),
    ]),
    # ===== Agent Swarm =====
    ("Agent Swarm", [
        ('GET', '/api/v1/agent-swarm/capabilities'),
        ('GET', '/api/v1/agent-swarm/runs'),
        ('GET', '/api/v1/agent-swarm/experiments'),
        ('POST', '/api/v1/agent-swarm/swarm/run', {'preset': 'investment_committee', 'symbol': '600519'}),
        ('GET', '/api/v1/agent-swarm/swarm/status/test'),
    ]),
    # ===== Alpha Factory =====
    ("Alpha Factory", [
        ('GET', '/api/v1/alpha-factory/status'),
        ('GET', '/api/v1/alpha-factory/pipeline'),
        ('GET', '/api/v1/alpha-factory/model-zoo'),
        ('GET', '/api/v1/alpha-factory/lineage'),
        ('GET', '/api/v1/alpha-factory/validate?formula=close>10'),
        ('GET', '/api/v1/alpha-factory/correlation'),
        ('GET', '/api/v1/alpha-factory/online-learning'),
        ('GET', '/api/v1/alpha-factory/knowledge/alphas'),
    ]),
    # ===== 工作台 =====
    ("工作台", [
        ('GET', '/api/v1/daily-workbench'),
        ('GET', '/api/v1/recommendations/daily?market=CN'),
        ('GET', '/api/v1/recommendations/daily?market=US'),
    ]),
    # ===== 自选股 =====
    ("自选股", [
        ('GET', '/api/v1/stock-groups'),
        ('GET', '/api/v1/stock-groups/1/stocks'),
        ('GET', '/api/v1/signal-observations'),
    ]),
    # ===== 用户 =====
    ("用户", [
        ('GET', '/api/v1/user/page-preferences'),
        ('PUT', '/api/v1/user/page-preferences', {'page': 'dashboard', 'settings': {}}),
        ('GET', '/api/v1/user/access-policy'),
        ('GET', '/api/v1/user/audit-trail'),
    ]),
    # ===== 系统 =====
    ("系统", [
        ('GET', '/api/v1/system/task-messages?limit=5'),
        ('GET', '/api/v1/system/health'),
    ]),
    # ===== 研究 =====
    ("研究", [
        ('GET', '/api/v1/research/pipeline-status'),
    ]),
    # ===== 投资经理 =====
    ("投资经理", [
        ('GET', '/api/v1/investment-managers'),
        ('GET', '/api/v1/investment-managers/1'),
    ]),
    # ===== 集成 =====
    ("集成", [
        ('GET', '/api/v1/integration/stack-status'),
    ]),
    # ===== TDX =====
    ("TDX", [
        ('GET', '/api/v1/tdx/blocks'),
        ('GET', '/api/v1/tdx/watchlists'),
        ('GET', '/api/v1/tdx/sectors'),
        ('GET', '/api/v1/tdx/blocks/stock'),
    ]),
    # ===== 组合 =====
    ("组合", [
        ('GET', '/api/v1/portfolio/snapshot'),
        ('GET', '/api/v1/portfolio/holdings'),
        ('GET', '/api/v1/portfolio/positions'),
        ('GET', '/api/v1/portfolio/performance'),
    ]),
    # ===== 信号 =====
    ("信号", [
        ('GET', '/api/v1/signal-flag/dates'),
        ('GET', '/api/v1/signal-flag/pool'),
    ]),
    # ===== 因子仓库 =====
    ("因子仓库", [
        ('GET', '/api/v1/factor-repository/list'),
        ('GET', '/api/v1/factor-repository/factors'),
    ]),
    # ===== 归因 =====
    ("归因", [
        ('POST', '/api/v1/attribution/analyze', {'trades': [], 'factors': []}),
        ('GET', '/api/v1/portfolio/attribution'),
    ]),
    # ===== AI分析 =====
    ("AI分析", [
        ('POST', '/api/v1/ai/analyze', {'symbol': '600519', 'market': 'CN'}),
        ('POST', '/api/v1/ai/evidence', {'symbol': '600519'}),
        ('GET', '/api/v1/ai-committee/analyze?symbol=600519&market=CN'),
    ]),
    # ===== 诊断 =====
    ("诊断", [
        ('GET', '/api/v1/diagnosis/report?symbol=600519'),
        ('GET', '/api/v1/diagnosis/stock?symbol=600519'),
    ]),
    # ===== Moments =====
    ("时刻", [
        ('GET', '/api/v1/moments'),
        ('POST', '/api/v1/moments', {'content': 'test'}),
    ]),
    # ===== 行业链 =====
    ("行业链", [
        ('GET', '/api/v1/industry-chain/tree'),
        ('GET', '/api/v1/industry-chain/stocks?industry=科技'),
    ]),
    # ===== 评论 =====
    ("评论", [
        ('GET', '/api/v1/reviews'),
        ('GET', '/api/v1/reviews/summary'),
    ]),
    # ===== 生命周期的 =====
    ("生命周期", [
        ('GET', '/api/v1/user/settings'),
        ('GET', '/api/v1/user/export'),
    ]),
    # ===== 助手 =====
    ("助手", [
        ('GET', '/api/v1/retail-assistant/snapshot'),
    ]),
    # ===== 交易计划 =====
    ("交易计划", [
        ('GET', '/api/v1/trade-plan/list'),
        ('GET', '/api/v1/trade-plan/1'),
    ]),
    # ===== FinGPT =====
    ("FinGPT", [
        ('GET', '/api/v1/fingpt/predictions'),
        ('GET', '/api/v1/fingpt/sentiments'),
    ]),
    # ===== 因子正交化 =====
    ("因子正交化", [
        ('GET', '/api/v1/factor-orthogonalization/status'),
    ]),
    # ===== 因子自修正 =====
    ("因子自修正", [
        ('GET', '/api/v1/factor-self-correction/status'),
    ]),
    # ===== 内存优化 =====
    ("内存优化", [
        ('GET', '/api/v1/memory-optimization/stats'),
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
                failed.append((ep, r.status_code))
                print(f"  ERR({r.status_code}) {ep}")
        except Exception as e:
            total += 1
            failed.append((ep, str(e)[:30]))
            print(f"  FAIL {ep}: {str(e)[:30]}")
    print()

print(f"=== 结果: {passed}/{total} 通过 ===")

if failed:
    print("\n失败的接口:")
    for ep, err in failed:
        print(f"  - {ep}: {err}")