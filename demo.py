"""
One-command full pipeline demo. Run: python demo.py
"""
from pipeline import (
    get_valid_workflow, get_flaw_report, decide_stack,
    decide_algorithms, decide_ai_models, predict_risks,
    verify_and_record
)
from workflow_ensemble import workflow_source

def print_section(title):
    print(f"\n{'='*70}\n{title}\n{'='*70}")


def print_task_record(task, algorithm, routed_model, risk):
    print(f"\n  TASK {task.id}: {task.name} [{task.type}]")
    print(f"    What it does: {task.description}")
    print(f"    Depends on: {', '.join(task.depends_on) if task.depends_on else 'nothing'}")
    if algorithm:
        print(f"    Algorithm: {algorithm.chosen_algorithm} (confidence={algorithm.confidence})")
        print(f"      Why: {algorithm.reasoning}")
        if algorithm.alternatives_considered:
            print("      Alternatives:")
            for alternative in algorithm.alternatives_considered:
                print(f"        - {alternative.name}: pros={alternative.pros}; cons={alternative.cons}")
    else:
        print("    Algorithm: no specialized algorithm decision was required")
    if routed_model:
        print(f"    AI model: {routed_model.chosen_model} ({routed_model.chosen_provider})")
        print(f"      Why: {routed_model.reasoning}")
        print(f"      Required capability tier: {routed_model.required_capability_tier}")
        if routed_model.alternatives_considered:
            print("      Alternative models:")
            for alternative in routed_model.alternatives_considered:
                print(f"        - {alternative.name} ({alternative.provider})")
    if risk:
        print(f"    Failure risk: {risk.failure_probability} ({risk.severity_if_failed})")
        print(f"      Signals: {'; '.join(risk.risk_factors)}")


def run_demo(requirement: str, user_stack: dict = None, risk_tolerance: float = 0.5, force_continue: bool = True):
    print_section(f"REQUIREMENT: {requirement}")

    # Model 1
    graph = get_valid_workflow(requirement)
    print_section("MODEL 1 — Workflow Understanding")
    print(f"  Source: {workflow_source()}")
    for t in graph.tasks:
        dependencies = ', '.join(t.depends_on) if t.depends_on else 'none'
        print(f"  [{t.id}] {t.name} ({t.type})")
        print(f"    Purpose: {t.description}")
        print(f"    Dependencies: {dependencies}")

    # Model 2
    flaw_report = get_flaw_report(graph)
    print_section("MODEL 2 — Flaw Detection")
    print(f"  Safe to proceed: {flaw_report.is_safe_to_proceed}")
    for f in flaw_report.flaws:
        print(f"  [{f.severity.upper()}] {f.description}")
        print(f"    Fix: {f.suggested_fix}")
    if not flaw_report.flaws:
        print("  Why: no structural, security, performance, or logic flaws were detected.")

    if not flaw_report.is_safe_to_proceed and not force_continue:
        print("\n>>> HALTED — set force_continue=True to see Models 3-8 anyway <<<")
        return

    # Model 3
    stack_result = decide_stack(graph, user_stack)
    print_section("MODEL 3 — Stack Recommendation/Validation")
    if stack_result["mode"] == "recommended":
        print(f"  Why: {stack_result['recommendation'].summary}")
        for c in stack_result["recommendation"].components:
            print(f"  [{c.category}] {c.name} (confidence={c.confidence})")
            print(f"    Why: {c.reasoning}")
    else:
        report = stack_result["report"]
        print(f"  Compatible: {report.is_compatible}")
        for i in report.issues:
            print(f"  [{i.severity.upper()}] {i.issue}")

    # Model 4
    algo_report = decide_algorithms(graph, requirement)
    print_section("MODEL 4 — Algorithm Recommendation")
    for d in algo_report.decisions:
        tag = f"[{d.source.upper()}]" if hasattr(d, 'source') else ""
        print(f"  {tag} [{d.task_id}] {d.chosen_algorithm} (confidence={d.confidence}, tiebreak={d.requires_human_tiebreak})")
        print(f"    Why: {d.reasoning}")
        print(f"    Assumptions: {d.assumed_constraints}")
        for alternative in d.alternatives_considered:
            print(f"    Alternative: {alternative.name} — pros={alternative.pros}; cons={alternative.cons}")

    # Model 5
    model_report = decide_ai_models(graph, algo_report, risk_tolerance=risk_tolerance)
    print_section(f"MODEL 5 — AI Model Router (risk_tolerance={risk_tolerance})")
    for d in model_report.decisions:
        print(f"  [{d.task_id}] {d.chosen_model} ({d.chosen_provider}) tiebreak={d.requires_human_tiebreak}")
        print(f"    Why: {d.reasoning}")
        print(f"    Required capability tier: {d.required_capability_tier}")
        for alternative in d.alternatives_considered:
            print(f"    Alternative: {alternative.name} ({alternative.provider})")

    # Model 6
    risk_report = predict_risks(graph, algo_report, model_report)
    print_section("MODEL 6 — Failure/Risk Prediction")
    for p in sorted(risk_report.predictions, key=lambda x: -x.failure_probability):
        print(f"  [{p.task_id}] risk={p.failure_probability} ({p.severity_if_failed})")
        print(f"    Why: {'; '.join(p.risk_factors)}")

    # Models 7 + 8 — simulate on the first task, since real code execution doesn't exist yet
    print_section("MODEL 7 + 8 — Output Verification & Reputation (simulated on task 1)")
    sample_task = graph.tasks[0]
    sample_model = model_report.decisions[0].chosen_model
    fake_output = f"# placeholder implementation for: {sample_task.name}\ndef handler():\n    pass"
    verification = verify_and_record(
        task_id=sample_task.id, task_description=sample_task.description,
        task_type=sample_task.type, chosen_model=sample_model, output=fake_output
    )
    print(f"  Verified task {sample_task.id}: passed={verification.passed}")
    print(f"  Reputation updated for {sample_model} on '{sample_task.type}' tasks")

    algorithm_lookup = {decision.task_id: decision for decision in algo_report.decisions}
    model_lookup = {decision.task_id: decision for decision in model_report.decisions}
    risk_lookup = {prediction.task_id: prediction for prediction in risk_report.predictions}
    print_section("COMPLETE TASK-BY-TASK DECISION SUMMARY")
    for task in graph.tasks:
        print_task_record(task, algorithm_lookup.get(task.id), model_lookup.get(task.id), risk_lookup.get(task.id))

    print_section("PIPELINE COMPLETE — ALL 8 MODELS EXECUTED")


if __name__ == "__main__":
    run_demo("Build a website for an college attendance system.", risk_tolerance=0.5, force_continue=True)