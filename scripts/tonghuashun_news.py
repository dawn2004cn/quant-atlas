"""
同花顺股道新闻 CLI（已迁入 ``app.cli``）。

推荐：自仓库根目录执行::

    python -m app.cli portal-10jqka [--out-dir DIR] [--limit N]

本文件保留为兼容入口。
"""

from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


if __name__ == "__main__":
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from app.cli.main import main

    sys.exit(main(["portal-10jqka", *sys.argv[1:]]))
