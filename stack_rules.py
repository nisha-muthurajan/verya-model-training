from schema import WorkflowGraph, StackValidationIssue

# very small known-limitation lookup table — expand this over time
KNOWN_LIMITATIONS = {
    "php": {"ml": "PHP has poor support for ML workflows. Consider a Python-based service for ML tasks."},
    "sqlite": {"backend": "SQLite is not suited for multi-user, concurrent-write backend services at scale."},
}


def rule_based_stack_checks(graph: WorkflowGraph, user_stack: dict) -> list[StackValidationIssue]:
    issues = []
    task_types_present = {t.type for t in graph.tasks}

    # Rule 1: ML tasks require an ML-capable backend
    backend_choice = user_stack.get("backend", "").lower()
    if "ml" in task_types_present:
        for tech, limitations in KNOWN_LIMITATIONS.items():
            if tech in backend_choice and "ml" in limitations:
                issues.append(StackValidationIssue(
                    category="ml_framework",
                    issue=limitations["ml"],
                    severity="high",
                    suggested_alternative="Python (FastAPI) or a dedicated ML microservice"
                ))

    # Rule 2: database task type with no database in the stack at all
    if "database" in task_types_present and "database" not in user_stack:
        issues.append(StackValidationIssue(
            category="database",
            issue="Task graph requires data storage but no database was specified in the stack.",
            severity="critical",
            suggested_alternative="Add a database (e.g. PostgreSQL, MongoDB)."
        ))

    return issues