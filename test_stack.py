from schema import Task, WorkflowGraph
from stack_rules import rule_based_stack_checks


def test_stack_keys_values_are_normalized_and_blank_database_is_missing():
    graph = WorkflowGraph(tasks=[
        Task(id="t1", name="Storage", type="database", description="Store records"),
        Task(id="t2", name="Model", type="ml", description="Train model"),
    ])

    issues = rule_based_stack_checks(graph, {" BACKEND ": "  PHP  ", " DATABASE ": " PostgreSQL "})

    assert [issue.category for issue in issues] == ["ml_framework"]
    assert rule_based_stack_checks(graph, {"database": "   "})[0].severity == "critical"


def test_unexpected_stack_value_types_are_ignored_safely():
    graph = WorkflowGraph(tasks=[
        Task(id="t1", name="Storage", type="database", description="Store records"),
    ])

    assert rule_based_stack_checks(graph, {"database": ["PostgreSQL"]})[0].severity == "critical"