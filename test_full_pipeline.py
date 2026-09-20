import pytest

from schema import AlgorithmReport, Flaw, FlawReport, FlawType, ModelSelectionReport, RiskReport, Severity, Task, WorkflowGraph


def _graph():
    return WorkflowGraph(tasks=[Task(id="t1", name="API", type="backend", description="Serve data")])


def test_pipeline_preserves_results_when_early_halt_occurs(monkeypatch):
    pipeline = pytest.importorskip("pipeline")
    graph = _graph()
    flaws = FlawReport(
        flaws=[Flaw(task_ids=["t1"], type=FlawType.security, severity=Severity.high, description="Unsafe", suggested_fix="Fix")],
        is_safe_to_proceed=False,
    )
    monkeypatch.setattr(pipeline, "get_valid_workflow", lambda requirement: graph)
    monkeypatch.setattr(pipeline, "get_flaw_report", lambda graph: flaws)

    result = pipeline.run_full_pipeline("Build API")

    assert result["workflow"] is graph
    assert result["flaws"] is flaws
    assert result["halted_at"] == "flaw_detection"
    assert "stack" not in result


def test_pipeline_keeps_structured_empty_optional_results(monkeypatch):
    pipeline = pytest.importorskip("pipeline")
    graph = _graph()
    monkeypatch.setattr(pipeline, "get_valid_workflow", lambda requirement: graph)
    monkeypatch.setattr(pipeline, "get_flaw_report", lambda graph: FlawReport(flaws=[], is_safe_to_proceed=True))
    monkeypatch.setattr(pipeline, "decide_stack", lambda graph, user_stack: {"mode": "recommended", "recommendation": object()})
    monkeypatch.setattr(pipeline, "decide_algorithms", lambda graph, requirement: AlgorithmReport(decisions=[]))
    monkeypatch.setattr(pipeline, "decide_ai_models", lambda graph, algorithm_report, risk_tolerance: ModelSelectionReport(decisions=[]))
    monkeypatch.setattr(pipeline, "predict_risks", lambda graph, algorithm_report, model_report, event_log_path=None: RiskReport(predictions=[]))

    result = pipeline.run_full_pipeline("Build API", risk_tolerance="invalid")

    assert result["halted_at"] is None
    assert result["summary"]["total_tasks"] == 1
    assert result["summary"]["high_risk_task_count"] == 0