"""Backward-compatible alias for ``UserKnowledgeService`` (replaces hardcoded stub)."""

from __future__ import annotations

from app.modules.user.services.user.user_knowledge_service import UserKnowledgeService

ConcreteUserKnowledgeService = UserKnowledgeService

__all__ = ["ConcreteUserKnowledgeService", "UserKnowledgeService"]
