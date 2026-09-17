from schema import WorkflowGraph
from workflow_ensemble import understand_workflow_ensemble


def understand_workflow(requirement: str) -> WorkflowGraph:
    return understand_workflow_ensemble(requirement)