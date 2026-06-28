from app.domain.workflow_hub.models import WorkflowInstance
from app.domain.workflow_hub.ports import WorkflowEngine


class DefaultWorkflowEngine(WorkflowEngine):
    def start(self, wf_type: str, params: dict[str, object], user_id: int | None) -> WorkflowInstance:
        raise NotImplementedError

    def resume(self, workflow_id: str, action: str, payload: dict[str, object] | None = None) -> WorkflowInstance:
        raise NotImplementedError


def get_default_workflow_engine() -> WorkflowEngine:
    return DefaultWorkflowEngine()
