from __future__ import annotations

"""Controlled VCS checkout for strategy snapshot rollback."""

import logging
import re
import subprocess
from pathlib import Path

from app.bootstrap_components.runtime_config_validator import resolve_deploy_profile
from app.core.runtime_config import get_runtime_bool

logger = logging.getLogger(__name__)

# Strict revision whitelist: hex SHA (7-40 chars) or refs/heads/* branch paths.
_GIT_REVISION_RE = re.compile(r"^[a-f0-9]{7,40}$|^refs/heads/[a-zA-Z0-9/_-]+$")
_SVN_REVISION_RE = re.compile(r"^\d+$")


def is_code_checkout_allowed() -> bool:
    """Gate mutating checkout: explicit env + block prod unless force flag."""
    if not get_runtime_bool("STRATEGY_SNAPSHOT_ALLOW_CODE_CHECKOUT", False):
        return False
    profile = resolve_deploy_profile()
    if profile in ("prod", "production", "trading"):
        return get_runtime_bool("STRATEGY_SNAPSHOT_FORCE_CODE_CHECKOUT", False)
    return True


def _validate_git_revision(revision: str) -> None:
    """Raise ValueError if the revision looks unsafe for ``git checkout``."""
    if not _GIT_REVISION_RE.match(revision):
        raise ValueError(
            f"invalid_revision: {revision!r} "
            "(expected git SHA or refs/heads/*)"
        )


def _validate_svn_revision(revision: str) -> None:
    """Raise ValueError if the revision looks unsafe for ``svn update -r``."""
    if not _SVN_REVISION_RE.match(revision):
        raise ValueError(
            f"invalid_revision: {revision!r} "
            "(expected numeric SVN revision)"
        )


def checkout_code_revision(repo_root: Path, code_revision: dict[str, str]) -> tuple[bool, str]:
    """Checkout git/svn revision; never raises."""
    if not is_code_checkout_allowed():
        return False, "code_checkout_not_allowed"

    vcs = str(code_revision.get("vcs") or "")
    revision = str(code_revision.get("revision") or "")
    if not vcs or revision in {"", "unknown"}:
        return False, "unknown_revision"

    # --- Revision validation (prevents command injection) ---
    if vcs == "git":
        try:
            _validate_git_revision(revision)
        except ValueError as exc:
            return False, str(exc)[:300]
    elif vcs == "svn":
        try:
            _validate_svn_revision(revision)
        except ValueError as exc:
            return False, str(exc)[:300]

    root = Path(repo_root)
    if vcs == "git":
        cmd = ["git", "-C", str(root), "checkout", revision]
    elif vcs == "svn":
        cmd = ["svn", "update", "-r", revision, str(root)]
    else:
        return False, f"unsupported_vcs:{vcs}"

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)  # revision validated by _validate_git_revision / _validate_svn_revision before reaching this point
        if proc.returncode == 0:
            return True, revision
        detail = (proc.stderr or proc.stdout or "checkout_failed")[:300]
        logger.warning("checkout_code_revision failed: %s", detail)
        return False, detail
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("checkout_code_revision error: %s", exc)
        return False, str(exc)[:300]
