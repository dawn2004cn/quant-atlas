from __future__ import annotations

"""Resolve repository code revision for deploy snapshots (Git / SVN / unknown)."""

import subprocess
from pathlib import Path


def resolve_code_revision(repo_root: Path) -> dict[str, str]:
    """Best-effort VCS revision; never raises."""
    root = Path(repo_root)
    for vcs, cmd in (
        ("git", ["git", "-C", str(root), "rev-parse", "HEAD"]),
        ("svn", ["svn", "info", "--show-item", "revision", str(root)]),
    ):
        try:
            proc = subprocess.run(  # cmd is fully hardcoded (git/svn with repo_root path)
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            revision = (proc.stdout or "").strip()
            if proc.returncode == 0 and revision:
                return {"vcs": vcs, "revision": revision, "dirty": "unknown"}
        except (OSError, subprocess.SubprocessError):
            continue
    return {"vcs": "unknown", "revision": "unknown", "dirty": "unknown"}
