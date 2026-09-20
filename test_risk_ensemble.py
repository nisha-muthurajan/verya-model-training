from algorithm_model import recommend_algorithms
from model_catalog import get_catalog
from risk_ensemble import RISK_ENGINES, predict_risk_ensemble
from schema import Task


def test_risk_ensemble_works_without_external_services():
    task = Task(
        id="t1",
        name="Payment API",
        type="backend",
        description="Process payment and authorize the transaction",
        depends_on=["t2", "t3"],
    )
    decision = predict_risk_ensemble(task)

    assert len(RISK_ENGINES) == 12
    assert decision.source == "ensemble"
    assert 0 <= decision.failure_probability <= 1
    assert decision.severity_if_failed in {"low", "medium", "high", "critical"}


def test_catalog_no_longer_depends_on_groq():
    assert all(candidate["provider"] != "groq" for candidate in get_catalog())
