from schema import RiskPrediction
from risk_features import extract_features, HIGH_RISK_KEYWORDS

TYPE_BASE_RISK = {"frontend": 0.05, "auth": 0.15, "database": 0.1, "backend": 0.12,
                   "ml": 0.25, "infra": 0.15, "integration": 0.2}


def predict_risk_heuristic(task, algo_decision=None, model_decision=None) -> RiskPrediction:
    features = extract_features(task, algo_decision, model_decision)

    score = TYPE_BASE_RISK.get(features["task_type"], 0.1)
    risk_factors = []

    if features["contains_high_risk_keyword"]:
        score += 0.2
        risk_factors.append("task involves a high-stakes operation (security/payment/admin-related)")

    if features["algorithm_confidence"] < 0.65:
        score += 0.15
        risk_factors.append(f"low confidence in chosen algorithm ({features['algorithm_confidence']})")

    if features["algorithm_required_tiebreak"]:
        score += 0.1
        risk_factors.append("algorithm selection required human tiebreak")

    if features["model_confidence"] < 0.7:
        score += 0.1
        risk_factors.append(f"low confidence in chosen AI model ({features['model_confidence']})")

    if features["num_dependencies"] >= 3:
        score += 0.1
        risk_factors.append(f"high dependency count ({features['num_dependencies']}) increases cascade-failure risk")

    score = min(score, 1.0)

    if score >= 0.7:
        severity = "critical"
    elif score >= 0.5:
        severity = "high"
    elif score >= 0.25:
        severity = "medium"
    else:
        severity = "low"

    if not risk_factors:
        risk_factors.append("no significant risk signals detected")

    return RiskPrediction(
        task_id=task.id,
        failure_probability=round(score, 2),
        risk_factors=risk_factors,
        severity_if_failed=severity,
        source="heuristic"
    )