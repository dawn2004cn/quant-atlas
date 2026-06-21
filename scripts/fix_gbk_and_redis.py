"""Fix GBK encoding corruption in quote_aggregator.py and re-apply Redis migration."""
from __future__ import annotations

import re

files = {
    "app/infrastructure/realtime/quote_aggregator.py": {
        "fixes": [
            ("  EALTIME = \"realtime\"", "    REALTIME = \"realtime\""),
            ("    PUS \"push\"", "    PUSH = \"push\""),
            ("    POLL poll\"", "    POLL = \"poll\""),
        ],
        "gbk": False,
    },
    "app/infrastructure/realtime/market_stream.py": {
        "fixes": [],
        "gbk": False,
    },
    "app/infrastructure/execution/driver/redis_executor.py": {
        "fixes": [],
        "gbk": True,
    },
    "app/infrastructure/tracing.py": {
        "fixes": [],
        "gbk": True,
    },
    "app/domain/trading/order_persistence.py": {
        "fixes": [],
        "gbk": True,
    },
}

for path, opts in files.items():
    with open(path, "rb") as fh:
        raw = fh.read()

    if opts["gbk"]:
        content = raw.decode("gbk", errors="replace")
    else:
        content = raw.decode("utf-8", errors="replace")

    # Apply targeted fixes
    for old, new in opts["fixes"]:
        content = content.replace(old, new)

    # Replace redis.from_url calls
    content = re.sub(
        r"redis\.from_url\(([^,]+),\s*decode_responses=True\)",
        r"RedisClientPool.get(\1).client",
        content,
    )
    content = re.sub(
        r"return redis\.from_url\(([^)]+)\)",
        r"return RedisClientPool.get(\1).binary_client",
        content,
    )

    # Add import if missing
    if "RedisClientPool" in content and "from app.infrastructure.redis_client" not in content:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("from app.core") or line.startswith("from app.infrastructure"):
                lines.insert(i, "from app.infrastructure.redis_client import RedisClientPool")
                break
        content = "\n".join(lines)

    # Write as UTF-8
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"Fixed: {path}")

# Verify all compile
import py_compile
for path in files:
    try:
        py_compile.compile(path, doraise=True)
        print(f"  Compile OK: {path}")
    except py_compile.PyCompileError as e:
        print(f"  Compile FAIL: {path}: {e}")