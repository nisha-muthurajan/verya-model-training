from schema import WorkflowGraph, StackValidationIssue

# very small known-limitation lookup table — expand this over time
KNOWN_LIMITATIONS = {
    "php": {"ml": "PHP has poor support for ML workflows. Consider a Python-based service for ML tasks."},
    "sqlite": {"backend": "SQLite is not suited for multi-user, concurrent-write backend services at scale."},
}


def _normalize_stack(user_stack: object) -> dict[str, str]:
    if not isinstance(user_stack, dict):
        return {}

    normalized = {}
    for key, value in user_stack.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        normalized_key = key.strip().lower()
        normalized_value = value.strip().lower()
        if normalized_key and normalized_value and normalized_key not in normalized:
            normalized[normalized_key] = normalized_value
    return normalized


def rule_based_stack_checks(graph: WorkflowGraph, user_stack: dict) -> list[StackValidationIssue]:
    issues = []
    stack = _normalize_stack(user_stack)
    task_types_present = {
        task_type.strip().lower()
        for task_type in (t.type for t in graph.tasks)
        if isinstance(task_type, str) and task_type.strip()
    }

    # Rule 1: ML tasks require an ML-capable backend
    backend_choice = stack.get("backend", "")
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
    if "database" in task_types_present and "database" not in stack:
        issues.append(StackValidationIssue(
            category="database",
            issue="Task graph requires data storage but no database was specified in the stack.",
            severity="critical",
            suggested_alternative="Add a database (e.g. PostgreSQL, MongoDB)."
        ))

    return issues