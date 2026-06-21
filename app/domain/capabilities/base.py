from __future__ import annotations
"""Base capability interface for the plugin registry."""


from abc import ABC, abstractmethod
from typing import Any


class BaseCapability(ABC):
    """Abstract interface for a self-registering tool capability.

    Every capability must define:
    - ``capability_name`` – a unique identifier string.
    - ``execute(**kwargs)`` – the core invocation, returning ``(result, evidence_note)``.
    - ``to_tool_spec()`` – an OpenAI-compatible tool schema for agent consumption.
    """

    @property
    @abstractmethod
    def capability_name(self) -> str:
        """Unique name for this capability (e.g. 'fetch_bars')."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, **kwargs: Any) -> tuple[Any, str]:
        """Execute the capability.

        Returns:
            A tuple of ``(result, evidence_note)`` where *result* is the
            capability-specific payload and *note* is a human-readable
            evidence string.
        """
        raise NotImplementedError

    def to_tool_spec(self) -> dict[str, Any]:
        return {
            "name": self.capability_name,
            "description": (self.__doc__ or "").strip(),
        }
