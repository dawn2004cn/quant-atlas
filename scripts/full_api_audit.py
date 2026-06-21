import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('API_Audit_Full')

BASE_URL = "http://127.0.0.1:5000"
HEADERS = {"Authorization": "Bearer TEST_TOKEN"}

# List of endpoints to audit
ENDPOINTS = [
    ('/api/v1/market/longhu', 'GET'),
    ('/api/v1/alpha-factory/model-zoo', 'GET'),
    ('/api/v1/long-term-select', 'GET'),
    ('/api/v1/industry-chain', 'GET'),
    ('/api/v1/portfolio/risk-budget', 'GET'),
    ('/api/v1/markets/CN/movements', 'GET'),
    ('/api/v1/alpha-factory/paper-trading', 'GET'),
    ('/api/v1/selector/report', 'GET'),
    ('/api/v1/tdx/blocks', 'GET'),
    ('/api/v1/alpha-factory/knowledge/alphas', 'GET'),
    ('/api/v1/retail-assistant/overview', 'GET'),
    ('/api/v1/selector/run', 'POST'),
    ('/api/v1/signal-observations', 'GET'),
    ('/api/v1/integration/stack-status', 'GET'),
    ('/api/v1/tdx/base-data/ingest', 'POST'),
    ('/api/v1/signal-observations/stats', 'GET'),
    ('/api/v1/global/quote', 'GET'),
    ('/api/v1/research/pipeline-status', 'GET'),
    ('/api/v1/backtest', 'POST'),
    ('/api/v1/user/lifecycle', 'GET'),
    ('/api/v1/alpha-factory/lineage', 'GET'),
    ('/api/v1/agent-swarm/swarm/run', 'POST'),
    ('/api/v1/portfolio/holdings', 'GET'),
    ('/api/v1/stock-groups/1/stocks', 'GET'),
    ('/api/v1/signal-flag/scan', 'POST'),
    ('/api/v1/alpha-factory/model/meta-learner', 'GET'),
    ('/api/v1/stock-groups', 'GET'),
    ('/api/v1/signal-flag/pool', 'GET'),
    ('/api/v1/ai/chat', 'POST'),
    ('/api/v1/moments/feed', 'GET'),
    ('/api/v1/user/page-preferences', 'GET'),
    ('/api/v1/system/task-messages', 'GET'),
    ('/api/v1/signal-observations/', 'GET'),
    ('/api/v1/admin/stock-cache', 'GET'),
    ('/api/v1/portfolio/trades/import', 'POST'),
    ('/api/v1/alpha-factory/pipeline', 'GET'),
    ('/api/v1/retail-assistant/portfolio-risk', 'GET'),
    ('/api/v1/user/access-policy', 'GET'),
    ('/api/v1/moments/upload', 'POST'),
    ('/api/v1/investment-managers/leaderboard', 'GET'),
    ('/api/v1/alpha-factory/evolve', 'POST'),
    ('/api/v1/user/audit-trail', 'GET'),
    ('/api/v1/reviews/weekly', 'GET'),
    ('/api/v1/alpha-factory/online-learning', 'GET'),
    ('/api/v1/portfolio/trades', 'GET'),
    ('/api/v1/portfolio/optimize', 'POST'),
    ('/api/v1/system/task-queue-hint', 'GET'),
    ('/api/v1/recommendations/daily', 'GET'),
    ('/api/v1/reviews/daily', 'GET'),
    ('/api/v1/users', 'GET'),
    ('/api/v1/long-term-report', 'GET')
]

def run_audit():
    for ep, method in ENDPOINTS:
        url = f"{BASE_URL}{ep}"
        try:
            resp = requests.request(method, url, headers=HEADERS, timeout=5)
            if resp.status_code == 200:
                logger.info(f"HEALTHY: {ep} ({method})")
            else:
                logger.warning(f"ISSUES: {ep} ({method}) -> Status: {resp.status_code}")
        except Exception as e:
            logger.error(f"ERROR: {ep} ({method}) -> {e}")

if __name__ == '__main__':
    run_audit()
