from algorithm_ensemble import SELECTOR_PROFILES, recommend_ensemble
from schema import Task


def test_all_relevant_task_types_receive_ensemble_decisions():
    tasks = [
        Task(id="t1", name="Users", type="database", description="Store users"),
        Task(id="t2", name="Product Search", type="backend", description="Search products"),
        Task(id="t3", name="Recommendations", type="ml", description="Classify product preferences"),
        Task(id="t4", name="Frontend", type="frontend", description="Render the application"),
    ]

    decisions = recommend_ensemble(tasks, "Build an e-commerce platform")

    assert [decision.task_id for decision in decisions] == ["t1", "t2", "t3"]
    assert all(decision.source == "ensemble" for decision in decisions)
    assert all(decision.chosen_algorithm for decision in decisions)
    assert len(SELECTOR_PROFILES) == 10
