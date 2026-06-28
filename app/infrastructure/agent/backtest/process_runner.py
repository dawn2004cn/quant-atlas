from __future__ import annotations

"""Runner module for executing generated backtest code and collecting artifacts.

Ported from Vibe-Trading.
"""


import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# resource module is Unix-only; gracefully unavailable on Windows
try:
    import resource
except ImportError:
    resource = None  # type: ignore[assignment]

from app.core.logger import get_logger

logger = get_logger(__name__)

# Windows process creation flags for sandboxing
_IS_WINDOWS = sys.platform == "win32"
if _IS_WINDOWS:
    try:
        import win32con
        import win32process
    except ImportError:
        win32process = None  # type: ignore[assignment]
        win32con = None  # type: ignore[assignment]
else:
    win32process = None  # type: ignore[assignment]
    win32con = None  # type: ignore[assignment]


@dataclass
class RunResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    artifacts: dict[str, Path]


_ARTIFACTS_SPEC = {
    "defaults": {"required": ["equity", "metrics", "trades"]},
    "schemas": {
        "equity_csv": {
            "columns": [
                {"name": "timestamp", "type": "string"},
                {"name": "ret", "type": "float"},
                {"name": "equity", "type": "float"},
                {"name": "drawdown", "type": "float"},
            ],
        },
        "metrics_csv": {
            "columns": [
                {"name": "final_value", "type": "float"},
                {"name": "total_return", "type": "float"},
                {"name": "annual_return", "type": "float"},
                {"name": "max_drawdown", "type": "float"},
                {"name": "sharpe", "type": "float"},
                {"name": "win_rate", "type": "float"},
                {"name": "trade_count", "type": "integer"},
            ],
        },
        "trade_log": {
            "columns": [
                {"name": "timestamp", "type": "string"},
                {"name": "code", "type": "string"},
                {"name": "side", "type": "string"},
                {"name": "price", "type": "float"},
                {"name": "qty", "type": "float"},
                {"name": "reason", "type": "string"},
            ],
        },
    },
    "artifacts": {
        "equity": {"schema": "equity_csv", "path": "artifacts/equity.csv"},
        "metrics": {"schema": "metrics_csv", "path": "artifacts/metrics.csv"},
        "trades": {"schema": "trade_log", "path": "artifacts/trades.csv"},
        "positions": {"schema": "positions_csv", "path": "artifacts/positions.csv"},
    },
}


def _expand_artifacts_spec(spec: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(spec, dict):
        return {}
    schemas = spec.get("schemas") or {}
    artifacts = spec.get("artifacts") or {}
    defaults = spec.get("defaults") or {}
    required = set(defaults.get("required") or [])
    expanded: dict[str, dict[str, Any]] = {}
    for name, meta in artifacts.items():
        if not isinstance(meta, dict):
            continue
        schema_name = meta.get("schema")
        schema = schemas.get(schema_name, {}) if isinstance(schemas, dict) else {}
        expanded[name] = {
            "path": meta.get("path"),
            "required": bool(meta.get("required", name in required)),
            "columns": meta.get("columns") or schema.get("columns"),
        }
    return expanded


class Runner:
    """Execute entry scripts inside a run directory and collect outputs."""

    def __init__(self, timeout: int = 300, artifacts_spec: dict[str, Any] | None = None) -> None:
        self.timeout = timeout
        self.artifacts_spec = artifacts_spec or _ARTIFACTS_SPEC
        self.artifact_entries = _expand_artifacts_spec(self.artifacts_spec)

    def _python_ready(self, python_cmd: str) -> bool:
        try:
            probe = subprocess.run(  # python_cmd from local filesystem scan; -c script is hardcoded
                [python_cmd, "-c", "import pandas,numpy; print('ok')"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=20,
            )
            return probe.returncode == 0
        except Exception:
            return False

    def _pick_python_interpreter(self) -> str:
        project_root = Path(__file__).resolve().parents[3]
        candidates = [
            project_root / ".venv" / "Scripts" / "python.exe",
            project_root / ".venv" / "bin" / "python",
            Path(sys.executable),
        ]
        for path in candidates:
            if not path.exists():
                continue
            cmd = str(path)
            if self._python_ready(cmd):
                return cmd
        return sys.executable

    def _build_runtime_env(self, run_dir: Path, *, pythonpath_extra: Path | None = None) -> dict[str, str]:
        """Build a restricted environment for the subprocess.

        Strips all secrets, API keys, tokens, and credentials from the
        inherited ``os.environ`` to prevent leaked secrets from being
        accessible to user-generated backtest scripts.
        """
        # Whitelist: only keep safe, non-sensitive variables
        SAFE_PREFIXES = (
            "HOME", "TEMP", "TMP", "PATH", "PATHEXT",
            "SYSTEMROOT", "COMSPEC",
            "PYTHONUNBUFFERED", "PYTHONIOENCODING", "PYTHONUTF8",
            "PYTHONPATH",
        )
        SAFE_EXACT = frozenset({
            "OS", "PROCESSOR_ARCHITECTURE",
        })
        sensitive_patterns = (
            "PASSWORD", "SECRET", "TOKEN", "API_KEY", "APIKEY",
            "ACCESS_KEY", "PRIVATE_KEY", "CREDENTIAL", "AUTH",
            "SESSION_KEY", "CLIENT_SECRET", "DB_URL", "DATABASE_URL",
            "REDIS_URL", "MONGO_URI", "MONGODB_URI",
            "CLICKHOUSE", "ALIBABA", "AKSHARE", "TUSHARE",
            "BAOSTOCK", "QUANDL", "WIND", "IFIND",
        )

        env: dict[str, str] = {}
        for key, value in os.environ.items():
            # Keep whitelisted prefix-based variables
            if any(key.startswith(prefix) for prefix in SAFE_PREFIXES):
                env[key] = value
                continue
            # Keep exact-match safe variables
            if key in SAFE_EXACT:
                env[key] = value
                continue
            # Block anything that looks sensitive
            upper = key.upper()
            if any(pat in upper for pat in sensitive_patterns):
                logger.debug("Stripping sensitive env var: %s", key)
                continue
            # Default: do not pass through unknown env vars
            # This is the secure default — only explicit safe vars are passed

        if pythonpath_extra:
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = str(pythonpath_extra) + (os.pathsep + existing if existing else "")

        return env

    def execute(
        self,
        entry_script: Path,
        run_dir: Path,
        *,
        cwd: Path | None = None,
        cli_args: list[str] | None = None,
    ) -> RunResult:
        logger.info("Runner: executing %s", entry_script)
        stdout_path = run_dir / "logs" / "runner_stdout.txt"
        stderr_path = run_dir / "logs" / "runner_stderr.txt"
        stdout_path.parent.mkdir(parents=True, exist_ok=True)

        start_time = time.time()

        effective_cwd = cwd or entry_script.parent
        pythonpath_extra = cwd if cwd else None
        env = self._build_runtime_env(run_dir, pythonpath_extra=pythonpath_extra)
        python_cmd = self._pick_python_interpreter()

        cmd = [python_cmd, str(entry_script)]
        if cli_args:
            cmd.extend(cli_args)

        # Resource limits: prevent runaway scripts from consuming all system resources
        # CPU time limit: 1.5x the configured timeout
        cpu_limit = int(self.timeout * 1.5)
        # Virtual memory limit: 2GB
        mem_limit = 2 * 1024 * 1024 * 1024

        process = None
        try:
            # Set resource limits before spawning the process (Unix only)
            old_soft, old_hard = 0, 0
            old_mem_soft, old_mem_hard = 0, 0
            try:
                if resource is None:
                    raise AttributeError("resource module unavailable")
                old_soft, old_hard = resource.getrlimit(resource.RLIMIT_CPU)
                old_mem_soft, old_mem_hard = resource.getrlimit(resource.RLIMIT_AS)
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
                resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
            except (ValueError, OSError, AttributeError):
                # Windows (no resource module) or unsupported: skip resource limits but keep timeout
                pass

            # Windows-specific process isolation: detach from parent console/job
            creation_flags = 0
            if _IS_WINDOWS and win32con is not None:
                creation_flags |= win32con.CREATE_BREAKAWAY_FROM_JOB  # type: ignore[attr-defined]
                creation_flags |= win32con.DETACHED_PROCESS  # type: ignore[attr-defined]

            process = subprocess.run(  # cmd is internally constructed [python_cmd, entry_script] from controlled Path
                cmd,
                cwd=str(effective_cwd),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
                encoding="utf-8",
                errors="ignore",
                creationflags=creation_flags if _IS_WINDOWS else 0,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Runner: subprocess timed out after %ds for %s", self.timeout, entry_script)
            if process is not None:
                process.kill()
            return RunResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {self.timeout}s",
                artifacts={},
            )
        finally:
            # Restore original resource limits (best-effort, may fail on Windows)
            try:
                if old_soft or old_hard:
                    resource.setrlimit(resource.RLIMIT_CPU, (old_soft, old_hard))
                if old_mem_soft or old_mem_hard:
                    resource.setrlimit(resource.RLIMIT_AS, (old_mem_soft, old_mem_hard))
            except (ValueError, OSError, AttributeError):
                logger.debug("Resource limit restore failed (expected on Windows)", exc_info=True)

        elapsed = time.time() - start_time
        logger.info("Runner: subprocess finished in %.2fs", elapsed)

        stdout_path.write_text(process.stdout, encoding="utf-8")
        stderr_path.write_text(process.stderr, encoding="utf-8")

        artifacts: dict[str, Path] = {}
        for name, info in self.artifact_entries.items():
            rel_path = info.get("path")
            if not isinstance(rel_path, str) or not rel_path.strip():
                continue
            target = run_dir / Path(rel_path)
            if target.exists():
                artifacts[name] = target

        success = process.returncode == 0
        return RunResult(
            success=success,
            exit_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
            artifacts=artifacts,
        )
