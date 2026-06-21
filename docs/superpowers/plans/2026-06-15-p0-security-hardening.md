# P0 Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first ordered refactor batch from the audit: remove arbitrary command execution, fix upload path traversal, and harden MySQL destructive DDL operations with lock/audit guards.

**Architecture:** Keep changes surgical. Add a small command-safety helper used by both agent command tools, constrain Flask upload serving to the uploads directory, and wrap destructive MySQL table operations with a named lock plus audit logging. Do not rewrite registry, UI, or business workflows in this batch.

**Tech Stack:** Python 3.12, Flask, pytest, PyMySQL-compatible DBAPI.

---

### Task 1: Add safe command execution and harden agent command tools

**Files:**
- Create: `app/infrastructure/agent/swarm/tools/command_safety.py`
- Modify: `app/infrastructure/agent/swarm/tools/background_tools.py`
- Modify: `app/infrastructure/agent/swarm/tools/bash_tool.py`
- Create: `tests/infrastructure/agent/swarm/test_command_safety.py`

- [ ] **Step 1: Write the failing test**

```python
from app.infrastructure.agent.swarm.tools.command_safety import validate_command, execute_command

def test_rejects_shell_metacharacters():
    assert validate_command("python -c 'print(1); rm -rf /'") == []
```

Expected: FAIL because validation does not exist yet.

- [ ] **Step 2: Implement command_safety.py**

```python
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

_ALLOWED_PROGRAMS = frozenset({"python", "python3", "pytest", "ruff", "uv", "pip"})
_BLOCKED_TOKENS = set(";|&<>(){}[]$`!\\\n\r")


def validate_command(command: str) -> list[str]:
    parts = shlex.split(command)
    if not parts:
        raise ValueError("command_required")
    program = Path(parts[0]).name
    if program not in _ALLOWED_PROGRAMS:
        raise ValueError(f"command_not_allowed:{program}")
    if any(token in _BLOCKED_TOKENS for token in command):
        raise ValueError("shell_metacharacters_not_allowed")
    return parts


def execute_command(command: str, *, cwd: Path | None, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        validate_command(command),
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
```

- [ ] **Step 3: Update BackgroundRunTool**

```python
from app.infrastructure.agent.swarm.tools.command_safety import execute_command

...
try:
    r = execute_command(command, cwd=WORKDIR, timeout=300)
...
```

- [ ] **Step 4: Update BashTool**

```python
from app.infrastructure.agent.swarm.tools.command_safety import execute_command

...
try:
    result = execute_command(command, cwd=Path(cwd) if cwd else None, timeout=_DEFAULT_TIMEOUT)
...
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/infrastructure/agent/swarm/test_command_safety.py -q
```

Expected: PASS.

---

### Task 2: Fix upload path traversal

**Files:**
- Modify: `app/presentation/static_files.py`
- Create: `tests/presentation/test_static_files_security.py`

- [ ] **Step 1: Write the failing test**

```python
from flask import Flask
from app.presentation.static_files import configure_static_files

def test_upload_path_traversal_returns_403(tmp_path):
    app = Flask(__name__)
    static_root = tmp_path / "static"
    static_root.mkdir()
    configure_static_files(app, static_root)
    client = app.test_client()
    response = client.get("/uploads/../static_files.py")
    assert response.status_code == 403
```

Expected: FAIL because `/uploads/<path:filename>` currently serves outside the uploads directory.

- [ ] **Step 2: Implement safe upload resolver**

```python
from pathlib import Path
from flask import Flask, abort, send_from_directory

def _safe_upload_path(base: Path, filename: str) -> Path:
    resolved_base = base.resolve()
    candidate = (resolved_base / filename).resolve()
    try:
        candidate.relative_to(resolved_base)
    except ValueError as exc:
        raise abort(403) from exc
    return candidate
```

- [ ] **Step 3: Wire resolver into route**

```python
@app.route("/uploads/<path:filename>")
def send_upload(filename: str):
    return send_from_directory(
        str(_safe_upload_path(uploads_dir, filename)),
        Path(filename).name,
        max_age=app.get_send_file_max_age(filename),
    )
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/presentation/test_static_files_security.py -q
```

Expected: PASS.

---

### Task 3: Harden MySQL destructive DDL with named locks and audit logging

**Files:**
- Modify: `app/infrastructure/repositories/mysql/mysql_tdx_dayk_repository.py`
- Create: `tests/infrastructure/repositories/mysql/test_mysql_tdx_dayk_repository_ddl_locks.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import Mock
from app.infrastructure.repositories.mysql.mysql_tdx_dayk_repository import MySQLTdxDaykSyncSession

def test_truncate_history_tables_acquires_and_releases_lock():
    conn = Mock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
    port = Mock()
    port.connect.return_value = conn
    repo = MySQLTdxDaykSyncSession(port)
    repo.truncate_history_tables()
    executed = [call.args[0] for call in conn.cursor.return_value.__enter__.return_value.execute.call_args_list]
    assert "SELECT GET_LOCK" in executed[0]
    assert "SELECT RELEASE_LOCK" in executed[-1]
```

Expected: FAIL because DDL methods currently do not acquire/release locks.

- [ ] **Step 2: Add lock helpers to repository**

```python
    def _acquire_mysql_lock(self, name: str, timeout: int = 10) -> Any:
        conn = self._conn_port.connect(autocommit=False)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT GET_LOCK(%s, %s)", (name, timeout))
                row = cur.fetchone()
            locked = bool(row and row[0] == 1)
            if locked:
                self._conn_port.commit(conn)
            else:
                self._conn_port.close(conn)
                raise RuntimeError(f"mysql_lock_not_acquired:{name}")
            return conn
        except Exception:
            self._conn_port.rollback(conn)
            self._conn_port.close(conn)
            raise

    def _release_mysql_lock(self, conn: Any, name: str) -> None:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT RELEASE_LOCK(%s)", (name,))
            self._conn_port.commit(conn)
        finally:
            self._conn_port.close(conn)
```

- [ ] **Step 3: Wrap destructive operations**

```python
lock_name = "quant_atlas_tdx_truncate_history"
conn = self._acquire_mysql_lock(lock_name)
try:
    ...
    logger.info("TRUNCATED history tables suffix=%r", suffix)
finally:
    self._release_mysql_lock(conn, lock_name)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/infrastructure/repositories/mysql/test_mysql_tdx_dayk_repository_ddl_locks.py -q
```

Expected: PASS.

---

### Task 4: Run focused verification suite

**Files:**
- No source changes.

- [ ] **Step 1: Run all P0 tests**

```bash
python -m pytest \
  tests/infrastructure/agent/swarm/test_command_safety.py \
  tests/presentation/test_static_files_security.py \
  tests/infrastructure/repositories/mysql/test_mysql_tdx_dayk_repository_ddl_locks.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run syntax check**

```bash
python -m compileall -q app
```

Expected: PASS.

- [ ] **Step 3: Run targeted regression tests**

```bash
python -m pytest tests/domain/test_market_regime_service.py tests/domain/test_pre_trade_preflight_service.py tests/core/test_circuit_breaker.py -q
```

Expected: PASS.

---

## Self-review checklist

- [ ] No arbitrary `shell=True` remains in `background_tools.py` or `bash_tool.py`.
- [ ] `/uploads/<path:filename>` cannot escape the uploads directory.
- [ ] `truncate_history_tables()` and `swap_reload_tables()` acquire and release MySQL named locks.
- [ ] Tests are deterministic and do not require a live MySQL server.
- [ ] No unrelated UI, registry, or business workflow changes were introduced.
