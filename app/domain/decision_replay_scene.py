from __future__ import annotations

"""3D decision replay scene descriptors (Quant Atlas 8.0 P2)."""

from typing import Any

from pydantic import BaseModel, Field


class SceneNode(BaseModel):
    id: str
    type: str
    label: str = ""
    color: str = "#6366f1"
    size: float = Field(default=0.4, ge=0.1, le=3.0)
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    meta: dict[str, Any] = Field(default_factory=dict)


class SceneEdge(BaseModel):
    from_id: str
    to_id: str
    relation: str = "linked"
    color: str = "#94a3b8"
    meta: dict[str, Any] = Field(default_factory=dict)


class DecisionReplayScene(BaseModel):
    schema_version: str = "v1"
    subject: str = ""
    symbol: str | None = None
    market: str = "CN"
    nodes: list[SceneNode] = Field(default_factory=list)
    edges: list[SceneEdge] = Field(default_factory=list)
    camera: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 8, "z": 18})
    bounds: dict[str, float] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


__all__ = ["SceneNode", "SceneEdge", "DecisionReplayScene"]
