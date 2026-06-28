from __future__ import annotations

"""Infrastructure adapter for ``PytdxMarketPort``."""

from typing import Any

from app.domain.ports.pytdx_port import PytdxMarketPort
from app.infrastructure.pytdx.facade import get_pytdx_facade
from app.infrastructure.pytdx.runtime import pytdx_available, require_pytdx


class PytdxMarketPortAdapter(PytdxMarketPort):
    """Delegates to ``PytdxFacade`` and runtime guards."""

    def is_available(self) -> bool:
        return pytdx_available()

    def require_available(self) -> None:
        require_pytdx()

    def status(self) -> dict[str, Any]:
        data = get_pytdx_facade().status()
        return data if isinstance(data, dict) else {"available": self.is_available()}

    def catalog(self) -> dict[str, Any]:
        data = get_pytdx_facade().catalog()
        return data if isinstance(data, dict) else {}

    def get_security_quotes_for_symbols(self, symbols: list[str]) -> list[dict[str, Any]]:
        rows = get_pytdx_facade().hq.get_security_quotes_for_symbols(symbols)
        return rows if isinstance(rows, list) else []

    def invoke(
        self,
        module: str,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return get_pytdx_facade().invoke(module, method, *args, **kwargs)

    def finance_call(self, method: str, **kwargs: Any) -> Any:
        return get_pytdx_facade().finance.call(method, **kwargs)
