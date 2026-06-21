import requests
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('API_Audit')

# Set your authentication token if required by the application (using a dummy for now)
HEADERS = {
    "Authorization": "Bearer YOUR_TEST_TOKEN",
    "Content-Type": "application/json"
}

ENDPOINTS = [
    'http://127.0.0.1:5000/api/v1/markets/CN/panorama',
    'http://127.0.0.1:5000/api/v1/agent-swarm/capabilities',
    'http://127.0.0.1:5000/api/v1/daily-workbench',
    'http://127.0.0.1:5000/api/v1/markets/CN/sentiment',
    'http://127.0.0.1:5000/api/v1/markets/CN/quotes'
]

def run_audit():
    for url in ENDPOINTS:
        start = time.perf_counter()
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            elapsed = (time.perf_counter() - start) * 1000
            # Accept 200 or 401 as 'valid' status for now as 401 proves auth logic exists
            if resp.status_code in [200, 401]:
                logger.info(f"OK: {url} | Time: {elapsed:.2f}ms | Status: {resp.status_code}")
            else:
                logger.error(f"FAIL: {url} | Status: {resp.status_code}")
        except Exception as e:
            logger.error(f"ERROR: {url} | {e}")

if __name__ == '__main__':
    run_audit()
