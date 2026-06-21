"""Test Ollama directly."""
import requests
import json

url = "http://localhost:11434/api/generate"
payload = {
    "model": "llama3.2:3b",
    "prompt": "Say 'hi'",
    "stream": False
}

try:
    resp = requests.post(url, json=payload, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
except Exception as e:
    print(f"Error: {e}")