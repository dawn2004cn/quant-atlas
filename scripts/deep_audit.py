import requests
import logging
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('API_Deep_Repair')

# List of endpoints discovered in templates, paired with method
ENDPOINTS = [
    ('/api/v1/market/longhu', 'GET'),
    ('/api/v1/alpha-factory/model-zoo', 'GET'),
    ('/api/v1/long-term-select', 'GET'),
    ('/api/v1/industry-chain', 'GET'),
    ('/api/v1/portfolio/risk-budget', 'GET'),
    ('/api/v1/markets/CN/movements', 'GET'),
    ('/api/v1/selector/run', 'POST'),
    ('/api/v1/markets/CN/quotes', 'GET'),
    ('/api/v1/agent-swarm/experiments', 'GET'),
    ('/api/v1/experiments', 'GET')
]

def get_authenticated_session():
    s = requests.Session()
    # Attempt to login using credentials (assume environment or default)
    try:
        s.post("http://127.0.0.1:5000/login", data={"username": "admin", "password": "changeme"}, timeout=5)
        logger.info("Session authenticated.")
    except Exception as e:
        logger.error(f"Login failed: {e}")
    return s

def deep_audit():
    session = get_authenticated_session()
    base_url = "http://127.0.0.1:5000"
    
    print(f"{'Endpoint':<40} | {'Method':<6} | {'Status':<6} | {'Result'}")
    print("-" * 80)
    
    for ep, method in ENDPOINTS:
        url = f"{base_url}{ep}"
        try:
            # For POST requests we need some dummy body
            body = {"symbol": "600519", "topic": "test", "preset": "investment_committee"} if method == 'POST' else None
            resp = session.request(method, url, json=body, timeout=10)
            
            result = "OK"
            if resp.status_code != 200:
                result = f"FAIL: {resp.status_code}"
            else:
                data = resp.json()
                if not data or (isinstance(data, dict) and not data.get('data')):
                    result = "EMPTY DATA"
            
            print(f"{ep:<40} | {method:<6} | {resp.status_code:<6} | {result}")
            if result != "OK":
                logger.warning(f"Issues at {ep}: {resp.text[:100]}")
        except Exception as e:
            print(f"{ep:<40} | {method:<6} | {'Error':<6} | {e}")

if __name__ == '__main__':
    deep_audit()
