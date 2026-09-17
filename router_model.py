import json
import os
import urllib.error
import urllib.request

from schema import ModelSelectionDecision, ModelCandidate, Task
from model_catalog import get_catalog
from complexity_scorer import compute_complexity, score_to_required_tier

UTILITY_GAP_THRESHOLD = 0.05  # how close two models' scores must be to even be "close"


from reputation_model import compute_trust_score


def _external_route(task, catalog, required_tier, risk_tolerance):
    endpoint = os.getenv("MODEL_ROUTER_ENDPOINT")
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
            result = json.loads(response.read().decode())
        if "choices" in result:
            content = result["choices"][0]["message"]["content"]
            result = json.loads(content)
        chosen_name = result.get("chosen_model") or result.get("model")
        chosen = next((model for model in catalog if model["name"] == chosen_name), None)
        if not chosen:
            return None
        return chosen, result.get("reasoning", "Selected by the configured model router.")
    except (KeyError, TypeError, ValueError, urllib.error.URLError, TimeoutError):
        return None

def select_model(task, algorithm_confidence=None, requires_tiebreak=False, risk_tolerance=0.5):
    score, breakdown = compute_complexity(task, algorithm_confidence, requires_tiebreak)
    required_tier = score_to_required_tier(score)
    breakdown["required_capability_tier"] = required_tier
    breakdown["risk_tolerance_used"] = risk_tolerance

    catalog = get_catalog()

    # Primary pool: only models at EXACTLY the tier this task needs — the
    # cheapest-sufficient model lives here, and it can't be out-competed by
    # a more expensive, more capable model just because it's "efficient."
    same_tier = [m for m in catalog if m["capability_tier"] == required_tier]
    higher_tier = [m for m in catalog if m["capability_tier"] > required_tier]
    if not same_tier:
        same_tier = [m for m in catalog if m["capability_tier"] >= required_tier] or catalog

    # Only pay for extra headroom above the required tier when risk_tolerance
    # explicitly asks for it (high setting = "give me margin for safety").
    pool = same_tier + higher_tier if risk_tolerance > 0.65 else same_tier

    routed = _external_route(task, pool, required_tier, risk_tolerance)
    if routed:
        chosen, routed_reasoning = routed
        alternatives = [
            ModelCandidate(name=model["name"], provider=model["provider"], cost_tier=model["cost_tier"], capability_tier=model["capability_tier"])
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
        base = (risk_tolerance * cap_score) - ((1 - risk_tolerance) * cost_penalty)
        return base + (rep_weight * (rep.trust_score - 0.5))

    ranked = sorted(pool, key=lambda m: (-utility(m), m["cost_tier"]))
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
        f"With risk_tolerance={risk_tolerance}, {chosen['name']} ({chosen['provider']}) is the cheapest "
        f"model meeting this task's actual requirement."
    )
    alternatives = [
        ModelCandidate(name=m["name"], provider=m["provider"], cost_tier=m["cost_tier"], capability_tier=m["capability_tier"])
        for m in ranked[1:3]
    ]

    return ModelSelectionDecision(
        task_id=task.id, chosen_model=chosen["name"], chosen_provider=chosen["provider"],
        required_capability_tier=required_tier, reasoning=reasoning, confidence=confidence,
        alternatives_considered=alternatives, requires_human_tiebreak=tiebreak_needed,
        complexity_breakdown=breakdown
    )

    def utility(m):
        cap_score = m["capability_tier"] / max_cap
        cost_penalty = m["cost_tier"] / max_cost
        rep = compute_trust_score(m["name"], task.type)
        # Only let reputation meaningfully sway the decision once it's not "unproven" —
        # this prevents a single unlucky early failure from permanently tanking a model.
        rep_weight = 0.3 if rep.confidence_level != "unproven" else 0.0
        base_utility = (risk_tolerance * cap_score) - ((1 - risk_tolerance) * cost_penalty)
        return base_utility + (rep_weight * (rep.trust_score - 0.5))

    ranked = sorted(eligible, key=lambda m: (-utility(m), m["cost_tier"]))
    chosen = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None

    # Only escalate to a human if the top two models are genuinely close
    # AND the task itself already carried real uncertainty upstream.
    tiebreak_needed = False
    if runner_up:
        utility_gap = abs(utility(chosen) - utility(runner_up))
        genuinely_close = utility_gap < UTILITY_GAP_THRESHOLD
        task_is_uncertain = requires_tiebreak or (algorithm_confidence is not None and algorithm_confidence < 0.6)
        tiebreak_needed = genuinely_close and task_is_uncertain

    confidence = round(1.0 - (0.15 if tiebreak_needed else 0.0), 2)

    reasoning = (
        f"Task complexity score {breakdown['final_score']} -> requires capability tier {required_tier}. "
        f"With risk_tolerance={risk_tolerance} (0=cost-first, 1=capability-first), "
        f"{chosen['name']} ({chosen['provider']}) offers the best balance of cost (tier {chosen['cost_tier']}) "
        f"and capability (tier {chosen['capability_tier']}) among eligible models."
    )

    alternatives = [
        ModelCandidate(name=m["name"], provider=m["provider"], cost_tier=m["cost_tier"], capability_tier=m["capability_tier"])
        for m in ranked[1:3]
    ]

    return ModelSelectionDecision(
        task_id=task.id,
        chosen_model=chosen["name"],
        chosen_provider=chosen["provider"],
        required_capability_tier=required_tier,
        reasoning=reasoning,
        confidence=confidence,
        alternatives_considered=alternatives,
        requires_human_tiebreak=tiebreak_needed,
        complexity_breakdown=breakdown
    )