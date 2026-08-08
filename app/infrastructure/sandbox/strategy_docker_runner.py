"""Strategy code sandbox runner (process | docker)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.core.logger import get_logger

logger = get_logger(__name__)

SandboxMode = Literal["process", "docker"]


class StrategySandboxError(RuntimeError):
    """Sandbox misconfiguration or execution failure."""


@dataclass(frozen=True, slots=True)
class SandboxRunResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    mode: SandboxMode


def resolve_sandbox_mode(raw: str | None = None) -> SandboxMode:
    value = (raw if raw is not None else os.getenv("STRATEGY_SANDBOX", "process")).strip().lower()
    if value not in ("process", "docker"):
        raise StrategySandboxError(f"invalid_STRATEGY_SANDBOX:{value}")
    return value  # type: ignore[return-value]


class StrategyDockerRunner:
    """Run a Python entry script inside Docker with no network and tight limits.

    When ``STRATEGY_SANDBOX=docker`` and Docker is unavailable, raises
    ``StrategySandboxError`` — never silently falls back to process.
    """

    def __init__(
        self,
        *,
        image: str | None = None,
        timeout_sec: int = 120,
        memory: str = "512m",
        cpus: str = "1",
    ) -> None:
        self._image = image or os.getenv("STRATEGY_SANDBOX_IMAGE", "python:3.12-slim")
        self._timeout_sec = timeout_sec
        self._memory = memory
        self._cpus = cpus

    def available(self) -> bool:
        return shutil.which("docker") is not None

    def run(self, entry_script: Path, *, workdir: Path | None = None) -> SandboxRunResult:
        if not self.available():
            raise StrategySandboxError("docker_unavailable")
        script = entry_script.resolve()
        if not script.is_file():
            raise StrategySandboxError(f"entry_missing:{script}")
        cwd = (workdir or script.parent).resolve()
        cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            self._memory,
            "--cpus",
            self._cpus,
            "-v",
            f"{cwd}:/work:ro",
            "-w",
            "/work",
            self._image,
            "python",
            script.name,
        ]
        try:
            completed = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise StrategySandboxError(f"docker_timeout:{self._timeout_sec}") from exc
        return SandboxRunResult(
            success=completed.returncode == 0,
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            mode="docker",
        )


def run_strategy_sandboxed(entry_script: Path, *, workdir: Path | None = None) -> SandboxRunResult:
    """Dispatch by ``STRATEGY_SANDBOX`` env (default process via subprocess)."""
    mode = resolve_sandbox_mode()
    if mode == "docker":
        return StrategyDockerRunner().run(entry_script, workdir=workdir)
    script = entry_script.resolve()
    if not script.is_file():
        raise StrategySandboxError(f"entry_missing:{script}")
    cwd = (workdir or script.parent).resolve()
    completed = subprocess.run(  # noqa: S603
        [sys.executable, str(script)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=int(os.getenv("STRATEGY_SANDBOX_TIMEOUT", "120")),
        check=False,
    )
    return SandboxRunResult(
        success=completed.returncode == 0,
        exit_code=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        mode="process",
    )
