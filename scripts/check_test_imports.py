"""Import all test modules and report collection errors."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

errors: list[tuple[str, str, str]] = []
files = sorted(root.joinpath("tests").rglob("test_*.py"))
for path in files:
    mod = path.with_suffix("").relative_to(root).as_posix().replace("/", ".")
    try:
        spec = importlib.util.spec_from_file_location(mod, path)
        if spec is None or spec.loader is None:
            errors.append((str(path), "SpecError", "could not build module spec"))
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except BaseException as exc:  # noqa: BLE001 — diagnostic script; includes pytest.skip
        if type(exc).__name__ in {"Skipped", "KeyboardInterrupt", "SystemExit"}:
            continue
        errors.append((str(path.relative_to(root)), type(exc).__name__, str(exc)[:300]))

lines = [f"checked {len(files)} files, errors={len(errors)}"]
for path, exc_type, msg in errors:
    lines.append(f"{path}: {exc_type}: {msg}")
out_path = root / "scripts" / "test_import_errors.txt"
out_path.write_text("\n".join(lines), encoding="utf-8")
