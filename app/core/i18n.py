from __future__ import annotations

"""Internationalization (i18n) support for quant-atlas.

加载 locales/{locale}.json 翻译文件，提供 t() 函数用于模板。
支持 Jinja2 全局函数和 JavaScript 端点调用。
"""

import json
from pathlib import Path
from typing import Any

DEFAULT_LOCALE = "zh"
SUPPORTED_LOCALES = ["zh", "en"]


class I18n:
    """Internationalization loader with caching."""

    def __init__(self, locale: str = DEFAULT_LOCALE):
        self.locale = locale
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        base_dir = Path(__file__).parent.parent.parent
        locales_dir = base_dir / "locales"
        json_path = locales_dir / f"{self.locale}.json"

        if json_path.exists():
            try:
                raw = json_path.read_text(encoding="utf-8")
                # Git LFS pointer left undownloaded — treat as missing.
                if raw.lstrip().startswith("version https://git-lfs.github.com/"):
                    raise ValueError("locale file is a git-lfs pointer")
                self._data = json.loads(raw)
            except (OSError, ValueError, json.JSONDecodeError):
                self._data = {}
                if self.locale != DEFAULT_LOCALE:
                    fallback = I18n(DEFAULT_LOCALE)
                    self._data = fallback._data
        elif self.locale != DEFAULT_LOCALE:
            fallback = I18n(DEFAULT_LOCALE)
            self._data = fallback._data

    def get(self, key: str, default: str | None = None) -> Any:
        """Get translation by dot-separated key."""
        parts = key.split(".")
        val = self._data
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                return default if default is not None else key
        return val if val is not None else (default if default is not None else key)

    def all(self) -> dict[str, Any]:
        """Get all translations."""
        return self._data


_loaded: dict[str, I18n] = {}


def get_i18n(locale: str = DEFAULT_LOCALE) -> I18n:
    """Get or create I18n instance for locale."""
    if locale not in _loaded:
        _loaded[locale] = I18n(locale)
    return _loaded[locale]


def t(key: str, default: str | None = None, **kwargs: Any) -> str:
    """Translate a key with optional formatting.

    Usage:
        t('nav.home') -> "首页"
        t('common.welcome', name="User") -> "欢迎 User"
    """
    i18n = get_i18n()
    result = i18n.get(key)

    if result is key and default is None:
        return key

    if isinstance(result, str) and kwargs:
        try:
            return result.format(**kwargs)
        except (KeyError, ValueError):
            return result
    return str(result) if result else f"[{key}]"


def set_locale(locale: str) -> None:
    """Set current locale (for session-based switching)."""
    if locale not in SUPPORTED_LOCALES:
        locale = DEFAULT_LOCALE
    global _current_locale
    _current_locale = locale


_current_locale = DEFAULT_LOCALE


def get_current_locale() -> str:
    """Get current locale."""
    return _current_locale


def get_available_locales() -> list[str]:
    """Get list of available locales."""
    return SUPPORTED_LOCALES.copy()


def get_all_translations() -> dict[str, Any]:
    """Get all translations for current locale."""
    return get_i18n(_current_locale).all()


def create_jinja2_env(locale: str = DEFAULT_LOCALE):
    """Create Jinja2 environment with t() function."""
    from jinja2 import DictLoader, Environment

    i18n = get_i18n(locale)

    def translate(key: str, default: str | None = None, **kwargs: Any) -> str:
        return t(key, default, **kwargs)

    env = Environment(loader=DictLoader({"index.html": ""}))
    env.globals["t"] = translate
    env.globals["i18n"] = i18n.all()
    return env
