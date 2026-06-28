from __future__ import annotations

"""Pytdx 模块调用基类。"""


from typing import Any

from app.infrastructure.pytdx.catalog import PytdxModule, allowed_methods
from app.infrastructure.pytdx.exceptions import PytdxMethodNotAllowedError
from app.infrastructure.pytdx.serialize import to_jsonable


class BasePytdxApi:
    module: PytdxModule

    def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        name = (method or "").strip()
        if name not in allowed_methods(self.module):
            raise PytdxMethodNotAllowedError(f"{self.module}.{name} not allowed")
        # 支持 call("m", [], {"symbol": "600519"}) 误传时展开
        if (
            len(args) == 1
            and isinstance(args[0], dict)
            and not kwargs
            and not any(isinstance(a, (list, tuple)) for a in args)
        ):
            kwargs = dict(args[0])
            args = ()
        raw = self._dispatch(name, *args, **kwargs)
        return to_jsonable(raw)

    def _dispatch(self, method: str, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError
