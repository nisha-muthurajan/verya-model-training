from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

from process_mining import detect_event_log_flaws
from prompts import FLAW_DETECTION_PROMPT
from rules import rule_based_checks
from schema import Flaw, FlawReport, WorkflowGraph

load_dotenv()


def _providers() -> list[dict]:
    raw = os.getenv("FLAW_MODEL_ENDPOINTS", "[]")
    try:
        providers = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("FLAW_MODEL_ENDPOINTS must be a JSON array") from error
    if not isinstance(providers, list):
        raise ValueError("FLAW_MODEL_ENDPOINTS must be a JSON array")
    return [provider for provider in providers if provider.get("url") and provider.get("model")]


def _call_provider(provider: dict, graph_json: str) -> list[Flaw]:
    request_body = json.dumps({
        "model": provider["model"],
        "messages": [
            {"role": "system", "content": FLAW_DETECTION_PROMPT + "\nReturn only valid JSON."},
            {"role": "user", "content": f"Task graph:\n{graph_json}"},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }).encode()
    headers = {"Content-Type": "application/json"}
    api_key = provider.get("api_key") or os.getenv(provider.get("api_key_env", ""), "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(provider["url"], data=request_body, headers=headers)
    with urllib.request.urlopen(request, timeout=provider.get("timeout", 30)) as response:
        payload = json.loads(response.read().decode())
    content = payload["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    raw_flaws = parsed.get("flaws", [])
    if not isinstance(raw_flaws, list):
        return []
    return [Flaw(**item) for item in raw_flaws if isinstance(item, dict)]


def _deduplicate(flaws: list[Flaw]) -> list[Flaw]:
    unique: dict[tuple, Flaw] = {}
    severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    for flaw in flaws:
        key = (tuple(sorted(flaw.task_ids)), flaw.type)
        existing = unique.get(key)
        if existing is None or severity_rank[flaw.severity] > severity_rank[existing.severity]:
            unique[key] = flaw
    return list(unique.values())


def detect_flaws(graph: WorkflowGraph, event_log_path: str | None = None) -> FlawReport:
    graph_json = graph.model_dump_json()
    flaws = rule_based_checks(graph)
    flaws.extend(detect_event_log_flaws(event_log_path, graph))

    provider_results = 0
    for provider in _providers():
        try:
            flaws.extend(_call_provider(provider, graph_json))
            provider_results += 1
        except (KeyError, TypeError, ValueError, urllib.error.URLError, TimeoutError):
            continue

    deduplicated = _deduplicate(flaws)
    return FlawReport(
        flaws=deduplicated,
        is_safe_to_proceed=not any(flaw.severity in ("high", "critical") for flaw in deduplicated),
    )
