from router_model import select_model
from schema import Task


def test_router_selects_from_local_catalog_without_gateway(monkeypatch):
    monkeypatch.delenv("MODEL_ROUTER_ENDPOINT", raising=False)
    task = Task(id="t1", name="Build API", type="backend", description="Implement a REST API")

    decision = select_model(task, risk_tolerance=" 0.1 ")

    assert decision.chosen_model
    assert decision.chosen_provider
    assert decision.complexity_breakdown["risk_tolerance_used"] == 0.1


def test_router_tie_breaking_is_deterministic(monkeypatch):
    monkeypatch.delenv("MODEL_ROUTER_ENDPOINT", raising=False)
    monkeypatch.setattr("router_model.get_catalog", lambda: [
        {"name": "z-model", "provider": "provider", "cost_tier": 1, "capability_tier": 2},
        {"name": "a-model", "provider": "provider", "cost_tier": 1, "capability_tier": 2},
    ])
    task = Task(id="t1", name="Build API", type="backend", description="Implement a REST API")

    assert select_model(task).chosen_model == "a-model"