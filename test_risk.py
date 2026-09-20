# test_risk.py
from risk_ensemble import predict_risk_ensemble
from schema import Task


def test_risk_prediction_is_bounded_and_deterministic():
    task = Task(
        id="t1",
        name="Payment API",
        type="backend",
        description="Process payment and authorize the transaction",
        depends_on=["t2", "t3"],
    )

    first = predict_risk_ensemble(task)
    second = predict_risk_ensemble(task)

    assert first.model_dump() == second.model_dump()
    assert 0 <= first.failure_probability <= 1
    assert first.severity_if_failed in {"low", "medium", "high", "critical"}