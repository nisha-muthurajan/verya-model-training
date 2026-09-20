# test_php_ml_rule.py
from schema import Task, WorkflowGraph
from stack_rules import rule_based_stack_checks


def test_php_backend_is_flagged_for_ml_workflow():
    graph = WorkflowGraph(tasks=[
        Task(id="t1", name="Recommendation Model", type="ml", description="Train recommendations"),
    ])

    issues = rule_based_stack_checks(graph, {"backend": "PHP"})

    assert len(issues) == 1
    assert issues[0].category == "ml_framework"
    assert issues[0].severity == "high"