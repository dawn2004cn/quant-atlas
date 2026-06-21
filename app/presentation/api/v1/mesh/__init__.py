"""Federated mesh API sub-package."""

from app.presentation.api.v1.mesh.gateway_routes import register_mesh_gateway_routes
from app.presentation.api.v1.mesh.perception_routes import register_mesh_perception_routes
from app.presentation.api.v1.mesh.runtime import MeshRuntime

__all__ = [
    "MeshRuntime",
    "register_mesh_gateway_routes",
    "register_mesh_perception_routes",
]
