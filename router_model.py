from schema import ModelSelectionDecision, ModelCandidate, Task
from model_catalog import get_catalog
from complexity_scorer import compute_complexity, score_to_required_tier

UTILITY_GAP_THRESHOLD = 0.05  # how close two models' scores must be to even be "close"


from reputation_model import compute_trust_score

def select_model(task, algorithm_confidence=None, requires_tiebreak=False, risk_tolerance=0.5):
    score, breakdown = compute_complexity(task, algorithm_confidence, requires_tiebreak)
    required_tier = score_to_required_tier(score)
    breakdown["required_capability_tier"] = required_tier
    breakdown["risk_tolerance_used"] = risk_tolerance

    catalog = get_catalog()
    eligible = [m for m in catalog if m["capability_tier"] >= required_tier]
    if not eligible:
        eligible = catalog

    max_cost = max(m["cost_tier"] for m in catalog)
    max_cap = max(m["capability_tier"] for m in catalog)

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