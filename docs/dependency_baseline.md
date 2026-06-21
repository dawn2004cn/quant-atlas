# Dependency Baseline

## Python manifests

| File | Role |
|---|---|
| `pyproject.toml` | Test, ruff, coverage configuration only; no `[project.dependencies]` yet. |
| `requirements.txt` | Main runtime dependency list. |
| `requirements-compute.txt` | Optional compute dependencies. |
| `requirements-qlib.txt` | Optional Qlib dependencies. |
| `scripts/mcp-servers/*/requirements.txt` | Isolated MCP server dependency lists. |
| `gemini-web2api/gemini-web2api/requirements.txt` | Subproject dependency list. |

## Frontend manifests

| File | Role |
|---|---|
| `package.json` | Minimal frontend dependency manifest with `@druid-ui/component`. |
| `package-lock.json` | npm lockfile for the root frontend dependency tree. |
| `bun.lock*` | Not found at repository root during baseline scan. |

## Current risk

- Python now has a primary dependency source in `pyproject.toml` and `requirements.txt` is kept as a compatibility install manifest.
- The drift check must stay green so `requirements.txt` and `pyproject.toml` do not diverge.
- Root frontend currently uses npm-style `package-lock.json`; no bun lockfile was found at root.
- Dependency audit is already wired into CI through `pip-audit`.

## Recommended next steps

1. Keep `pyproject.toml` as the authoritative Python dependency source.
2. Keep `requirements.txt` in sync via `scripts/check_dependency_drift.py`.
3. Keep MCP server manifests isolated unless they share runtime with the main app.
4. Keep npm as the frontend package manager unless a concrete reason appears to switch to bun.
5. Keep the existing `pip-audit` CI job.

## Validation commands

```bash
test -f docs/dependency_baseline.md
python -m pip install --dry-run -r requirements.txt
npm audit --audit-level=high
```
