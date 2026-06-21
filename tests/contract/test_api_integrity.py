"""Automated API Data Integrity Tests."""

import pytest
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('API_Integrity_Audit')

BASE_URL = "http://127.0.0.1:5000"
# For testing purposes, we assume a testing token is available if auth is enforced
HEADERS = {"Authorization": "Bearer TEST_TOKEN"}

TEST_CASES = [
    {"url": "/api/v1/markets/CN/panorama", "required_keys": ["market", "status", "trend"]},
    {"url": "/api/v1/agent-swarm/capabilities", "required_keys": ["presets", "skills"]},
    {"url": "/api/v1/markets/CN/quotes", "params": {"symbols": "600519"}},
]

@pytest.mark.parametrize("case", TEST_CASES)
def test_api_data_integrity(case):
    url = f"{BASE_URL}{case['url']}"
    params = case.get("params", {})
    
    logger.info(f"Auditing integrity for: {url}")
    response = requests.get(url, params=params, headers=HEADERS, timeout=10)
    
    # 1. Assert Status
    assert response.status_code == 200, f"Endpoint {url} failed with {response.status_code}"
    
    data = response.json()
    
    # 2. Assert Standard Envelope (if present)
    if "code" in data:
        assert data["code"] == 200
        payload = data.get("data")
    else:
        payload = data
        
    # 3. Assert Required Keys
    if "required_keys" in case:
        for key in case["required_keys"]:
            assert key in payload, f"Missing required key: {key} in response for {url}"
            assert payload[key] is not None, f"Key {key} is null in response for {url}"
    
    logger.info(f"Integrity check passed for {url}")
