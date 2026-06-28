from __future__ import annotations
"""API Documentation.

OpenAPI/Swagger documentation for API endpoints.
"""


from dataclasses import dataclass


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class APIEndpoint:
    """API endpoint documentation."""
    path: str
    method: str
    summary: str
    description: str = ""
    tags: list[str] = None
    parameters: list[dict] = None
    request_body: dict | None = None
    responses: dict = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.parameters is None:
            self.parameters = []
        if self.responses is None:
            self.responses = {}


class APIDocumentation:
    """API documentation generator."""

    def __init__(self, title: str = "Quant Atlas API", version: str = "1.0.0"):
        self._title = title
        self._version = version
        self._endpoints: list[APIEndpoint] = []
        self._servers: list[dict] = []
        logger.info(f"APIDocumentation initialized: {title} v{version}")

    def add_endpoint(self, endpoint: APIEndpoint) -> None:
        """Add endpoint to documentation."""
        self._endpoints.append(endpoint)

    def add_server(self, url: str, description: str = "") -> None:
        """Add server."""
        self._servers.append({"url": url, "description": description})

    def generate_openapi(self) -> dict:
        """Generate OpenAPI 3.0 specification."""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": self._title,
                "version": self._version,
                "description": "Quant Atlas Trading API"
            },
            "servers": self._servers,
            "paths": self._generate_paths(),
            "components": {
                "schemas": self._generate_schemas()
            },
            "tags": self._generate_tags()
        }
        return spec

    def _generate_paths(self) -> dict:
        """Generate paths section."""
        paths = {}
        for ep in self._endpoints:
            if ep.path not in paths:
                paths[ep.path] = {}

            paths[ep.path][ep.method.lower()] = {
                "summary": ep.summary,
                "description": ep.description,
                "tags": ep.tags,
                "parameters": ep.parameters,
                "requestBody": ep.request_body,
                "responses": ep.responses
            }
        return paths

    def _generate_schemas(self) -> dict:
        """Generate schema definitions."""
        return {
            "Error": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "message": {"type": "string"}
                        }
                    }
                }
            },
            "Stock": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "name": {"type": "string"},
                    "price": {"type": "number"}
                }
            }
        }

    def _generate_tags(self) -> list:
        """Generate tags."""
        tags_set = set()
        for ep in self._endpoints:
            tags_set.update(ep.tags)
        return [{"name": tag} for tag in sorted(tags_set)]

    def get_swagger_ui_config(self) -> dict:
        """Get Swagger UI configuration."""
        return {
            "swagger": "2.0",
            "info": {
                "title": self._title,
                "version": self._version
            },
            "paths": self._generate_paths()
        }


# Default documented endpoints
DEFAULT_ENDPOINTS = [
    APIEndpoint(
        path="/api/v1/stocks",
        method="GET",
        summary="List stocks",
        description="Get list of all stocks",
        tags=["stocks"]
    ),
    APIEndpoint(
        path="/api/v1/stocks/{code}",
        method="GET",
        summary="Get stock",
        description="Get stock by code",
        tags=["stocks"]
    ),
    APIEndpoint(
        path="/api/v1/screening",
        method="POST",
        summary="Screen stocks",
        description="Screen stocks with filters",
        tags=["screening"]
    ),
    APIEndpoint(
        path="/api/v1/signals",
        method="GET",
        summary="Get signals",
        description="Get trading signals",
        tags=["signals"]
    ),
    APIEndpoint(
        path="/api/v1/portfolio",
        method="GET",
        summary="Get portfolio",
        description="Get portfolio positions",
        tags=["portfolio"]
    ),
    APIEndpoint(
        path="/api/health",
        method="GET",
        summary="Health check",
        description="Check API health",
        tags=["health"]
    ),
]


def create_api_documentation() -> APIDocumentation:
    """Create default API documentation."""
    doc = APIDocumentation()
    doc.add_server("http://localhost:5000", "Local development")

    for endpoint in DEFAULT_ENDPOINTS:
        doc.add_endpoint(endpoint)

    return doc


# Global instance
_api_documentation: APIDocumentation | None = None


def get_api_documentation() -> APIDocumentation:
    """Get global API documentation."""
    global _api_documentation
    if _api_documentation is None:
        _api_documentation = create_api_documentation()
    return _api_documentation


__all__ = [
    "APIEndpoint",
    "APIDocumentation",
    "create_api_documentation",
    "get_api_documentation",
]
