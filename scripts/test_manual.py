# 先手动启动服务器，然后运行此脚本
# python test_manual.py
import requests

BASE = 'http://localhost:5000'
s = requests.Session()

print("1. 登录...")
r = s.post(f'{BASE}/login', data={'username':'admin','password':'changeme'}, timeout=10)
print(f"   Login: {r.status_code}")

print("\n2. 测试端点:")
endpoints = [
    '/api/v1/agent-swarm/capabilities',
    '/api/v1/alpha-factory/status',
    '/api/v1/markets/pulse',
    '/api/v1/markets/CN/sentiment',
    '/api/v1/daily-workbench',
    '/api/v1/agent-swarm/runs',
    '/api/v1/alpha-factory/pipeline',
    '/api/v1/stock-groups',
    '/api/v1/signal-observations',
]

for ep in endpoints:
    try:
        r = s.get(BASE+ep, timeout=5)
        status = 'OK' if r.status_code==200 else f'ERR({r.status_code})'
        print(f"   {status} {ep}")
    except Exception as e:
        print(f"   FAIL {ep}: {str(e)[:40]}")

print("\n完成!")