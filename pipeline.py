from workflow_model import understand_workflow
from validate import validate_graph
from flaw_model import detect_flaws
from rules import rule_based_checks
from stack_model import recommend_stack, validate_stack
from stack_rules import rule_based_stack_checks
from algorithm_model import recommend_algorithms



def get_valid_workflow(requirement: str, max_retries: int = 2):
    """Model 1: requirement -> validated task graph"""
    last_errors = []
    for attempt in range(max_retries + 1):
        prompt = requirement
        if last_errors:
            prompt += f"\n\nYour previous attempt had these problems, fix them: {last_errors}"
        graph = understand_workflow(prompt)
        errors = validate_graph(graph)
        if not errors:
            return graph
        last_errors = errors
    raise ValueError(f"Could not produce valid graph after {max_retries + 1} attempts: {last_errors}")


def get_flaw_report(graph):
    llm_report = detect_flaws(graph)
    rule_flaws = rule_based_checks(graph)

    # Dedupe by (task_id, type) only — same logic as stack validation
    seen = {(f.task_ids[0], f.type) for f in llm_report.flaws if f.task_ids}
    for rf in rule_flaws:
        key = (rf.task_ids[0], rf.type) if rf.task_ids else None
        if key not in seen:
            llm_report.flaws.append(rf)
            if key:
                seen.add(key)

    llm_report.is_safe_to_proceed = not any(
        f.severity in ("high", "critical") for f in llm_report.flaws
    )
    return llm_report


def run_full_pipeline(requirement: str):
    """End-to-end: requirement -> graph -> flaw report"""
    graph = get_valid_workflow(requirement)
    report = get_flaw_report(graph)
    return graph, report


def decide_algorithms(graph, original_requirement: str):
    """Recommend algorithms for the graph's ML and algorithm-sensitive tasks."""
    return recommend_algorithms(graph, original_requirement)




def decide_stack(graph, user_stack: dict = None):
    if user_stack:
        llm_report = validate_stack(graph, user_stack)
        rule_issues = rule_based_stack_checks(graph, user_stack)

        # Dedupe by category only — if the LLM already caught a problem 
        # in this category, skip the rule's version to avoid saying the 
        # same thing twice in different words.
        categories_already_flagged = {i.category for i in llm_report.issues}
        for ri in rule_issues:
            if ri.category not in categories_already_flagged:
                llm_report.issues.append(ri)
                categories_already_flagged.add(ri.category)

        llm_report.is_compatible = not any(
            i.severity in ("high", "critical") for i in llm_report.issues
        )
        return {"mode": "validated", "stack": user_stack, "report": llm_report}

    else:
        recommendation = recommend_stack(graph)
        return {"mode": "recommended", "recommendation": recommendation}

# Add to pipeline.py
from router_model import select_model
from schema import ModelSelectionReport


def decide_ai_models(graph, algorithm_report, risk_tolerance: float = 0.5):
    """
    Model 5: for every task, decide which AI model should execute it,
    using complexity signals + the Cost-vs-Risk slider (risk_tolerance).
    """
    algo_lookup = {d.task_id: d for d in algorithm_report.decisions}
    decisions = []

    for t in graph.tasks:
        algo_decision = algo_lookup.get(t.id)
        algo_confidence = algo_decision.confidence if algo_decision else None
        needs_tiebreak = algo_decision.requires_human_tiebreak if algo_decision else False

        decision = select_model(t, algorithm_confidence=algo_confidence,
                                 requires_tiebreak=needs_tiebreak, risk_tolerance=risk_tolerance)
        decisions.append(decision)

    return ModelSelectionReport(decisions=decisions)


# Add to pipeline.py
from risk_heuristic import predict_risk_heuristic
from schema import RiskReport


def predict_risks(graph, algorithm_report, model_report):
    algo_lookup = {d.task_id: d for d in algorithm_report.decisions}
    model_lookup = {d.task_id: d for d in model_report.decisions}

    predictions = []
    for t in graph.tasks:
        pred = predict_risk_heuristic(t, algo_lookup.get(t.id), model_lookup.get(t.id))
        predictions.append(pred)

    return RiskReport(predictions=predictions)


# Add to pipeline.py
from verification_model import verify_output_ensemble
from verification_rules import rule_based_verification
from schema import VerificationReport, VerificationIssue


def verify_output(task_id: str, task_description: str, output: str) -> VerificationReport:
    ensemble = verify_output_ensemble(task_id, task_description, output)

    issues_1 = [VerificationIssue(**i) for i in ensemble["pass_1"].get("issues", [])]
    issues_2 = [VerificationIssue(**i) for i in ensemble["pass_2"].get("issues", [])]
    rule_issues = rule_based_verification(output)

    # Agreement score: how much overlap exists between the two LLM passes' categories
    cats_1 = {i.category for i in issues_1}
    cats_2 = {i.category for i in issues_2}
    if not cats_1 and not cats_2:
        agreement = 1.0  # both found nothing — full agreement
    else:
        overlap = len(cats_1 & cats_2)
        total = len(cats_1 | cats_2)
        agreement = round(overlap / total, 2) if total > 0 else 1.0

    severity_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    best_by_category = {}
    for issue in issues_1 + issues_2 + rule_issues:
        existing = best_by_category.get(issue.category)
        if existing is None or severity_rank[issue.severity] > severity_rank[existing.severity]:
            best_by_category[issue.category] = issue

    merged = list(best_by_category.values())

    passed = not any(i.severity in ("high", "critical") for i in merged)
    # Low agreement between the two independent passes is itself a signal worth
    # escalating, even if neither pass alone found a severe issue.
    requires_human_review = (not passed) or (agreement < 0.5 and (issues_1 or issues_2))

    return VerificationReport(
        task_id=task_id,
        passed=passed,
        issues=merged,
        verifier_agreement=agreement,
        requires_human_review=requires_human_review
    )

# Add to pipeline.py
from reputation_model import update_reputation, get_all_reputation_scores


def record_task_outcome(model_decision, task, verification_report=None, human_override: bool = None):
    """
    Call this once a task's real outcome is known. Feeds Model 8 from three
    possible signals, matching your architecture's Human Trust Calibration idea:
    - verification_report.passed (automated signal from Model 7)
    - human_override (explicit human accept=True / reject=False, if given — takes priority)
    """
    if human_override is not None:
        succeeded = human_override
    elif verification_report is not None:
        succeeded = verification_report.passed
    else:
        return  # no signal available, nothing to record

    update_reputation(model_decision.chosen_model, task.type, succeeded)



# Add to pipeline.py (this consolidates everything into one entry point)

def run_full_pipeline(requirement: str, user_stack: dict = None, risk_tolerance: float = 0.5):
    """
    The complete Verya pipeline, Models 1-8, in sequence.
    Returns a single dict with every stage's output, ready for a dashboard or demo UI.
    """
    result = {"requirement": requirement}

    # Model 1: Workflow Understanding
    graph = get_valid_workflow(requirement)
    result["workflow"] = graph

    # Model 2: Flaw Detection
    flaw_report = get_flaw_report(graph)
    result["flaws"] = flaw_report

    if not flaw_report.is_safe_to_proceed:
        result["halted_at"] = "flaw_detection"
        result["halt_reason"] = "Critical or high-severity architectural flaws found before execution."
        return result

    # Model 3: Stack Recommendation / Validation
    stack_result = decide_stack(graph, user_stack)
    result["stack"] = stack_result

    if stack_result["mode"] == "validated" and not stack_result["report"].is_compatible:
        result["halted_at"] = "stack_validation"
        result["halt_reason"] = "User-supplied stack has critical/high compatibility issues."
        return result

    # Model 4: Algorithm Recommendation
    algo_report = decide_algorithms(graph, requirement)
    result["algorithms"] = algo_report

    # Model 5: AI Model Router (now reputation-aware via Model 8)
    model_report = decide_ai_models(graph, algo_report, risk_tolerance=risk_tolerance)
    result["model_routing"] = model_report

    # Model 6: Failure/Risk Prediction
    risk_report = predict_risks(graph, algo_report, model_report)
    result["risk"] = risk_report

    # Flag any task whose predicted risk crosses a threshold, for visibility
    high_risk_tasks = [p for p in risk_report.predictions if p.failure_probability >= 0.5]
    result["high_risk_tasks"] = high_risk_tasks

    # NOTE: Model 7 (Output Verification) and Model 8 (Reputation update) run
    # AFTER actual execution happens — Verya doesn't execute code itself yet,
    # so these two are called separately once an output exists. See
    # verify_and_record() below for that step.

    result["halted_at"] = None
    result["summary"] = {
        "total_tasks": len(graph.tasks),
        "flaws_found": len(flaw_report.flaws),
        "algorithm_decisions_needing_human": sum(1 for d in algo_report.decisions if d.requires_human_tiebreak),
        "model_decisions_needing_human": sum(1 for d in model_report.decisions if d.requires_human_tiebreak),
        "high_risk_task_count": len(high_risk_tasks),
    }

    return result


def verify_and_record(task_id: str, task_description: str, task_type: str, chosen_model: str, output: str):
    """
    Call this once actual output exists for a task (Model 7 + Model 8 together).
    This is the step that closes the loop back into the Reputation Economy.
    """
    verification_report = verify_output(task_id, task_description, output)
    update_reputation(chosen_model, task_type, verification_report.passed)
    return verification_report