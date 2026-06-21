# P8 Prompt Versioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach prompt version/hash metadata to AI analysis calls so LLM call traces can identify which prompt was used.

**Architecture:** Keep existing `PromptEvolutionService` JSONL persistence. Add lightweight helpers for prompt hashing and snapshots. `AiAnalysisService` resolves the current prompt snapshot and passes `prompt_version`/`prompt_hash` through the adapter. Ollama adapter includes those fields in its response.

**Tech Stack:** Python stdlib `hashlib`, existing service registry.

---

### Task 1: Add prompt snapshot helpers and tests

**Files:**
- Modify: `app/modules/ai_agent/services/prompt_evolution_service.py`
- Create: `tests/modules/ai_agent/test_prompt_versioning.py`

- [ ] **Step 1: Add helpers**

```python
def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]

def get_current_prompt_snapshot(self, prompt_id="jarvis_default") -> dict[str, Any]:
    ...
```

Snapshot fields:
- `prompt_id`
- `prompt_version`
- `prompt_hash`
- `prompt`

- [ ] **Step 2: Add rollback**

```python
def rollback(self, prompt_id: str) -> bool:
    if prompt_id not in self._variants: return False
    self._current_best = prompt_id
    return True
```

- [ ] **Step 3: Add tests**
  - `evolve()` creates a stable 16-char hash.
  - `get_current_prompt_snapshot()` returns version/hash/prompt.
  - `rollback()` switches current best.

Expected: PASS.

---

### Task 2: Thread prompt metadata through AI analysis

**Files:**
- Modify: `app/modules/ai_agent/services/ai_analysis_service.py`
- Modify: `app/bootstrap_components/wiring_ai.py`
- Modify: `app/infrastructure/adapters/ollama_prompt_adapter.py`

- [ ] **Step 1: Inject optional prompt service**

```python
prompt_evolution_service: Any | None = None
```

- [ ] **Step 2: Resolve snapshot before adapter calls**

```python
prompt_meta = self._prompt_metadata()
ai_payload = self._ai_adapter.analyze(..., **prompt_meta)
```

- [ ] **Step 3: Ollama adapter includes metadata**

Return fields:
- `prompt_version`
- `prompt_hash`

- [ ] **Step 4: Wire factory**

```python
prompt_evolution_service=reg.get_or_none("prompt_evolution_service")
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/modules/ai_agent/test_prompt_versioning.py -q
```

Expected: PASS.

---

## Self-review checklist

- [ ] Prompt hash is deterministic for the same prompt text.
- [ ] Missing prompt evolution service does not block analysis.
- [ ] Ollama adapter returns prompt metadata even on degraded/failure paths.
- [ ] `AiAnalysisService.analyze()` and `analyze_stream()` pass metadata.
- [ ] No LLM call is made in tests.
