"""OpenAPI spec consistency tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_openapi_json_can_be_generated():
    """generate_openapi.py should produce valid JSON."""
    output = REPO_ROOT / "docs" / "openapi.json"
    result = subprocess.run(
        [sys.executable, "scripts/generate_openapi.py", "--output", str(output)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
    )
    assert result.returncode == 0, f"generate_openapi.py failed: {result.stderr}"
    assert output.exists(), "openapi.json not created"
    spec = json.loads(output.read_text())
    assert "openapi" in spec
    assert spec["openapi"].startswith("3.")


def test_openapi_has_info():
    """Spec must have title and version."""
    spec_path = REPO_ROOT / "docs" / "openapi.json"
    if not spec_path.exists():
        return
    spec = json.loads(spec_path.read_text())
    assert spec.get("info", {}).get("title"), "Missing info.title"
    assert spec.get("info", {}).get("version"), "Missing info.version"
