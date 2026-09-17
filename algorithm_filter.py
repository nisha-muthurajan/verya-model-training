from schema import Task, WorkflowGraph


ALGORITHM_RELEVANT_TYPES = {"backend", "database", "ml"}


def tasks_needing_algorithm_decision(graph: WorkflowGraph) -> list[Task]:
    """
    Every backend, database, or ml task gets an algorithm decision —
    implementation approach matters for all of them, not just ones
    whose name happens to contain a specific keyword.
    """
    return [t for t in graph.tasks if t.type in ALGORITHM_RELEVANT_TYPES]
