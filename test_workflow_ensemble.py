from algorithm_filter import tasks_needing_algorithm_decision
from validate import validate_graph
from workflow_ensemble import WORKFLOW_ADVISORS, understand_workflow_ensemble


def test_workflow_ensemble_builds_valid_ecommerce_graph(monkeypatch):
    for key in ("WORKFLOW_MODEL_ENDPOINTS", "WORKFLOW_REQUIRE_API", "GROQ_API_KEY", "ZAI_API_KEY", "OPENAI_API_KEY", "OPEN_AI_API_KEY", "GEMINI_API_KEY", "MINIMAX_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    graph = understand_workflow_ensemble("Build an e-commerce platform with product search and payments.")

    assert len(WORKFLOW_ADVISORS) == 10
    assert validate_graph(graph) == []
    assert {task.type for task in graph.tasks} >= {"database", "auth", "backend", "integration", "frontend"}
    assert tasks_needing_algorithm_decision(graph)


def test_workflow_ensemble_builds_valid_blog_graph(monkeypatch):
    for key in ("WORKFLOW_MODEL_ENDPOINTS", "WORKFLOW_REQUIRE_API", "GROQ_API_KEY", "ZAI_API_KEY", "OPENAI_API_KEY", "OPEN_AI_API_KEY", "GEMINI_API_KEY", "MINIMAX_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    graph = understand_workflow_ensemble("Build a blog where users can write and read posts.")

    assert validate_graph(graph) == []
    assert any("Post" in task.name for task in graph.tasks)
    assert any(task.type == "backend" for task in graph.tasks)
