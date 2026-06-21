"""Bootstrap types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ApiBundle:
    """API bundle containing services, providers, and repositories."""
    services: Any
    providers: Any
    repositories: Any


@dataclass
class AppBundle:
    """Main application bundle."""
    services: Any
    providers: Any
    repositories: Any
    settings: Any