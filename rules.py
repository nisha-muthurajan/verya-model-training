from schema import WorkflowGraph, Flaw

SENSITIVE_KEYWORDS = ["payment", "order", "post", "delete", "admin", "user data", "leave request", "approve", "cart"]


def rule_based_checks(graph: WorkflowGraph) -> list[Flaw]:
    flaws = []
    auth_task_ids = [t.id for t in graph.tasks if t.type == "auth"]

    for t in graph.tasks:
        # Rule 1: sensitive-sounding backend tasks should depend on an auth task
        if t.type == "backend" and any(k in f"{t.name} {t.description}".lower() for k in SENSITIVE_KEYWORDS):
            if auth_task_ids and not any(dep in auth_task_ids for dep in t.depends_on):
                flaws.append(Flaw(
                    task_ids=[t.id],
                    type="security",
                    severity="high",
                    description=f"Task '{t.name}' looks sensitive but does not depend on any Authentication task.",
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