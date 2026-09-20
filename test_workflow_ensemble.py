import pytest

from algorithm_filter import tasks_needing_algorithm_decision
from pydantic import ValidationError
from schema import Flaw, FlawReport, FlawType, Severity, Task
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


def test_schema_rejects_invalid_task_dependencies():
    with pytest.raises(ValidationError):
        Task(id="t1", name="Task", type="backend", description="Work", depends_on=["t1"])


def test_flaw_report_safety_flag_matches_severity():
    flaw = Flaw(
        task_ids=["t1"],
        type=FlawType.security,
        severity=Severity.high,
        description="Unsafe",
        suggested_fix="Fix it",
    )

    with pytest.raises(ValidationError):
        FlawReport(flaws=[flaw], is_safe_to_proceed=True)
