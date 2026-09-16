from schema import ReputationScore
from reputation_store import get_raw_counts, record_outcome, get_all_scores

# Prior belief: before any evidence, assume a middling 50/50 chance,
# but weighted as if we'd already seen 2 successes and 2 failures.
# This is what prevents "1 success = 100% trust" from a single lucky run.
PRIOR_ALPHA = 2
PRIOR_BETA = 2


def compute_trust_score(model_name: str, task_type: str) -> ReputationScore:
    successes, failures = get_raw_counts(model_name, task_type)

    alpha = PRIOR_ALPHA + successes
    beta = PRIOR_BETA + failures
    trust_score = alpha / (alpha + beta)  # Bayesian mean estimate

    total = successes + failures
    if total < 5:
        confidence_level = "unproven"
    elif total < 20:
        confidence_level = "emerging"
    else:
        confidence_level = "established"

    return ReputationScore(
        model_name=model_name,
        task_type=task_type,
        trust_score=round(trust_score, 3),
        successes=successes,
        failures=failures,
        total_observations=total,
        confidence_level=confidence_level
    )


def update_reputation(model_name: str, task_type: str, succeeded: bool):
    record_outcome(model_name, task_type, succeeded)


def get_all_reputation_scores() -> list[ReputationScore]:
    store = get_all_scores()
    scores = []
    for key in store:
        model_name, task_type = key.split("::")
        scores.append(compute_trust_score(model_name, task_type))
    return scores