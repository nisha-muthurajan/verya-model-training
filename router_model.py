import json
import math
import os
import urllib.error
import urllib.request

from schema import ModelSelectionDecision, ModelCandidate, Task
from model_catalog import get_catalog
from complexity_scorer import compute_complexity, score_to_required_tier

UTILITY_GAP_THRESHOLD = 0.05  # how close two models' scores must be to even be "close"


from reputation_model import compute_trust_score


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


def _normalize_catalog(catalog: object) -> list[dict]:
    if not isinstance(catalog, list):
        return []

    normalized = []
    for model in catalog:
        if not isinstance(model, dict):
            continue
        name = model.get("name")
        provider = model.get("provider")
        if not isinstance(name, str) or not name.strip() or not isinstance(provider, str) or not provider.strip():
            continue
        cost_tier = model.get("cost_tier")
        capability_tier = model.get("capability_tier")
        if isinstance(cost_tier, bool) or isinstance(capability_tier, bool):
            continue
        try:
            cost_tier = int(cost_tier)
            capability_tier = int(capability_tier)
        except (TypeError, ValueError):
            continue
        if not 1 <= cost_tier <= 4 or not 1 <= capability_tier <= 3:
            continue
        normalized.append({
            **model,
            "name": name.strip(),
            "provider": provider.strip(),
            "cost_tier": cost_tier,
            "capability_tier": capability_tier,
        })
    return normalized


def _model_candidate(model: dict) -> ModelCandidate:
    return ModelCandidate(
        name=model["name"],
        provider=model["provider"],
        cost_tier=model["cost_tier"],
        capability_tier=model["capability_tier"],
    )


def _external_route(task, catalog, required_tier, risk_tolerance):
    endpoint = os.getenv("MODEL_ROUTER_ENDPOINT", "").strip()
    if not endpoint:
        return None

    payload = json.dumps({
        "task": {
            "id": task.id,
            "name": task.name,
            "type": task.type,
            "description": task.description,
        },
        "required_capability_tier": required_tier,
        "risk_tolerance": risk_tolerance,
        "candidate_models": catalog,
    }).encode()
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("MODEL_ROUTER_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(endpoint, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw_result = response.read()
        if not raw_result.strip():
            return None
        result = json.loads(raw_result.decode())
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
        chosen_name = result.get("chosen_model") or result.get("model")
        chosen = next((model for model in catalog if model["name"] == chosen_name), None)
        if not chosen:
            return None
        reasoning = result.get("reasoning", "Selected by the configured model router.")
        if not isinstance(reasoning, str) or not reasoning.strip():
            reasoning = "Selected by the configured model router."
        return chosen, reasoning.strip()
    except (KeyError, TypeError, UnicodeDecodeError, ValueError, urllib.error.URLError, TimeoutError):
        return None


def select_model(task, algorithm_confidence=None, requires_tiebreak=False, risk_tolerance=0.5):
    normalized_risk_tolerance = _normalize_risk_tolerance(risk_tolerance)
    score, breakdown = compute_complexity(
        task,
        algorithm_confidence,
        requires_tiebreak,
        normalized_risk_tolerance,
    )
    required_tier = score_to_required_tier(score)
    breakdown["required_capability_tier"] = required_tier
    breakdown["risk_tolerance_used"] = normalized_risk_tolerance

    catalog = _normalize_catalog(get_catalog())
    if not catalog:
        raise ValueError("model catalog contains no valid candidates")

    # Primary pool: only models at EXACTLY the tier this task needs — the
    # cheapest-sufficient model lives here, and it can't be out-competed by
    # a more expensive, more capable model just because it's "efficient."
    same_tier = [m for m in catalog if m["capability_tier"] == required_tier]
    higher_tier = [m for m in catalog if m["capability_tier"] > required_tier]
    if not same_tier:
        same_tier = [m for m in catalog if m["capability_tier"] >= required_tier] or catalog

    # Only pay for extra headroom above the required tier when risk_tolerance
    # explicitly asks for it (high setting = "give me margin for safety").
    pool = same_tier + higher_tier if normalized_risk_tolerance > 0.65 else same_tier

    routed = _external_route(task, pool, required_tier, normalized_risk_tolerance)
    if routed:
        chosen, routed_reasoning = routed
        alternatives = [
            _model_candidate(model)
            for model in pool if model["name"] != chosen["name"]
        ][:2]
        return ModelSelectionDecision(
            task_id=task.id,
            chosen_model=chosen["name"],
            chosen_provider=chosen["provider"],
            required_capability_tier=required_tier,
            reasoning=f"Configured router selected this model: {routed_reasoning}",
            confidence=0.8,
            alternatives_considered=alternatives,
            requires_human_tiebreak=False,
            complexity_breakdown=breakdown,
        )

    max_cost = max(m["cost_tier"] for m in catalog)
    max_cap = max(m["capability_tier"] for m in catalog)

    def utility(m):
        cap_score = m["capability_tier"] / max_cap
        cost_penalty = m["cost_tier"] / max_cost
        rep = compute_trust_score(m["name"], task.type)
        rep_weight = 0.3 if rep.confidence_level != "unproven" else 0.0
        base = (normalized_risk_tolerance * cap_score) - ((1 - normalized_risk_tolerance) * cost_penalty)
        return base + (rep_weight * (rep.trust_score - 0.5))

    ranked = sorted(pool, key=lambda m: (-utility(m), m["cost_tier"], m["name"], m["provider"]))
    chosen = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None

    tiebreak_needed = False
    if runner_up:
        gap = abs(utility(chosen) - utility(runner_up))
        task_is_uncertain = requires_tiebreak or (algorithm_confidence is not None and algorithm_confidence < 0.6)
        tiebreak_needed = gap < 0.05 and task_is_uncertain

    confidence = round(1.0 - (0.15 if tiebreak_needed else 0.0), 2)
    reasoning = (
        f"Task complexity score {breakdown['final_score']} -> requires capability tier {required_tier}. "
        f"With risk_tolerance={normalized_risk_tolerance}, {chosen['name']} ({chosen['provider']}) is the cheapest "
        f"model meeting this task's actual requirement."
    )
    alternatives = [
        _model_candidate(m)
        for m in ranked[1:3]
    ]

    return ModelSelectionDecision(
        task_id=task.id, chosen_model=chosen["name"], chosen_provider=chosen["provider"],
        required_capability_tier=required_tier, reasoning=reasoning, confidence=confidence,
        alternatives_considered=alternatives, requires_human_tiebreak=tiebreak_needed,
        complexity_breakdown=breakdown
    )