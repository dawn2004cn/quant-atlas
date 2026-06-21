import requests
import logging
import json
from app.core.container import container
from app.application.services.auth_service import AuthService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('API_Repair')

# 1. Simulate Login to get Token
def get_auth_token():
    # In a real setup, we would login via the auth service or a test credential
    # Here we simulate/use a known test token or login endpoint
    login_url = "http://127.0.0.1:5000/login"
    # Using dummy data for demonstration; adjust based on your actual auth mechanism
    payload = {"username": "admin", "password": "changeme"}
    session = requests.Session()
    session.post(login_url, data=payload) # Assumes session-based auth
    return session

# 2. Endpoints discovered from templates
ENDPOINTS = [
    ('/api/v1/market/longhu', 'GET'),
    ('/api/v1/alpha-factory/model-zoo', 'GET'),
    ('/api/v1/long-term-select', 'GET'),
    ('/api/v1/industry-chain', 'GET'),
    ('/api/v1/portfolio/risk-budget', 'GET'),
    ('/api/v1/markets/CN/movements', 'GET'),
    ('/api/v1/selector/run', 'POST'), # Example of potential 405 if called via GET
    ('/api/v1/markets/CN/quotes', 'GET'),
    ('/api/v1/agent-swarm/experiments', 'GET'),
    ('/api/v1/experiments', 'GET')
]

def audit_api():
    session = get_auth_token()
    base_url = "http://127.0.0.1:5000"
    
    print(f"{'Endpoint':<40} | {'Method':<6} | {'Status':<6} | {'Action'}")
    print("-" * 80)
    
    for ep, method in ENDPOINTS:
        url = f"{base_url}{ep}"
        try:
            resp = session.request(method, url, timeout=5)
            action = "OK"
            if resp.status_code == 405:
                action = "FIX: Check HTTP Method (expected POST/GET?)"
            elif resp.status_code == 404:
                action = "FIX: URL Path Error or missing alias"
            elif resp.status_code == 401:
                action = "FIX: Auth failed"
            
            print(f"{ep:<40} | {method:<6} | {resp.status_code:<6} | {action}")
        except Exception as e:
            print(f"{ep:<40} | {method:<6} | {'Error':<6} | {e}")

if __name__ == '__main__':
    audit_api()
