from __future__ import annotations

"""Port for Pytdx market data access."""

from typing import Any, Protocol


class PytdxMarketPort(Protocol):
    """Application-facing Pytdx access without importing pytdx infrastructure modules."""

    def is_available(self) -> bool:
        ...

    def require_available(self) -> None:
        ...

    def status(self) -> dict[str, Any]:
        ...

    def catalog(self) -> dict[str, Any]:
        ...

    def get_security_quotes_for_symbols(self, symbols: list[str]) -> list[dict[str, Any]]:
        ...

    def invoke(
        self,
        module: str,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        ...

    def finance_call(self, method: str, **kwargs: Any) -> Any:
        ...
