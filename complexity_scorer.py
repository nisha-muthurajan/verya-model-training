import math
import re

from schema import Task

HIGH_STAKES_KEYWORDS = [
    "payment", "payments", "security", "auth", "authentication", "authorization",
    "delete", "admin", "compliance", "medical", "financial",
]


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


def _normalize_confidence(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(normalized):
        return None
    return min(max(normalized, 0.0), 1.0)


def _has_high_stakes_keyword(text: str) -> bool:
    return any(
        re.search(rf"\b{re.escape(keyword)}(?:s|es)?\b", text)
        for keyword in HIGH_STAKES_KEYWORDS
    )


def compute_complexity(
    task: Task,
    algorithm_confidence: float = None,
    requires_tiebreak: bool = False,
    risk_tolerance: object = 0.5,
) -> tuple[float, dict]:
    """
    Returns (score 0-1, breakdown dict explaining the score).
    Higher score = needs a more capable (and likely costlier) model.
    """
    breakdown = {}
    score = 0.0
    normalized_risk_tolerance = _normalize_risk_tolerance(risk_tolerance)

    # Signal 1: task type baseline weight
    type_weights = {"frontend": 0.15, "auth": 0.4, "database": 0.3, "backend": 0.35, "ml": 0.6, "infra": 0.3, "integration": 0.4}
    raw_task_type = getattr(task, "type", "")
    task_type = raw_task_type.strip().lower() if isinstance(raw_task_type, str) else ""
    type_score = type_weights.get(task_type, 0.3)
    breakdown["task_type_weight"] = type_score
    score += type_score * 0.35

    # Signal 2: high-stakes keyword presence
    raw_task_name = getattr(task, "name", "")
    raw_task_description = getattr(task, "description", "")
    task_name = raw_task_name if isinstance(raw_task_name, str) else ""
    task_description = raw_task_description if isinstance(raw_task_description, str) else ""
    text = f"{task_name} {task_description}".strip().lower()
    is_high_stakes = _has_high_stakes_keyword(text)
    breakdown["high_stakes_keywords_found"] = is_high_stakes
    if is_high_stakes:
        score += 0.3

    # Signal 3: inherited uncertainty from Model 4 (Algorithm Recommendation)
    normalized_confidence = _normalize_confidence(algorithm_confidence)
    if normalized_confidence is not None:
        uncertainty = 1 - normalized_confidence
        breakdown["algorithm_uncertainty"] = round(uncertainty, 2)
        score += uncertainty * 0.2

    # Signal 4: if the algorithm stage already flagged this for human review, 
    # the model executing it should also be a stronger one
    if requires_tiebreak is True:
        breakdown["algorithm_flagged_tiebreak"] = True
        score += 0.15

    # Signal 5: upstream dependencies increase coordination and failure risk.
    raw_dependencies = getattr(task, "depends_on", ())
    dependencies = raw_dependencies if isinstance(raw_dependencies, (list, tuple, set)) else ()
    dependency_count = len(dependencies)
    dependency_risk = min(dependency_count * 0.05, 0.2)
    dependency_risk *= 0.5 + (0.5 * normalized_risk_tolerance)
    breakdown["depends_on_count"] = dependency_count
    breakdown["dependency_risk"] = round(dependency_risk, 2)
    breakdown["risk_tolerance_used"] = normalized_risk_tolerance
    score += dependency_risk

    score = min(score, 1.0)
    breakdown["final_score"] = round(score, 2)
    return score, breakdown


def score_to_required_tier(score: float) -> int:
    if score < 0.35:
        return 1  # simple
    elif score < 0.7:
        return 2  # moderate
    else:
        return 3  # complex / high-stakes