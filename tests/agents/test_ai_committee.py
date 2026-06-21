from app.modules.ai_agent.services.ai_committee_service import AICommitteeService
from app.infrastructure.adapters.ollama_prompt_adapter import OllamaPromptAdapter

print('Creating AICommitteeService...')
svc = AICommitteeService(None, OllamaPromptAdapter())
print(f'Service created: {type(svc)}')
print(f'Has run_debate: {hasattr(svc, "run_debate")}')

# Try calling run_debate with a simple test
try:
    result = svc.run_debate('600519', 'CN')
    print(f'Result type: {type(result)}')
    print(f'Result keys: {result.keys() if isinstance(result, dict) else "not a dict"}')
    print(f'Has steps: {"steps" in result}')
    print(f'Has consensus: {"consensus" in result}')
except Exception as e:
    print(f'Error: {e}')