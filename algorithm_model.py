# algorithm_model.py — complete replacement
from schema import AlgorithmReport, WorkflowGraph
from algorithm_filter import tasks_needing_algorithm_decision
from algorithm_ensemble import recommend_ensemble


def recommend_algorithms(graph: WorkflowGraph, original_requirement: str) -> AlgorithmReport:
    relevant_tasks = tasks_needing_algorithm_decision(graph)

    all_decisions = recommend_ensemble(relevant_tasks, original_requirement)

    # Hard assertion — this makes a future regression IMPOSSIBLE to miss silently.
    expected_ids = {t.id for t in relevant_tasks}
    actual_ids = {d.task_id for d in all_decisions}
    assert expected_ids == actual_ids, (
        f"Model 4 completeness check FAILED. Expected decisions for {expected_ids}, "
        f"got {actual_ids}. Missing: {expected_ids - actual_ids}"
    )

    return AlgorithmReport(decisions=all_decisions)