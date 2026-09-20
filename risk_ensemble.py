from __future__ import annotations

import json
import math
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


def _normalize_probability(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        probability = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(probability):
        return None
    return min(max(probability, 0.0), 1.0)


def _normalize_provider(provider: object) -> dict | None:
    if not isinstance(provider, dict):
        return None
    url = provider.get("url")
    model = provider.get("model")
    if not isinstance(url, str) or not url.strip() or not isinstance(model, str) or not model.strip():
        return None

    timeout = provider.get("timeout", 30)
    if isinstance(timeout, bool):
        return None
    try:
        timeout = float(timeout)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(timeout) or timeout <= 0:
        return None

    name = provider.get("name", model)
    if not isinstance(name, str) or not name.strip():
        name = model
    api_key = provider.get("api_key", "")
    api_key_env = provider.get("api_key_env", "")
    if api_key is None:
        api_key = ""
    if api_key_env is None:
        api_key_env = ""
    if not isinstance(api_key, str) or not isinstance(api_key_env, str):
        return None

    return {
        "name": name.strip(),
        "url": url.strip(),
        "model": model.strip(),
        "timeout": timeout,
        "api_key": api_key.strip(),
        "api_key_env": api_key_env.strip(),
    }


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
            raw_probability = model.predict_proba([features])[0][1]
        else:
            raw_probability = model.predict([features])[0]
        return _normalize_probability(raw_probability)
    except (ImportError, OSError, TypeError, ValueError, IndexError, AttributeError):
        return None


def _event_log_signal(event_log_path: str | None) -> float | None:
    if not isinstance(event_log_path, (str, os.PathLike)) or not str(event_log_path).strip():
        return None
    try:
        import pm4py
        path = Path(event_log_path)
        if not path.is_file():
            return None
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
        counts = [len(cases) for cases in variants.values()]
        total = sum(counts)
        if total <= 0:
            return None
        dominant = max(counts)
        return _normalize_probability(round(1.0 - dominant / total, 2))
    except (ImportError, OSError, ValueError, KeyError, TypeError, ZeroDivisionError):
        return None


def _llm_probability(provider: dict, task, features: list[float]) -> tuple[float, str] | None:
    try:
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
        request = urllib.request.Request(provider["url"], data=payload, headers=headers)
        with urllib.request.urlopen(request, timeout=provider.get("timeout", 30)) as response:
            raw_response = response.read()
        if not raw_response or not raw_response.strip():
            return None
        result = json.loads(raw_response.decode())
        if not isinstance(result, dict):
            return None
        if "choices" in result:
            choices = result["choices"]
            if not isinstance(choices, list) or not choices:
                return None
            message = choices[0].get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                return None
            result = json.loads(message["content"])
            if not isinstance(result, dict):
                return None
        probability = _normalize_probability(result.get("failure_probability"))
        if probability is None:
            return None
        reason = result.get("reason", "LLM risk analysis")
        if not isinstance(reason, str) or not reason.strip():
            reason = "LLM risk analysis"
        return probability, reason.strip()
    except (KeyError, TypeError, UnicodeDecodeError, ValueError, urllib.error.URLError, TimeoutError):
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
    baseline_probability = _normalize_probability(baseline.failure_probability)
    signals = [baseline_probability if baseline_probability is not None else 0.0]
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
        normalized_provider = _normalize_provider(provider)
        if normalized_provider is None:
            continue
        result = _llm_probability(normalized_provider, task, features)
        if result is not None:
            probability, reason = result
            normalized_probability = _normalize_probability(probability)
            if normalized_probability is None:
                continue
            signals.append(normalized_probability)
            factors.append(f"{normalized_provider['name']}: {reason}")

    probability = round(sum(signals) / len(signals), 2)
    return RiskPrediction(
        task_id=task.id,
        failure_probability=probability,
        risk_factors=factors or ["no significant risk signals detected"],
        severity_if_failed=_severity(probability),
        source="ensemble",
    )
