"""One-off repair: remove U+FFFD from task modules after botched bulk replace."""
from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "app" / "tasks"


def main() -> None:
    for path in sorted(ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "\ufffd" not in text:
            continue
        cleaned = text.replace("\ufffd?", "").replace("\ufffd", "")
        path.write_text(cleaned, encoding="utf-8")
        try:
            ast.parse(cleaned)
            print("ok", path.name)
        except SyntaxError as exc:
            print("still bad", path.name, exc.lineno, exc.msg)


if __name__ == "__main__":
    main()
