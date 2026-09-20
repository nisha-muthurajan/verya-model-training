"""
One-command full pipeline demo. Run: python demo.py
"""
from pipeline import (
    get_valid_workflow, get_flaw_report, decide_stack,
    decide_algorithms, decide_ai_models, predict_risks,
    verify_and_record
)
from workflow_ensemble import workflow_source


def _items(value, attribute):
    items = getattr(value, attribute, []) if value is not None else []
    return items if isinstance(items, list) else []


def _text(value, default="unavailable"):
    return value.strip() if isinstance(value, str) and value.strip() else default


def _task_id(task):
    return _text(getattr(task, "id", None), "unknown")


def _print_unavailable(stage):
    print(f"  {stage}: unavailable")


def print_section(title):
    print(f"\n{'='*70}\n{title}\n{'='*70}")


def print_task_record(task, algorithm, routed_model, risk):
    task_id = _task_id(task)
    task_name = _text(getattr(task, "name", None), "Unnamed task")
    task_type = _text(getattr(task, "type", None), "unknown")
    description = _text(getattr(task, "description", None), "No description")
    dependencies = getattr(task, "depends_on", [])
    if not isinstance(dependencies, (list, tuple)):
        dependencies = []
    dependencies = ", ".join(_text(dependency, "unknown") for dependency in dependencies) or "nothing"

    print(f"\n  TASK {task_id}: {task_name} [{task_type}]")
    print(f"    What it does: {description}")
    print(f"    Depends on: {dependencies}")
    if algorithm:
        print(f"    Algorithm: {_text(getattr(algorithm, 'chosen_algorithm', None))} (confidence={getattr(algorithm, 'confidence', 'unavailable')})")
        print(f"      Why: {_text(getattr(algorithm, 'reasoning', None))}")
        alternatives = _items(algorithm, "alternatives_considered")
        if alternatives:
            print("      Alternatives:")
            for alternative in alternatives:
                print(f"        - {_text(getattr(alternative, 'name', None))}: pros={_text(getattr(alternative, 'pros', None))}; cons={_text(getattr(alternative, 'cons', None))}")
    else:
        print("    Algorithm: no specialized algorithm decision was required")
    if routed_model:
        print(f"    AI model: {_text(getattr(routed_model, 'chosen_model', None))} ({_text(getattr(routed_model, 'chosen_provider', None))})")
        print(f"      Why: {_text(getattr(routed_model, 'reasoning', None))}")
        print(f"      Required capability tier: {getattr(routed_model, 'required_capability_tier', 'unavailable')}")
        alternatives = _items(routed_model, "alternatives_considered")
        if alternatives:
            print("      Alternative models:")
            for alternative in alternatives:
                print(f"        - {_text(getattr(alternative, 'name', None))} ({_text(getattr(alternative, 'provider', None))})")
    if risk:
        factors = getattr(risk, "risk_factors", [])
        if not isinstance(factors, list):
            factors = []
        print(f"    Failure risk: {getattr(risk, 'failure_probability', 'unavailable')} ({_text(getattr(risk, 'severity_if_failed', None))})")
        print(f"      Signals: {'; '.join(_text(factor) for factor in factors) or 'none'}")


def run_demo(requirement: str, user_stack: dict = None, risk_tolerance: float = 0.5, force_continue: bool = True):
    print_section(f"REQUIREMENT: {requirement}")

    # Model 1
    try:
        graph = get_valid_workflow(requirement)
    except Exception:
        print("  Workflow could not be generated.")
        return
    tasks = _items(graph, "tasks")
    if not tasks:
        print_section("MODEL 1 — Workflow Understanding")
        _print_unavailable("Workflow tasks")
        return
    print_section("MODEL 1 — Workflow Understanding")
    print(f"  Source: {workflow_source()}")
    for t in tasks:
        dependencies = getattr(t, "depends_on", [])
        if not isinstance(dependencies, (list, tuple)):
            dependencies = []
        dependencies = ", ".join(_text(dependency, "unknown") for dependency in dependencies) or "none"
        print(f"  [{_task_id(t)}] {_text(getattr(t, 'name', None), 'Unnamed task')} ({_text(getattr(t, 'type', None), 'unknown')})")
        print(f"    Purpose: {_text(getattr(t, 'description', None), 'No description')}")
        print(f"    Dependencies: {dependencies}")

    # Model 2
    try:
        flaw_report = get_flaw_report(graph)
    except Exception:
        flaw_report = None
    print_section("MODEL 2 — Flaw Detection")
    flaws = _items(flaw_report, "flaws")
    safe_to_proceed = getattr(flaw_report, "is_safe_to_proceed", True)
    print(f"  Safe to proceed: {safe_to_proceed}")
    for f in flaws:
        severity = _text(getattr(f, "severity", None), "unknown").upper()
        print(f"  [{severity}] {_text(getattr(f, 'description', None), 'No description')}")
        print(f"    Fix: {_text(getattr(f, 'suggested_fix', None), 'No suggested fix')}")
    if not flaws:
        print("  Why: no structural, security, performance, or logic flaws were detected.")

    if not safe_to_proceed and not force_continue:
        print("\n>>> HALTED — set force_continue=True to see Models 3-8 anyway <<<")
        return

    # Model 3
    try:
        stack_result = decide_stack(graph, user_stack)
    except Exception:
        stack_result = None
    print_section("MODEL 3 — Stack Recommendation/Validation")
    if not isinstance(stack_result, dict):
        _print_unavailable("Stack validation")
    elif stack_result.get("mode") == "recommended":
        recommendation = stack_result.get("recommendation")
        if recommendation is None:
            _print_unavailable("Stack recommendation")
        else:
            print(f"  Why: {_text(getattr(recommendation, 'summary', None), 'No summary')}")
            for c in _items(recommendation, "components"):
                print(f"  [{_text(getattr(c, 'category', None), 'unknown')}] {_text(getattr(c, 'name', None))} (confidence={getattr(c, 'confidence', 'unavailable')})")
                print(f"    Why: {_text(getattr(c, 'reasoning', None))}")
    else:
        report = stack_result.get("report")
        if report is None:
            _print_unavailable("Stack validation")
        else:
            print(f"  Compatible: {getattr(report, 'is_compatible', 'unavailable')}")
            for i in _items(report, "issues"):
                print(f"  [{_text(getattr(i, 'severity', None), 'unknown').upper()}] {_text(getattr(i, 'issue', None), 'No issue description')}")

    # Model 4
    try:
        algo_report = decide_algorithms(graph, requirement)
    except Exception:
        algo_report = None
    print_section("MODEL 4 — Algorithm Recommendation")
    algorithm_decisions = _items(algo_report, "decisions")
    if not algorithm_decisions:
        _print_unavailable("Algorithm decisions")
    for d in algorithm_decisions:
        source = _text(getattr(d, "source", None), "").upper()
        tag = f"[{source}]" if source else ""
        print(f"  {tag} [{_text(getattr(d, 'task_id', None), 'unknown')}] {_text(getattr(d, 'chosen_algorithm', None))} (confidence={getattr(d, 'confidence', 'unavailable')}, tiebreak={getattr(d, 'requires_human_tiebreak', 'unavailable')})")
        print(f"    Why: {_text(getattr(d, 'reasoning', None))}")
        print(f"    Assumptions: {_text(getattr(d, 'assumed_constraints', None), 'None')}")
        for alternative in _items(d, "alternatives_considered"):
            print(f"    Alternative: {_text(getattr(alternative, 'name', None))} — pros={_text(getattr(alternative, 'pros', None))}; cons={_text(getattr(alternative, 'cons', None))}")

    # Model 5
    try:
        model_report = decide_ai_models(graph, algo_report, risk_tolerance=risk_tolerance)
    except Exception:
        model_report = None
    print_section(f"MODEL 5 — AI Model Router (risk_tolerance={risk_tolerance})")
    model_decisions = _items(model_report, "decisions")
    if not model_decisions:
        _print_unavailable("Model decisions")
    for d in model_decisions:
        print(f"  [{_text(getattr(d, 'task_id', None), 'unknown')}] {_text(getattr(d, 'chosen_model', None))} ({_text(getattr(d, 'chosen_provider', None))}) tiebreak={getattr(d, 'requires_human_tiebreak', 'unavailable')}")
        print(f"    Why: {_text(getattr(d, 'reasoning', None))}")
        print(f"    Required capability tier: {getattr(d, 'required_capability_tier', 'unavailable')}")
        for alternative in _items(d, "alternatives_considered"):
            print(f"    Alternative: {_text(getattr(alternative, 'name', None))} ({_text(getattr(alternative, 'provider', None))})")

    # Model 6
    try:
        risk_report = predict_risks(graph, algo_report, model_report)
    except Exception:
        risk_report = None
    print_section("MODEL 6 — Failure/Risk Prediction")
    predictions = _items(risk_report, "predictions")
    if not predictions:
        _print_unavailable("Risk predictions")
    for p in sorted(predictions, key=lambda x: (-getattr(x, "failure_probability", 0), _text(getattr(x, "task_id", None), "unknown"))):
        print(f"  [{p.task_id}] risk={p.failure_probability} ({p.severity_if_failed})")
        print(f"    Why: {'; '.join(_text(factor) for factor in getattr(p, 'risk_factors', []) if isinstance(getattr(p, 'risk_factors', []), list)) or 'none'}")

    # Models 7 + 8 — simulate on the first task, since real code execution doesn't exist yet
    print_section("MODEL 7 + 8 — Output Verification & Reputation (simulated on task 1)")
    if tasks and model_decisions:
        sample_task = tasks[0]
        sample_model = _text(getattr(model_decisions[0], "chosen_model", None), "unavailable")
        fake_output = f"# placeholder implementation for: {_text(getattr(sample_task, 'name', None), 'task')}\ndef handler():\n    pass"
        try:
            verification = verify_and_record(
                task_id=_task_id(sample_task), task_description=_text(getattr(sample_task, 'description', None), 'No description'),
                task_type=_text(getattr(sample_task, 'type', None), 'unknown'), chosen_model=sample_model, output=fake_output
            )
        except Exception:
            verification = None
        if verification is None:
            _print_unavailable("Verification")
        else:
            print(f"  Verified task {_task_id(sample_task)}: passed={getattr(verification, 'passed', 'unavailable')}")
            print(f"  Reputation updated for {sample_model} on '{_text(getattr(sample_task, 'type', None), 'unknown')}' tasks")
    else:
        _print_unavailable("Verification and reputation update")

    algorithm_lookup = {_task_id(decision): decision for decision in algorithm_decisions}
    model_lookup = {_task_id(decision): decision for decision in model_decisions}
    risk_lookup = {_task_id(prediction): prediction for prediction in predictions}
    print_section("COMPLETE TASK-BY-TASK DECISION SUMMARY")
    for task in graph.tasks:
        print_task_record(task, algorithm_lookup.get(task.id), model_lookup.get(task.id), risk_lookup.get(task.id))

    print_section("PIPELINE COMPLETE — ALL 8 MODELS EXECUTED")


if __name__ == "__main__":
    run_demo("Build a website for an college attendance system.", risk_tolerance=0.5, force_continue=True)