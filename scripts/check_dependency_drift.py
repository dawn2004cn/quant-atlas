from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"
PYPROJECT = ROOT / "pyproject.toml"
OPTIONAL_REQUIREMENTS: dict[str, Path] = {
    "compute": ROOT / "requirements-compute.txt",
    "qlib": ROOT / "requirements-qlib.txt",
}
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+")


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_key(requirement: str) -> str:
    match = NAME_RE.match(requirement.strip())
    if not match:
        raise ValueError(f"invalid requirement: {requirement}")
    return normalize_name(match.group(0))


def canonical_requirement(requirement: str) -> str:
    return requirement.replace(" ", "")


def parse_requirements(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        values[requirement_key(line)] = canonical_requirement(line)
    return values


def load_pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def parse_pyproject_main(path: Path | None = None) -> dict[str, str]:
    data = load_pyproject() if path is None else tomllib.loads(path.read_text(encoding="utf-8"))
    dependencies = data.get("project", {}).get("dependencies", [])
    if not dependencies:
        raise RuntimeError("pyproject.toml has no project.dependencies")
    return {requirement_key(dep): canonical_requirement(dep) for dep in dependencies}


def parse_pyproject_extras() -> dict[str, dict[str, str]]:
    optional = load_pyproject().get("project", {}).get("optional-dependencies", {})
    extras: dict[str, dict[str, str]] = {}
    for name, deps in optional.items():
        if name == "test":
            continue
        extras[name] = {requirement_key(dep): canonical_requirement(dep) for dep in deps}
    return extras


def diff(left: dict[str, str], right: dict[str, str], *, left_label: str, right_label: str) -> list[str]:
    lines: list[str] = []
    for key in sorted(set(left) ^ set(right)):
        if key in left:
            lines.append(f"only in {left_label}: {left[key]}")
        else:
            lines.append(f"only in {right_label}: {right[key]}")
    for key in sorted(set(left) & set(right)):
        if left[key] != right[key]:
            lines.append(
                f"mismatch for {key}: {left_label}={left[key]} {right_label}={right[key]}"
            )
    return lines


def check_main_manifests() -> list[str]:
    requirements = parse_requirements(REQUIREMENTS)
    pyproject = parse_pyproject_main()
    return diff(requirements, pyproject, left_label="requirements.txt", right_label="pyproject.toml")


def check_optional_extras() -> list[str]:
    issues: list[str] = []
    extras = parse_pyproject_extras()
    main_keys = set(parse_pyproject_main())

    for extra_name, req_path in OPTIONAL_REQUIREMENTS.items():
        if extra_name not in extras:
            issues.append(f"missing optional-dependencies.{extra_name} in pyproject.toml")
            continue
        if not req_path.is_file():
            issues.append(f"missing requirements file for extra [{extra_name}]: {req_path.name}")
            continue

        file_deps = parse_requirements(req_path)
        extra_deps = extras[extra_name]

        # Legacy convenience lines (e.g. rdagent duplicated in main deps) are ignored.
        filtered_file = {
            key: value for key, value in file_deps.items() if key not in main_keys or key in extra_deps
        }

        issues.extend(
            diff(
                extra_deps,
                filtered_file,
                left_label=f"pyproject.toml [{extra_name}]",
                right_label=req_path.name,
            )
        )

    for extra_name in extras:
        if extra_name not in OPTIONAL_REQUIREMENTS:
            issues.append(
                f"optional extra [{extra_name}] has no requirements-*.txt mapping in check script"
            )

    return issues


def main() -> int:
    differences = check_main_manifests() + check_optional_extras()
    if differences:
        print("Dependency drift detected:", file=sys.stderr)
        for line in differences:
            print(f"- {line}", file=sys.stderr)
        return 1

    main_count = len(parse_requirements(REQUIREMENTS))
    extra_count = sum(len(v) for v in parse_pyproject_extras().values())
    print(
        f"Dependency manifests are aligned: {main_count} runtime + {extra_count} optional dependencies"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
