import json

from router_model import select_model
from schema import Task


def test_router_uses_local_catalog_without_gateway(monkeypatch):
    monkeypatch.delenv("MODEL_ROUTER_ENDPOINT", raising=False)
    task = Task(id="t1", name="Build API", type="backend", description="Implement a REST API")

    decision = select_model(task)

    assert decision.chosen_provider != "groq"
    assert decision.chosen_model


def test_router_accepts_gateway_model(monkeypatch):
    monkeypatch.setenv("MODEL_ROUTER_ENDPOINT", "https://router.invalid/v1/route")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"chosen_model": "deepseek-chat", "reasoning": "Best for code"}).encode()

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())
    task = Task(id="t1", name="Build API", type="backend", description="Implement a REST API")

    decision = select_model(task)

    assert decision.chosen_model == "deepseek-chat"
    assert decision.chosen_provider == "deepseek"


def test_router_ignores_malformed_gateway_response(monkeypatch):
    monkeypatch.setenv("MODEL_ROUTER_ENDPOINT", "https://router.invalid/v1/route")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"not-json"

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())
    task = Task(id="t1", name="Build API", type="backend", description="Implement a REST API")

    decision = select_model(task)

    assert decision.chosen_model
    assert decision.chosen_provider != ""
