import requests
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('API_Repair')

# Endpoints discovered
ENDPOINTS = [
    '/api/v1/market/longhu', '/api/v1/alpha-factory/model-zoo', '/api/v1/long-term-select', 
    '/api/v1/industry-chain', '/api/v1/portfolio/risk-budget', '/api/v1/markets/CN/movements', 
    '/api/v1/alpha-factory/paper-trading', '/api/v1/selector/report', '/api/v1/markets/CN/panorama', 
    '/api/v1/quotes', '/api/v1/tdx/blocks', '/api/v1/alpha-factory/knowledge/alphas', 
    '/api/v1/retail-assistant/overview', '/api/v1/selector/run', '/api/v1/signal-observations', 
    '/api/v1/integration/stack-status', '/api/v1/tdx/base-data/ingest', '/api/v1/signal-observations/stats', 
    '/api/v1/global/quote', '/api/v1/research/pipeline-status', '/api/v1/tdx/blocks/', 
    '/api/v1/backtest', '/api/v1/user/lifecycle', '/api/v1/alpha-factory/lineage', 
    '/api/v1/agent-swarm/experiments', '/api/v1/signal-observations/positions', '/api/v1/moments', 
    '/api/v1/user/audit-trail', '/api/v1/global/quote', '/api/v1/reviews/weekly', 
    '/api/v1/alpha-factory/online-learning', '/api/v1/portfolio/trades', '/api/v1/portfolio/optimize', 
    '/api/v1/system/task-queue-hint', '/api/v1/recommendations/daily', '/api/v1/reviews/daily', 
    '/api/v1/users', '/api/v1/experiments', '/api/v1/long-term-report'
]

def repair_api():
    base_url = "http://127.0.0.1:5000"
    headers = {"Authorization": "Bearer TEST_TOKEN"}
    
    for ep in ENDPOINTS:
        url = f"{base_url}{ep}"
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code >= 400:
                logger.warning(f"Endpoint {ep} returning {resp.status_code}, needs attention.")
            else:
                logger.info(f"Endpoint {ep} healthy.")
        except Exception as e:
            logger.error(f"Endpoint {ep} unreachable: {e}")

if __name__ == '__main__':
    repair_api()
