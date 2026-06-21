from app.domain.workflow_hub.ports import WorkflowRepository
from app.infrastructure.workflow_hub.memory_repository import InMemoryWorkflowRepository

_default_repo: WorkflowRepository | None = None


def get_workflow_repository() -> WorkflowRepository:
    global _default_repo
    if _default_repo is None:
        _default_repo = InMemoryWorkflowRepository()
    return _default_repo


def set_workflow_repository(repo: WorkflowRepository) -> None:
    global _default_repo
    _default_repo = repo
