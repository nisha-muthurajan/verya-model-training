from schema import Task, AlgorithmDecision, ModelSelectionDecision

HIGH_RISK_KEYWORDS = ["payment", "delete", "admin", "security", "auth", "compliance", "medical", "financial"]


def extract_features(task: Task, algo_decision: AlgorithmDecision = None,
                      model_decision: ModelSelectionDecision = None) -> dict:
    """
    Every signal here is something we ALREADY have from Models 1, 4, and 5 —
    no new api calls needed. This is what makes Phase 2 training cheap:
    the features already exist in your pipeline's own output.
    """
    text = f"{task.name} {task.description}".lower()

    features = {
        "task_type": task.type,
        "num_dependencies": len(task.depends_on),
        "contains_high_risk_keyword": int(any(k in text for k in HIGH_RISK_KEYWORDS)),
        "name_length": len(task.name),
        "description_length": len(task.description),
    }

    if algo_decision:
        features["algorithm_confidence"] = algo_decision.confidence
        features["algorithm_required_tiebreak"] = int(algo_decision.requires_human_tiebreak)
        features["num_alternatives_considered"] = len(algo_decision.alternatives_considered)
        features["assumed_constraints"] = int(bool(algo_decision.assumed_constraints))
    else:
        features["algorithm_confidence"] = 1.0
        features["algorithm_required_tiebreak"] = 0
        features["num_alternatives_considered"] = 0
        features["assumed_constraints"] = 0

    if model_decision:
        features["model_confidence"] = model_decision.confidence
        features["model_required_tiebreak"] = int(model_decision.requires_human_tiebreak)
        features["required_capability_tier"] = model_decision.required_capability_tier
    else:
        features["model_confidence"] = 1.0
        features["model_required_tiebreak"] = 0
        features["required_capability_tier"] = 1

    return features