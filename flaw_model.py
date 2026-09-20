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


class _ProviderResponseError(ValueError):
    """A safe description of a malformed flaw-provider response."""


def _providers() -> list[dict]:
    raw = os.getenv("FLAW_MODEL_ENDPOINTS", "[]")
    try:
        providers = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("FLAW_MODEL_ENDPOINTS must be a JSON array") from error
    if not isinstance(providers, list):
        raise ValueError("FLAW_MODEL_ENDPOINTS must be a JSON array")
    return [
        provider
        for provider in providers
        if isinstance(provider, dict)
        and isinstance(provider.get("url"), str)
        and provider["url"].strip()
        and isinstance(provider.get("model"), str)
        and provider["model"].strip()
    ]


def _decode_provider_payload(raw_body: bytes) -> dict:
    if not raw_body or not raw_body.strip():
        raise _ProviderResponseError("empty response body")
    try:
        payload = json.loads(raw_body.decode())
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _ProviderResponseError("response body was not valid JSON") from error
    if not isinstance(payload, dict):
        raise _ProviderResponseError("response JSON must be an object")
    return payload


def _extract_provider_content(payload: dict) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise _ProviderResponseError(
            "response did not contain expected chat completion content"
        ) from error
    if not isinstance(content, str) or not content.strip():
        raise _ProviderResponseError("response content was missing or invalid")
    return content


def _parse_provider_flaws(content: str) -> list[Flaw]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as error:
        raise _ProviderResponseError("provider content was not valid JSON") from error
    if not isinstance(parsed, dict) or "flaws" not in parsed:
        raise _ProviderResponseError("response did not contain a flaws list")
    raw_flaws = parsed["flaws"]
    if not isinstance(raw_flaws, list):
        raise _ProviderResponseError("response flaws field was not a list")

    flaws = []
    invalid_items = 0
    for item in raw_flaws:
        if not isinstance(item, dict):
            invalid_items += 1
            continue
        try:
            flaws.append(Flaw(**item))
        except (TypeError, ValueError):
            invalid_items += 1
    if invalid_items:
        print(f"  [Flaw API] skipped {invalid_items} malformed flaw item(s)")
    return flaws


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
        payload = _decode_provider_payload(response.read())
    content = _extract_provider_content(payload)
    return _parse_provider_flaws(content)


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
    for provider_index, provider in enumerate(_providers(), start=1):
        try:
            flaws.extend(_call_provider(provider, graph_json))
            provider_results += 1
        except urllib.error.HTTPError as error:
            print(f"  [Flaw API] provider {provider_index}: HTTP {error.code}")
            continue
        except _ProviderResponseError as error:
            print(f"  [Flaw API] provider {provider_index}: {error}")
            continue
        except (KeyError, TypeError, ValueError, urllib.error.URLError, TimeoutError):
            print(f"  [Flaw API] provider {provider_index}: invalid provider response")
            continue

    deduplicated = _deduplicate(flaws)
    return FlawReport(
        flaws=deduplicated,
        is_safe_to_proceed=not any(flaw.severity in ("high", "critical") for flaw in deduplicated),
    )
