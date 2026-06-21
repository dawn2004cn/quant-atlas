from __future__ import annotations
"""非敏感运行时配置：优先读 ``config/config.cfg``，环境变量非空时覆盖文件。

密钥、数据库 URI、Webhook 等仍仅从环境变量读取（不参与 cfg 回退）。
"""


import configparser
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CFG_PATH = _REPO_ROOT / "config" / "config.cfg"
_SECRET_CFG_PATH = _REPO_ROOT / "config" / "secret.cfg"
_DOTENV_PATH = _REPO_ROOT / ".env"
_SECTION = "app"
_SECRET_CFG_KEYS_LOADED: set[str] = set()

# 仅允许从环境变量读取（可能含密钥或带密码的连接串）
_ENV_ONLY_KEYS: frozenset[str] = frozenset(
    {
        "FLASK_SECRET_KEY",
        "QUANT_DATABASE_URI",
        "WECHAT_OPEN_APP_SECRET",
        "OPENAI_API_KEY",
        "LANGGRAPH_POSTGRES_URI",
        "DATABASE_URL",
        "RDAGENT_WEBHOOK_URL",
    }
)

_parser: configparser.ConfigParser | None = None
_loaded: bool = False


def _load_env_file(path: Path, *, track_secret_keys: bool = False) -> None:
    """Load KEY=value lines into ``os.environ``.

    Does not override non-empty values already in the process environment.
    Empty placeholders (e.g. ``MYSQL_PASSWORD=`` from ``.env``) may be filled
    by a later file such as ``config/secret.cfg``.
    """
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw in lines:
        s = (raw or "").strip()
        if not s or s.startswith("#") or s.startswith("["):
            continue
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        key = (k or "").strip()
        if not key:
            continue
        val = (v or "").strip()
        if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
            val = val[1:-1]
        if not str(val).strip():
            continue
        if track_secret_keys:
            _SECRET_CFG_KEYS_LOADED.add(key)
        existing = os.environ.get(key)
        if existing is not None and str(existing).strip():
            continue
        os.environ[key] = val


def _load_secret_cfg_if_present() -> None:
    """Load local private secrets from ``config/secret.cfg`` before ``.env``."""
    _load_env_file(_SECRET_CFG_PATH, track_secret_keys=True)


def _load_dotenv_if_present() -> None:
    """Load local ``config/secret.cfg`` first, then repository ``.env``.

    Both files only populate missing environment variables and never override
    values already provided by the process environment.
    """
    _load_secret_cfg_if_present()
    _load_env_file(_DOTENV_PATH)


def _ensure_loaded() -> None:
    global _parser, _loaded
    if _loaded:
        return
    _loaded = True
    # 优先加载本地私有 secret.cfg，再加载 .env；两者都不覆盖已有环境变量。
    _load_dotenv_if_present()
    p = configparser.ConfigParser()
    p.optionxform = str
    if _CFG_PATH.is_file():
        try:
            p.read(_CFG_PATH, encoding="utf-8")
        except OSError:
            p = configparser.ConfigParser()
            p.optionxform = str
    _parser = p


def secret_cfg_loaded_keys() -> frozenset[str]:
    """Return env keys populated from the local private ``config/secret.cfg``."""
    return frozenset(_SECRET_CFG_KEYS_LOADED)


def get_runtime(key: str, default: str = "") -> str:
    """非敏感键：``os.environ`` 非空优先，否则 ``[app]`` 段同名项，否则 ``default``。"""
    if key in _ENV_ONLY_KEYS:
        return (os.getenv(key) or default).strip()
    ev = os.getenv(key)
    if ev is not None and str(ev).strip() != "":
        return str(ev).strip()
    _ensure_loaded()
    # .env is loaded inside _ensure_loaded; re-read env before config.cfg fallback.
    ev = os.getenv(key)
    if ev is not None and str(ev).strip() != "":
        return str(ev).strip()
    if _parser is not None and _parser.has_option(_SECTION, key):
        return _parser.get(_SECTION, key, fallback=default).strip()
    return default


def resolved_redis_url(default: str = "") -> str:
    """Resolve a Redis URL from REDIS_URL and known Celery/Mesh fallbacks."""
    for env_key in (
        "REDIS_URL",
        "TASK_MESSAGE_REDIS_URL",
        "MESH_REDIS_URL",
        "CELERY_BROKER_URL",
    ):
        value = get_runtime(env_key, "")
        if value.strip():
            return value.strip()
    return default


def get_runtime_bool(key: str, default: bool = False) -> bool:
    raw = get_runtime(key, "1" if default else "0")
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def get_runtime_int(key: str, default: int) -> int:
    raw = get_runtime(key, str(default))
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


def get_runtime_float(key: str, default: float) -> float:
    raw = get_runtime(key, str(default))
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return default
