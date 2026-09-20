from complexity_scorer import compute_complexity
from schema import Task


def test_uncertain_algorithm_inputs_raise_complexity_and_preserve_breakdown():
    task = Task(id="t1", name="Employee lookup", type="backend", description="Look up employee records")

    score, breakdown = compute_complexity(
        task,
        algorithm_confidence=0.4,
        requires_tiebreak=True,
        risk_tolerance=0.5,
    )

    assert score > 0.35
    assert breakdown["algorithm_uncertainty"] == 0.6
    assert breakdown["algorithm_flagged_tiebreak"] is True
    assert breakdown["risk_tolerance_used"] == 0.5