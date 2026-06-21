"""Architecture gates for Phase F — optional dependency extras."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dependency_drift_script_passes():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_dependency_drift.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_pyproject_declares_compute_and_qlib_extras():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    optional = data.get("project", {}).get("optional-dependencies", {})
    assert "compute" in optional
    assert "qlib" in optional
    compute_keys = {line.split(">=")[0].split(";")[0].strip().lower() for line in optional["compute"]}
    qlib_keys = {line.split(">=")[0].strip().lower() for line in optional["qlib"]}
    assert "polars" in compute_keys
    assert "vectorbt" in compute_keys
    assert "pyqlib" in qlib_keys


def test_package_lock_is_authoritative_npm_lock():
    assert (ROOT / "package-lock.json").is_file()
    assert not (ROOT / "bun.lock").is_file()
    assert not (ROOT / "bun.lockb").is_file()
