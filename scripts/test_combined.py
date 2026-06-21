"""Test Ollama direct API."""
import requests
import json

# First test generate
url = "http://localhost:11434/api/generate"
payload = {"model": "llama3.2:3b", "prompt": "Say 'hi'", "stream": False}
resp = requests.post(url, json=payload, timeout=30)
print(f"Generate Status: {resp.status_code}")

# Then test chat
url = "http://localhost:11434/api/chat"
payload = {"model": "llama3.2:3b", "messages": [{"role": "user", "content": "Say 'hi'"}], "stream": False}
resp = requests.post(url, json=payload, timeout=30)
print(f"Chat Status: {resp.status_code}")

# Test langchain
import os
os.environ["LANGCHAIN_PROVIDER"] = "ollama"
os.environ["LANGCHAIN_MODEL_NAME"] = "llama3.2:3b"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

from app.infrastructure.agent.providers.llm import build_llm
llm = build_llm()
print(f"LLM created: {llm}")

response = llm.invoke("Say 'hi'")
print(f"Langchain response: {response.content}")