from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from risk_features import extract_features
from risk_heuristic import predict_risk_heuristic
from schema import RiskPrediction


RISK_ENGINES = (
    "NASA ProgPy",
    "scikit-learn",
    "XGBoost",
    "LightGBM",
    "PyTorch/TensorFlow",
    "lifelines/scikit-survival",
    "PM4Py",
    "Predictive Maintenance MCP",
    "ChatGPT-class models",
    "Claude",
    "DeepSeek",
    "Kimi K3",
)


def _numeric_features(task, algorithm_decision, model_decision) -> list[float]:
    features = extract_features(task, algorithm_decision, model_decision)
    return [
        float(features["num_dependencies"]),
        float(features["contains_high_risk_keyword"]),
        float(features["name_length"]),
        float(features["description_length"]),
        float(features["algorithm_confidence"]),
        float(features["algorithm_required_tiebreak"]),
        float(features["num_alternatives_considered"]),
        float(features["assumed_constraints"]),
        float(features["model_confidence"]),
        float(features["model_required_tiebreak"]),
        float(features["required_capability_tier"]),
    ]


def _trained_model_probability(features: list[float]) -> float | None:
    model_path = os.getenv("RISK_MODEL_PATH")
    if not model_path or not Path(model_path).exists():
        return None
    try:
        import joblib
        model = joblib.load(model_path)
        if hasattr(model, "predict_proba"):
            return float(model.predict_proba([features])[0][1])
        return float(model.predict([features])[0])
    except (ImportError, OSError, ValueError, IndexError, AttributeError):
        return None


def _event_log_signal(event_log_path: str | None) -> float | None:
    if not event_log_path or not Path(event_log_path).exists():
        return None
    try:
        import pm4py
        path = Path(event_log_path)
        if path.suffix.lower() == ".xes":
            log = pm4py.read_xes(str(path))
        elif path.suffix.lower() == ".csv":
            log = pm4py.format_dataframe(
                pm4py.read_csv(str(path)),
                case_id="case_id",
                activity_key="activity",
                timestamp_key="timestamp",
            )
        else:
            return None
        variants = pm4py.get_variants_as_tuples(log)
        if not variants:
            return 0.0
        total = sum(len(cases) for cases in variants.values())
        dominant = max(len(cases) for cases in variants.values())
        return round(1.0 - dominant / total, 2)
    except (ImportError, OSError, ValueError, KeyError, TypeError):
        return None


def _llm_probability(provider: dict, task, features: list[float]) -> tuple[float, str] | None:
    payload = json.dumps({
        "model": provider["model"],
        "messages": [
            {"role": "system", "content": "Analyze workflow failure risk. Return only JSON: {\"failure_probability\": 0.0, \"reason\": \"...\"}."},
            {"role": "user", "content": json.dumps({"task": task.model_dump(), "features": features})},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }).encode()
    headers = {"Content-Type": "application/json"}
    api_key = provider.get("api_key") or os.getenv(provider.get("api_key_env", ""), "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        request = urllib.request.Request(provider["url"], data=payload, headers=headers)
        with urllib.request.urlopen(request, timeout=provider.get("timeout", 30)) as response:
            result = json.loads(response.read().decode())
        if "choices" in result:
            result = json.loads(result["choices"][0]["message"]["content"])
        probability = max(0.0, min(1.0, float(result["failure_probability"])))
        return probability, str(result.get("reason", "LLM risk analysis"))
    except (KeyError, TypeError, ValueError, urllib.error.URLError, TimeoutError):
        return None


def _severity(probability: float) -> str:
    if probability >= 0.7:
        return "critical"
    if probability >= 0.5:
        return "high"
    if probability >= 0.25:
        return "medium"
    return "low"


def predict_risk_ensemble(task, algorithm_decision=None, model_decision=None, event_log_path=None) -> RiskPrediction:
    baseline = predict_risk_heuristic(task, algorithm_decision, model_decision)
    features = _numeric_features(task, algorithm_decision, model_decision)
    signals = [baseline.failure_probability]
    factors = list(baseline.risk_factors)

    trained_probability = _trained_model_probability(features)
    if trained_probability is not None:
        signals.append(trained_probability)
        factors.append("trained scikit-learn/XGBoost/LightGBM model signal")

    process_probability = _event_log_signal(event_log_path)
    if process_probability is not None:
        signals.append(process_probability)
        factors.append("PM4Py process-variant deviation signal")

    raw_providers = os.getenv("RISK_MODEL_ENDPOINTS", "[]")
    try:
        providers = json.loads(raw_providers)
    except json.JSONDecodeError:
        providers = []
    for provider in providers if isinstance(providers, list) else []:
        result = _llm_probability(provider, task, features)
        if result is not None:
            probability, reason = result
            signals.append(probability)
            factors.append(f"{provider.get('name', provider['model'])}: {reason}")

    probability = round(sum(signals) / len(signals), 2)
    return RiskPrediction(
        task_id=task.id,
        failure_probability=probability,
        risk_factors=factors or ["no significant risk signals detected"],
        severity_if_failed=_severity(probability),
        source="ensemble",
    )
