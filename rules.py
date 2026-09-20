import re

from schema import WorkflowGraph, Flaw

SENSITIVE_KEYWORDS = ["payment", "order", "post", "delete", "admin", "user data", "leave request", "approve", "cart"]


def _mentions_sensitive_operation(text: str) -> bool:
    return any(
        re.search(
            rf"\b{re.escape(keyword)}(?:s|es)?\b(?!-)",
            text,
        )
        for keyword in SENSITIVE_KEYWORDS
    )


def _has_auth_ancestor(task_id: str, tasks_by_id: dict[str, object]) -> bool:
    pending = list(tasks_by_id[task_id].depends_on)
    visited = set()
    while pending:
        dependency_id = pending.pop()
        if dependency_id in visited:
            continue
        visited.add(dependency_id)
        dependency = tasks_by_id.get(dependency_id)
        if dependency is None:
            continue
        if dependency.type == "auth":
            return True
        pending.extend(dependency.depends_on)
    return False


def rule_based_checks(graph: WorkflowGraph) -> list[Flaw]:
    flaws = []
    tasks_by_id = {task.id: task for task in graph.tasks}
    has_auth_task = any(task.type == "auth" for task in graph.tasks)

    for t in graph.tasks:
        # Rule 1: sensitive-sounding backend tasks should depend on an auth task
        text = f"{t.name} {t.description}".lower()
        if t.type == "backend" and _mentions_sensitive_operation(text):
            if not has_auth_task or not _has_auth_ancestor(t.id, tasks_by_id):
                auth_message = (
                    "no Authentication task exists in the workflow"
                    if not has_auth_task
                    else "does not depend on an Authentication task"
                )
                flaws.append(Flaw(
                    task_ids=[t.id],
                    type="security",
                    severity="high",
                    description=f"Task '{t.name}' looks sensitive but {auth_message}.",
                    suggested_fix=f"Add a dependency from {t.id} to an authentication task."
                ))

    # Rule 2: frontend must not be the only task with no backend to talk to
    has_backend = any(t.type == "backend" for t in graph.tasks)
    has_frontend = any(t.type == "frontend" for t in graph.tasks)
    if has_frontend and not has_backend:
        flaws.append(Flaw(
            task_ids=[t.id for t in graph.tasks if t.type == "frontend"],
            type="architecture",
            severity="critical",
            description="Frontend task exists with no backend task for it to call.",
            suggested_fix="Add backend API task(s) that the frontend depends on."
        ))

    return flaws