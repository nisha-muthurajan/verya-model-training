import importlib
import sys
import types

from schema import AlgorithmReport, Flaw, FlawReport, FlawType, ModelSelectionReport, RiskReport, Severity, Task, WorkflowGraph


def _graph():
    return WorkflowGraph(tasks=[Task(id="t1", name="API", type="backend", description="Serve data")])


def _load_pipeline(monkeypatch):
    groq_stub = types.ModuleType("groq")
    groq_stub.Groq = type("Groq", (), {})
    monkeypatch.setitem(sys.modules, "groq", groq_stub)
    return importlib.import_module("pipeline")


def test_pipeline_preserves_results_when_early_halt_occurs(monkeypatch):
    pipeline = _load_pipeline(monkeypatch)
    graph = _graph()
    flaws = FlawReport(
        flaws=[Flaw(task_ids=["t1"], type=FlawType.security, severity=Severity.high, description="Unsafe", suggested_fix="Fix")],
        is_safe_to_proceed=False,
    )
    monkeypatch.setattr(pipeline, "get_valid_workflow", lambda requirement: graph)
    monkeypatch.setattr(pipeline, "get_flaw_report", lambda graph, event_log_path=None: flaws)

    result = pipeline.run_full_pipeline("Build API")

    assert result["workflow"] is graph
    assert result["flaws"] is flaws
    assert result["halted_at"] == "flaw_detection"
    assert "stack" not in result


def test_pipeline_keeps_structured_empty_optional_results(monkeypatch):
    pipeline = _load_pipeline(monkeypatch)
    graph = _graph()
    monkeypatch.setattr(pipeline, "get_valid_workflow", lambda requirement: graph)
    monkeypatch.setattr(pipeline, "get_flaw_report", lambda graph, event_log_path=None: FlawReport(flaws=[], is_safe_to_proceed=True))
    monkeypatch.setattr(pipeline, "decide_stack", lambda graph, user_stack: {"mode": "recommended", "recommendation": object()})
    monkeypatch.setattr(pipeline, "decide_algorithms", lambda graph, requirement: AlgorithmReport(decisions=[]))
    monkeypatch.setattr(pipeline, "decide_ai_models", lambda graph, algorithm_report, risk_tolerance: ModelSelectionReport(decisions=[]))
    monkeypatch.setattr(pipeline, "predict_risks", lambda graph, algorithm_report, model_report, event_log_path=None: RiskReport(predictions=[]))

    result = pipeline.run_full_pipeline("Build API", risk_tolerance="invalid")

    assert result["halted_at"] is None
    assert result["summary"]["total_tasks"] == 1
    assert result["summary"]["high_risk_task_count"] == 0


def test_pipeline_converts_malformed_optional_stages_to_empty_reports(monkeypatch):
    pipeline = _load_pipeline(monkeypatch)
    graph = _graph()
    monkeypatch.setattr(pipeline, "get_valid_workflow", lambda requirement: graph)
    monkeypatch.setattr(pipeline, "detect_flaws", lambda graph, event_log_path=None: None)
    monkeypatch.setattr(pipeline, "recommend_stack", lambda graph: object())
    monkeypatch.setattr(pipeline, "recommend_algorithms", lambda graph, requirement: (_ for _ in ()).throw(RuntimeError("provider detail")))
    monkeypatch.setattr(pipeline, "select_model", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("router detail")))
    monkeypatch.setattr(pipeline, "predict_risk_ensemble", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("risk detail")))

    result = pipeline.run_full_pipeline("Build API")

    assert result["flaws"].flaws == []
    assert result["algorithms"].decisions == []
    assert result["model_routing"].decisions == []
    assert result["risk"].predictions == []
    assert result["summary"]["high_risk_task_count"] == 0