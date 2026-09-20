import math

from workflow_model import understand_workflow
from validate import validate_graph
from flaw_model import detect_flaws
from stack_model import recommend_stack, validate_stack
from stack_rules import rule_based_stack_checks
from algorithm_model import recommend_algorithms
from schema import (
    AlgorithmReport,
    FlawReport,
    RiskReport,
    StackValidationIssue,
    StackValidationReport,
)



def _normalize_requirement(requirement: object) -> str:
    if not isinstance(requirement, str) or not requirement.strip():
        raise ValueError("requirement must be a non-empty string")
    return requirement.strip()


def _normalize_retry_count(value: object) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError("max_retries must be a non-negative integer")
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        raise ValueError("max_retries must be a non-negative integer") from None
    return max(normalized, 0)


def _normalize_risk_tolerance(value: object) -> float:
    if isinstance(value, bool) or value is None:
        return 0.5
    if isinstance(value, str) and not value.strip():
        return 0.5
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(normalized):
        return 0.5
    return min(max(normalized, 0.0), 1.0)


def _empty_flaw_report() -> FlawReport:
    return FlawReport(flaws=[], is_safe_to_proceed=True)


def get_valid_workflow(requirement: str, max_retries: int = 2):
    """Model 1: requirement -> validated task graph"""
    requirement = _normalize_requirement(requirement)
    max_retries = _normalize_retry_count(max_retries)
    last_errors = []
    for attempt in range(max_retries + 1):
        prompt = requirement
        if last_errors:
            prompt += f"\n\nYour previous attempt had these problems, fix them: {last_errors}"
        try:
            graph = understand_workflow(prompt)
            errors = validate_graph(graph)
        except Exception:
            errors = ["workflow generation or validation failed"]
        if not errors:
            return graph
        last_errors = errors
    raise ValueError(f"Could not produce valid graph after {max_retries + 1} attempts: {last_errors}")


def get_flaw_report(graph, event_log_path=None):
    try:
        report = detect_flaws(graph, event_log_path=event_log_path)
    except Exception:
        return _empty_flaw_report()
    return report if isinstance(report, FlawReport) else _empty_flaw_report()


def decide_algorithms(graph, original_requirement: str):
    """Recommend algorithms for the graph's ML and algorithm-sensitive tasks."""
    try:
        report = recommend_algorithms(graph, original_requirement)
    except Exception:
        return AlgorithmReport(decisions=[])
    return report if isinstance(report, AlgorithmReport) else AlgorithmReport(decisions=[])




def decide_stack(graph, user_stack: dict = None):
    if user_stack:
        try:
            llm_report = validate_stack(graph, user_stack)
        except Exception:
            llm_report = StackValidationReport(
                issues=[StackValidationIssue(
                    category="infra",
                    issue="Stack validation could not be completed; review the supplied stack manually.",
                    severity="medium",
                    suggested_alternative="Retry stack validation with an available provider.",
                )],
                is_compatible=True,
            )
        if not isinstance(llm_report, StackValidationReport):
            llm_report = StackValidationReport(
                issues=[StackValidationIssue(
                    category="infra",
                    issue="Stack validation returned an incomplete result; review the supplied stack manually.",
                    severity="medium",
                    suggested_alternative="Retry stack validation with an available provider.",
                )],
                is_compatible=True,
            )
        try:
            rule_issues = rule_based_stack_checks(graph, user_stack)
        except Exception:
            rule_issues = []
        if not isinstance(rule_issues, list):
            rule_issues = []
        rule_issues = [issue for issue in rule_issues if isinstance(issue, StackValidationIssue)]

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
    decisions = []
    algo_decisions = getattr(algorithm_report, "decisions", [])
    if not isinstance(algo_decisions, list):
        algo_decisions = []
    algo_lookup = {
        d.task_id: d
        for d in algo_decisions
        if all(hasattr(d, field) for field in ("task_id", "confidence", "requires_human_tiebreak"))
    }
    normalized_risk_tolerance = _normalize_risk_tolerance(risk_tolerance)

    for t in graph.tasks:
        algo_decision = algo_lookup.get(t.id)
        algo_confidence = algo_decision.confidence if algo_decision else None
        needs_tiebreak = algo_decision.requires_human_tiebreak if algo_decision else False

        try:
            decision = select_model(
                t,
                algorithm_confidence=algo_confidence,
                requires_tiebreak=needs_tiebreak,
                risk_tolerance=normalized_risk_tolerance,
            )
        except Exception:
            continue
        if decision is not None:
            decisions.append(decision)

    return ModelSelectionReport(decisions=decisions)


# Add to pipeline.py
from risk_ensemble import predict_risk_ensemble
from schema import RiskReport


def predict_risks(graph, algorithm_report, model_report, event_log_path=None):
    algo_decisions = getattr(algorithm_report, "decisions", [])
    model_decisions = getattr(model_report, "decisions", [])
    algo_lookup = {d.task_id: d for d in algo_decisions if hasattr(d, "task_id")}
    model_lookup = {d.task_id: d for d in model_decisions if hasattr(d, "task_id")}

    predictions = []
    for t in graph.tasks:
        try:
            pred = predict_risk_ensemble(
                t, algo_lookup.get(t.id), model_lookup.get(t.id), event_log_path=event_log_path
            )
        except Exception:
            continue
        if pred is not None:
            predictions.append(pred)

    return RiskReport(predictions=predictions)


# Add to pipeline.py
from verification_model import verify_output_ensemble
from verification_rules import rule_based_verification
from schema import VerificationReport, VerificationIssue


def verify_output(task_id: str, task_description: str, output: str) -> VerificationReport:
    try:
        ensemble = verify_output_ensemble(task_id, task_description, output)
    except Exception:
        ensemble = {}

    if not isinstance(ensemble, dict):
        ensemble = {}

    def parse_issues(pass_result):
        if not isinstance(pass_result, dict) or not isinstance(pass_result.get("issues", []), list):
            return []
        issues = []
        for raw_issue in pass_result["issues"]:
            if not isinstance(raw_issue, dict):
                continue
            try:
                issues.append(VerificationIssue(**raw_issue))
            except (TypeError, ValueError):
                continue
        return issues

    issues_1 = parse_issues(ensemble.get("pass_1"))
    issues_2 = parse_issues(ensemble.get("pass_2"))
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
        if existing is None or severity_rank.get(issue.severity, 0) > severity_rank.get(existing.severity, 0):
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
    if model_decision is None or task is None:
        return
    if human_override is not None:
        succeeded = human_override
    elif verification_report is not None:
        succeeded = verification_report.passed
    else:
        return  # no signal available, nothing to record

    update_reputation(model_decision.chosen_model, task.type, succeeded)



# Add to pipeline.py (this consolidates everything into one entry point)

def run_full_pipeline(requirement: str, user_stack: dict = None, risk_tolerance: float = 0.5, event_log_path=None):
    """
    The complete Verya pipeline, Models 1-8, in sequence.
    Returns a single dict with every stage's output, ready for a dashboard or demo UI.
    """
    requirement = _normalize_requirement(requirement)
    normalized_risk_tolerance = _normalize_risk_tolerance(risk_tolerance)
    result = {"requirement": requirement}

    # Model 1: Workflow Understanding
    graph = get_valid_workflow(requirement)
    result["workflow"] = graph

    # Model 2: Flaw Detection
    flaw_report = get_flaw_report(graph, event_log_path=event_log_path)
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
    model_report = decide_ai_models(graph, algo_report, risk_tolerance=normalized_risk_tolerance)
    result["model_routing"] = model_report

    # Model 6: Failure/Risk Prediction
    risk_report = predict_risks(graph, algo_report, model_report, event_log_path=event_log_path)
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