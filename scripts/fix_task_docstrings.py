"""Fix docstrings accidentally truncated to two closing quotes."""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1] / "app" / "tasks"
PAT = re.compile(r'^(\s*)"""(.+?)""\s*$')


def main() -> None:
    for path in sorted(ROOT.rglob("*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        changed = False
        out: list[str] = []
        for line in lines:
            m = PAT.match(line)
            if m and not line.rstrip().endswith('"""'):
                indent, body = m.group(1), m.group(2)
                out.append(f'{indent}"""{body}"""')
                changed = True
            else:
                out.append(line)
        if changed:
            path.write_text("\n".join(out) + "\n", encoding="utf-8")
            print("fixed", path.name)


if __name__ == "__main__":
    main()
