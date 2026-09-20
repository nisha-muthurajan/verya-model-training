import json

from workflow_ensemble import _normalize_provider_config, _parse_provider_configs, understand_workflow_ensemble


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({
            "choices": [{"message": {"content": json.dumps({"tasks": self.content})}}]
        }).encode()


def test_workflow_calls_all_configured_providers(monkeypatch):
    monkeypatch.setenv("WORKFLOW_MODEL_ENDPOINTS", json.dumps([
        {"url": "https://one.invalid", "model": "model-one"},
        {"url": "https://two.invalid", "model": "model-two"},
    ]))
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        tasks = [
            {"id": "t1", "name": "Student Records", "type": "database", "description": "Store students", "depends_on": []},
            {"id": "t2", "name": "Attendance API", "type": "backend", "description": "Record attendance", "depends_on": ["t1"]},
        ]
        return FakeResponse(tasks)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    graph = understand_workflow_ensemble("Build any unusual workflow")

    assert len(calls) == 2
    assert [task.name for task in graph.tasks] == ["Student Records", "Attendance API"]


def test_workflow_require_api_fails_without_valid_response(monkeypatch):
    monkeypatch.setenv("WORKFLOW_MODEL_ENDPOINTS", "[]")
    monkeypatch.setenv("WORKFLOW_REQUIRE_API", "true")

    try:
        understand_workflow_ensemble("Build an arbitrary app")
    except RuntimeError as error:
        assert "No valid workflow model response" in str(error)
    else:
        raise AssertionError("strict API mode should reject local fallback")


def test_workflow_provider_config_filters_invalid_entries():
    assert _normalize_provider_config({"url": " https://example.invalid ", "model": " model ", "timeout": "15"})["timeout"] == 15.0
    assert _normalize_provider_config({"url": "https://example.invalid", "model": "model", "protocol": " OPENAI-COMPATIBLE "})["protocol"] == "openai"
    assert _normalize_provider_config({"url": "", "model": "model"}) is None
    assert _normalize_provider_config({"url": "https://example.invalid", "model": "", "timeout": 0}) is None
    assert _normalize_provider_config({"url": "https://example.invalid", "model": "model", "protocol": "unknown"}) is None

    providers = _parse_provider_configs(json.dumps([
        {"url": "https://valid.invalid", "model": "valid"},
        {"url": "https://missing-model.invalid"},
        "malformed",
    ]))
    assert [provider["model"] for provider in providers] == ["valid"]
