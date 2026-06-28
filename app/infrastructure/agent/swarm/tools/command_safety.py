from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

_ALLOWED_PROGRAMS = frozenset({
    "pytest",
    "pytest.exe",
    "ruff",
    "ruff.exe",
})
_ALLOWED_PYTHON_MODULE_COMMANDS = frozenset({
    ("python", "-m", "pytest"),
    ("python3", "-m", "pytest"),
    ("python.exe", "-m", "pytest"),
    ("python", "-m", "compileall"),
    ("python3", "-m", "compileall"),
    ("python.exe", "-m", "compileall"),
})
_BLOCKED_TOKENS = set(";|&<>(){}[]$`!\\\n\r")
_BLOCKED_PYTHON_FLAGS = frozenset({"-c", "--command"})


def _validate_argv_parts(parts: list[str]) -> None:
    program = Path(parts[0]).name
    if program.startswith("python"):
        for flag in _BLOCKED_PYTHON_FLAGS:
            if flag in parts:
                raise ValueError("python_c_execution_not_allowed")
    for arg in parts[1:]:
        if any(ch in arg for ch in _BLOCKED_TOKENS):
            raise ValueError("shell_metacharacters_not_allowed")
        if ".." in arg.replace("\\", "/").split("/"):
            raise ValueError("path_traversal_not_allowed")


def validate_command(command: str) -> list[str]:
    if not isinstance(command, str) or not command.strip():
        raise ValueError("command_required")

    if any(ch in command for ch in _BLOCKED_TOKENS):
        raise ValueError("shell_metacharacters_not_allowed")

    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise ValueError("command_parse_failed") from exc

    if not parts:
        raise ValueError("command_required")

    program = Path(parts[0]).name
    if program.startswith("python"):
        for flag in _BLOCKED_PYTHON_FLAGS:
            if flag in parts:
                raise ValueError("python_c_execution_not_allowed")

    if program in _ALLOWED_PROGRAMS:
        _validate_argv_parts(parts)
        return parts
    if program.startswith("python") and tuple(parts[:3]) in _ALLOWED_PYTHON_MODULE_COMMANDS:
        _validate_argv_parts(parts)
        return parts
    raise ValueError(f"command_not_allowed:{program}")


def execute_command(command: str, *, cwd: Path | None, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # command validated by validate_command() against whitelist + shell-metachar block
        validate_command(command),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
