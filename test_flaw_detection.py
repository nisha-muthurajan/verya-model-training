import json

import pytest

from flaw_model import _call_provider, _ProviderResponseError
from rules import rule_based_checks
from schema import Task, WorkflowGraph


def test_sensitive_backend_requires_authentication_ancestor():
    graph = WorkflowGraph(tasks=[
        Task(id="t1", name="Authentication", type="auth", description="Validate users"),
        Task(id="t2", name="Session Gateway", type="backend", description="Create sessions", depends_on=["t1"]),
        Task(id="t3", name="Order API", type="backend", description="Create orders", depends_on=["t2"]),
    ])

    assert rule_based_checks(graph) == []


def test_missing_authentication_is_reported_for_sensitive_backend():
    graph = WorkflowGraph(tasks=[
        Task(id="t1", name="Payment API", type="backend", description="Capture payments"),
    ])

    findings = rule_based_checks(graph)

    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert "no Authentication task exists" in findings[0].description


def test_hyphenated_post_processing_is_not_a_sensitive_post_operation():
    graph = WorkflowGraph(tasks=[
        Task(id="t1", name="Batch Worker", type="backend", description="Run post-processing"),
    ])

    assert rule_based_checks(graph) == []


@pytest.mark.parametrize("body", [b"", b"not-json", b'{"choices": []}'])
def test_flaw_provider_rejects_malformed_responses(monkeypatch, body):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return body

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(_ProviderResponseError):
        _call_provider({"url": "https://provider.invalid", "model": "flaw-model"}, "{}")


def test_flaw_provider_preserves_valid_items_and_skips_malformed_items(monkeypatch):
    body = json.dumps({
        "choices": [{"message": {"content": json.dumps({
            "flaws": [
                {"task_ids": ["t1"], "type": "security", "severity": "high", "description": "Unsafe", "suggested_fix": "Fix"},
                {"task_ids": [], "type": "invalid", "severity": "unknown"},
            ]
        })}}]
    }).encode()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return body

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())

    flaws = _call_provider({"url": "https://provider.invalid", "model": "flaw-model", "api_key": "secret"}, "{}")

    assert len(flaws) == 1
    assert flaws[0].severity == "high"