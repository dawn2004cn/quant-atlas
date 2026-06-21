"""Quick test for Ollama connection."""
import os
import sys
os.environ.setdefault("FLASK_APP", "run.py")

# Load env
from dotenv import load_dotenv
load_dotenv()

print(f"Provider: {os.getenv('LANGCHAIN_PROVIDER')}")
print(f"Model: {os.getenv('LANGCHAIN_MODEL_NAME')}")
print(f"Ollama URL: {os.getenv('OLLAMA_BASE_URL')}")

# Test Ollama connection
try:
    from app.infrastructure.agent.providers.llm import build_llm
    llm = build_llm()
    print(f"[OK] LLM created: {llm.model}")
    sys.stdout.flush()

    # Simple test
    print("Testing LLM response...")
    sys.stdout.flush()
    response = llm.invoke("Say 'hi' in 3 characters")
    print(f"[OK] Response: {response.content}")
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()