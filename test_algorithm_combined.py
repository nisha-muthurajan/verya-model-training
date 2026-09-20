# test_algorithm_combined.py
from algorithm_model import recommend_algorithms
from schema import Task, WorkflowGraph


def test_algorithm_recommendations_cover_backend_database_and_ml_tasks():
    requirement = "Build a product recommendation system with one million products."
    graph = WorkflowGraph(tasks=[
        Task(id="t1", name="Product Storage", type="database", description="Store products"),
        Task(id="t2", name="Recommendation API", type="backend", description="Serve recommendations"),
        Task(id="t3", name="Recommendation Model", type="ml", description="Classify product preferences"),
    ])

    report = recommend_algorithms(graph, requirement)

    assert [decision.task_id for decision in report.decisions] == ["t1", "t2", "t3"]
    assert all(decision.chosen_algorithm for decision in report.decisions)
    assert all(0 <= decision.confidence <= 1 for decision in report.decisions)
    assert report.decisions[-1].problem_type == "classification_tabular"