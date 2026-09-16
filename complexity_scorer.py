from schema import Task

HIGH_STAKES_KEYWORDS = ["payment", "security", "auth", "delete", "admin", "compliance", "medical", "financial"]


def compute_complexity(task: Task, algorithm_confidence: float = None, requires_tiebreak: bool = False) -> tuple[float, dict]:
    """
    Returns (score 0-1, breakdown dict explaining the score).
    Higher score = needs a more capable (and likely costlier) model.
    """
    breakdown = {}
    score = 0.0

    # Signal 1: task type baseline weight
    type_weights = {"frontend": 0.15, "auth": 0.4, "database": 0.3, "backend": 0.35, "ml": 0.6, "infra": 0.3, "integration": 0.4}
    type_score = type_weights.get(task.type, 0.3)
    breakdown["task_type_weight"] = type_score
    score += type_score * 0.35

    # Signal 2: high-stakes keyword presence
    text = f"{task.name} {task.description}".lower()
    is_high_stakes = any(k in text for k in HIGH_STAKES_KEYWORDS)
    breakdown["high_stakes_keywords_found"] = is_high_stakes
    if is_high_stakes:
        score += 0.3

    # Signal 3: inherited uncertainty from Model 4 (Algorithm Recommendation)
    if algorithm_confidence is not None:
        uncertainty = 1 - algorithm_confidence
        breakdown["algorithm_uncertainty"] = round(uncertainty, 2)
        score += uncertainty * 0.2

    # Signal 4: if the algorithm stage already flagged this for human review, 
    # the model executing it should also be a stronger one
    if requires_tiebreak:
        breakdown["algorithm_flagged_tiebreak"] = True
        score += 0.15

    # Signal 5: dependency fan-in — tasks many others depend on are higher-stakes
    breakdown["depends_on_count"] = len(task.depends_on)

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