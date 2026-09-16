from schema import Task, WorkflowGraph


ALGORITHM_SENSITIVE_TYPES = {"backend", "database", "ml"}
ALGORITHM_HINTS = (
    "algorithm",
    "search",
    "recommend",
    "recommendation",
    "ranking",
    "sort",
    "matching",
    "prediction",
    "forecast",
    "classification",
    "model",
)


def tasks_needing_algorithm_decision(graph: WorkflowGraph) -> list[Task]:
    """Select tasks where an algorithm choice materially affects implementation."""
    selected = []
    for task in graph.tasks:
        text = f"{task.name} {task.description}".lower()
        if task.type == "ml" or task.type in ALGORITHM_SENSITIVE_TYPES and any(
            hint in text for hint in ALGORITHM_HINTS
        ):
            selected.append(task)
    return selected
