from __future__ import annotations

import pytest

from app.infrastructure.agent.swarm.tools.command_safety import execute_command, validate_command


def test_validate_command_rejects_python_code_execution():
    with pytest.raises(ValueError):
        validate_command("python -c 'print(1)'")


def test_validate_command_rejects_path_traversal_in_args():
    with pytest.raises(ValueError, match="path_traversal_not_allowed"):
        validate_command("python -m pytest ../../etc/passwd")


def test_validate_command_rejects_python_command_flag():
    with pytest.raises(ValueError, match="python_c_execution_not_allowed"):
        validate_command("python --command print")


def test_validate_command_allows_approved_python_module_command():
    assert validate_command("python -m pytest tests/domain -q") == [
        "python",
        "-m",
        "pytest",
        "tests/domain",
        "-q",
    ]


def test_validate_command_rejects_shell_metacharacters():
    with pytest.raises(ValueError, match="shell_metacharacters_not_allowed"):
        validate_command("python -c 'print(1); rm -rf /'")


def test_validate_command_rejects_unapproved_python_module():
    with pytest.raises(ValueError, match="command_not_allowed:python"):
        validate_command("python -m os")


def test_validate_command_rejects_disallowed_program():
    with pytest.raises(ValueError, match="command_not_allowed:curl"):
        validate_command("curl https://example.com")


def test_execute_command_passes_argv_without_shell(monkeypatch, tmp_path):
    calls = []

    class Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    result = execute_command("python -m pytest --version", cwd=tmp_path, timeout=120)

    assert result.stdout == "ok"
    assert calls[0][0] == ["python", "-m", "pytest", "--version"]
    assert "shell" not in calls[0][1]
    assert calls[0][1]["cwd"] == str(tmp_path)
