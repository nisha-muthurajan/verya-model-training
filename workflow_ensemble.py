from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT
from schema import Task, WorkflowGraph

load_dotenv()


@dataclass(frozen=True)
class WorkflowAdvisor:
    name: str
    strength: str
    weight: float


WORKFLOW_ADVISORS = (
    WorkflowAdvisor("Kimi K3", "agentic planning and tool-use workflows", 1.2),
    WorkflowAdvisor("GLM-5.2", "reasoning and workflow routing", 1.1),
    WorkflowAdvisor("DeepSeek-V4/V3.2", "coding and automation pipelines", 1.1),
    WorkflowAdvisor("Llama 4.1 Scout", "long workflow documents and RAG", 1.0),
    WorkflowAdvisor("Qwen 3.5", "multilingual enterprise workflows", 1.0),
    WorkflowAdvisor("MiniMax M3/M2.5", "productivity and business processes", 0.9),
    WorkflowAdvisor("Mistral Large 2", "sovereign and compliance-sensitive workflows", 0.9),
    WorkflowAdvisor("DeepSeek R1+", "advanced multi-step reasoning", 1.0),
    WorkflowAdvisor("Llama 4/Llama 3.1", "general-purpose workflow planning", 1.0),
    WorkflowAdvisor("Free-tier proprietary APIs", "hosted workflow experimentation", 0.8),
)


def _normalize_requirement(requirement: str) -> str:
    if not isinstance(requirement, str) or not requirement.strip():
        raise ValueError("workflow requirement must be a non-empty string")
    return requirement.strip()


def _normalize_json_content(content: object) -> str:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("workflow provider returned empty content")
    content = content.strip()
    if content.startswith("```") and content.endswith("```"):
        content = content[3:-3].strip()
        if content.lower().startswith("json"):
            content = content[4:].lstrip()
    if not content:
        raise ValueError("workflow provider returned empty content")
    return content


def _normalize_provider_config(provider: object) -> dict | None:
    if not isinstance(provider, dict):
        return None

    url = provider.get("url")
    model = provider.get("model")
    if not isinstance(url, str) or not url.strip() or not isinstance(model, str) or not model.strip():
        return None

    protocol = provider.get("protocol", "openai")
    if not isinstance(protocol, str):
        return None
    protocol = protocol.strip().lower()
    if protocol in {"openai-compatible", "openai_compatible"}:
        protocol = "openai"
    if protocol not in {"openai", "gemini"}:
        return None

    api_key = provider.get("api_key", "")
    if api_key is None:
        api_key = ""
    elif not isinstance(api_key, str):
        return None

    api_key_env = provider.get("api_key_env", "")
    if api_key_env is None:
        api_key_env = ""
    elif not isinstance(api_key_env, str):
        return None

    timeout = provider.get("timeout", 60)
    if isinstance(timeout, bool):
        return None
    try:
        timeout = float(timeout)
    except (TypeError, ValueError):
        return None
    if timeout <= 0:
        return None

    name = provider.get("name", model)
    if not isinstance(name, str) or not name.strip():
        name = model

    return {
        "name": name.strip(),
        "url": url.strip(),
        "model": model.strip(),
        "protocol": protocol,
        "api_key": api_key.strip(),
        "api_key_env": api_key_env.strip(),
        "timeout": timeout,
    }


def _parse_provider_configs(raw: str) -> list[dict]:
    try:
        providers = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("WORKFLOW_MODEL_ENDPOINTS must be a JSON array") from error

    if not isinstance(providers, list):
        raise ValueError("WORKFLOW_MODEL_ENDPOINTS must be a JSON array")

    return [
        normalized
        for provider in providers
        if (normalized := _normalize_provider_config(provider)) is not None
    ]


def _task(task_id: str, name: str, task_type: str, description: str, depends_on: list[str] | None = None) -> Task:
    return Task(
        id=task_id,
        name=name,
        type=task_type,
        description=description,
        depends_on=depends_on or [],
    )


def _domain_tasks(requirement: str) -> list[Task]:
    requirement = _normalize_requirement(requirement)
    text = requirement.lower()
    tasks = [
        _task("t1", "User Model & Storage", "database", "Store user accounts and application ownership data."),
        _task("t2", "Authentication", "auth", "Handle signup, login, sessions, and token validation.", ["t1"]),
    ]

    if any(word in text for word in ("e-commerce", "ecommerce", "shop", "store", "product", "catalog")):
        tasks.extend([
            _task("t3", "Product Model & Storage", "database", "Store products, prices, categories, and inventory."),
            _task("t4", "Product Catalog API", "backend", "Expose product browsing, filtering, and catalog retrieval.", ["t3"]),
            _task("t5", "Shopping Cart Model & Storage", "database", "Persist user carts and cart items.", ["t1", "t3"]),
            _task("t6", "Cart API", "backend", "Allow authenticated users to add, update, and remove cart items.", ["t5", "t2"]),
            _task("t7", "Payment Integration", "integration", "Authorize and capture payments through an external provider.", ["t2"]),
            _task("t8", "Order Model & Storage", "database", "Persist orders and payment status independently of the provider.", ["t1", "t5"]),
            _task("t9", "Order API", "backend", "Create and retrieve authenticated user orders.", ["t8", "t2"]),
        ])
    elif any(word in text for word in ("blog", "post", "article")):
        tasks.extend([
            _task("t3", "Post Model & Storage", "database", "Store posts, authors, publication state, and timestamps.", ["t1"]),
            _task("t4", "Post API", "backend", "Allow users to create, read, edit, and publish posts.", ["t3", "t2"]),
        ])
    elif any(word in text for word in ("food delivery", "restaurant", "live tracking")):
        tasks.extend([
            _task("t3", "Restaurant Model & Storage", "database", "Store restaurants, menus, availability, and locations."),
            _task("t4", "Restaurant Catalog API", "backend", "Expose restaurant and menu browsing.", ["t3"]),
            _task("t5", "Delivery Order Storage", "database", "Persist delivery orders and status transitions.", ["t1"]),
            _task("t6", "Delivery Order API", "backend", "Create authenticated food orders and update delivery state.", ["t5", "t2"]),
            _task("t7", "Live Tracking Integration", "integration", "Receive and publish courier location updates.", ["t6"]),
        ])
    elif any(word in text for word in ("hr", "leave", "employee")):
        tasks.extend([
            _task("t3", "Employee Model & Storage", "database", "Store employee profiles, teams, and reporting relationships."),
            _task("t4", "Leave Request API", "backend", "Submit and retrieve authenticated leave requests.", ["t3", "t2"]),
            _task("t5", "Approval Workflow", "backend", "Route leave requests to authorized approvers and record decisions.", ["t4", "t2"]),
        ])
    elif any(word in text for word in ("task management", "deadlines", "project management")):
        tasks.extend([
            _task("t3", "Task Model & Storage", "database", "Store tasks, teams, assignments, and deadlines."),
            _task("t4", "Task Management API", "backend", "Create, assign, update, and query tasks for authenticated users.", ["t3", "t2"]),
            _task("t5", "Deadline Notifications", "integration", "Notify assignees about upcoming and missed deadlines.", ["t4"]),
        ])
    else:
        tasks.extend([
            _task("t3", "Application Data Model & Storage", "database", "Persist the core entities required by the application."),
            _task("t4", "Application API", "backend", "Expose the core application operations through authenticated endpoints.", ["t3", "t2"]),
        ])

    tasks.append(_task(f"t{len(tasks) + 1}", "Application Frontend", "frontend", "Provide the user interface for the requested workflows.", [task.id for task in tasks if task.type in {"backend", "integration"}] + ["t2"]))
    return tasks


def _configured_provider_graphs(requirement: str) -> list[WorkflowGraph]:
    requirement = _normalize_requirement(requirement)
    endpoints = os.getenv("WORKFLOW_MODEL_ENDPOINTS", "").strip()
    if not endpoints:
        providers = []
        if os.getenv("GROQ_API_KEY"):
            providers.append({
                "name": "groq",
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
                "api_key_env": "GROQ_API_KEY",
            })
        if os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_API_KEY"):
            providers.append({
                "name": "openai",
                "url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o-mini",
                "api_key_env": "OPENAI_API_KEY" if os.getenv("OPENAI_API_KEY") else "OPEN_AI_API_KEY",
            })
        if os.getenv("GEMINI_API_KEY"):
            providers.append({
                "name": "gemini",
                "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
                "api_key_env": "GEMINI_API_KEY",
                "protocol": "gemini",
            })
        if os.getenv("MINIMAX_API_KEY"):
            providers.append({
                "name": "minimax",
                "url": "https://api.minimax.io/v1/text/chatcompletion_v2",
                "model": os.getenv("MINIMAX_MODEL", "MiniMax-Text-01"),
                "api_key_env": "MINIMAX_API_KEY",
            })
        if os.getenv("ZAI_API_KEY"):
            providers.append({
                "name": "glm",
                "url": "https://api.z.ai/api/paas/v4/chat/completions",
                "model": "glm-4.5",
                "api_key_env": "ZAI_API_KEY",
            })
        return _request_provider_graphs(
            requirement,
            [normalized for provider in providers if (normalized := _normalize_provider_config(provider)) is not None],
        )

    return _request_provider_graphs(requirement, _parse_provider_configs(endpoints))


def _request_provider_graphs(requirement: str, providers: list[dict]) -> list[WorkflowGraph]:
    requirement = _normalize_requirement(requirement)
    votes: list[WorkflowGraph] = []
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        provider = _normalize_provider_config(provider)
        if provider is None:
            continue
        url = provider["url"]
        model = provider["model"]
        api_key = provider.get("api_key") or os.getenv(provider.get("api_key_env", ""), "")
        if provider.get("protocol") == "gemini":
            url = url.format(model=model) + f"?key={api_key}"
            request_body = json.dumps({
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT + "\nReturn only valid JSON. Do not use markdown."}]},
                "contents": [{"parts": [{"text": requirement}]}],
                "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
            }).encode()
            headers = {"Content-Type": "application/json"}
        else:
            request_body = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT + "\nReturn only valid JSON. Do not use markdown."},
                    {"role": "user", "content": requirement},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }).encode()
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(url, data=request_body, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=provider.get("timeout", 60)) as response:
                payload = json.loads(response.read().decode())
            if provider.get("protocol") == "gemini":
                content = payload["candidates"][0]["content"]["parts"][0]["text"]
            else:
                message = payload["choices"][0]["message"]
                content = message["content"]
                if isinstance(content, list):
                    content = "".join(
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in content
                    )
                if not isinstance(content, str):
                    content = str(content)
            content = _normalize_json_content(content)
            graph = WorkflowGraph(**json.loads(content))
            if graph.tasks:
                votes.append(graph)
        except urllib.error.HTTPError as error:
            print(f"  [Workflow API] {provider.get('name', provider['model'])}: HTTP {error.code}")
            continue
        except (KeyError, TypeError, ValueError, urllib.error.URLError, TimeoutError) as error:
            print(f"  [Workflow API] {provider.get('name', provider['model'])}: {error.__class__.__name__} ({error})")
            continue

    return votes


def _graph_signature(graph: WorkflowGraph) -> frozenset[tuple[str, str, tuple[str, ...]]]:
    return frozenset(
        (
            task.name.strip().lower(),
            task.type,
            tuple(sorted(task.depends_on)),
        )
        for task in graph.tasks
    )


def _consensus_graph(votes: list[WorkflowGraph]) -> WorkflowGraph:
    if len(votes) == 1:
        return votes[0]

    signatures = [_graph_signature(graph) for graph in votes]
    scores = []
    for index, signature in enumerate(signatures):
        similarity = sum(
            len(signature & other) / max(len(signature | other), 1)
            for other_index, other in enumerate(signatures)
            if other_index != index
        )
        scores.append(similarity)
    return votes[max(range(len(votes)), key=scores.__getitem__)]


def understand_workflow_ensemble(requirement: str) -> WorkflowGraph:
    requirement = _normalize_requirement(requirement)
    configured_graphs = _configured_provider_graphs(requirement)
    if configured_graphs:
        return _consensus_graph(configured_graphs)
    api_configured = bool(
        os.getenv("WORKFLOW_MODEL_ENDPOINTS")
        or os.getenv("GROQ_API_KEY")
        or os.getenv("ZAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("OPEN_AI_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("MINIMAX_API_KEY")
    )
    require_api = os.getenv("WORKFLOW_REQUIRE_API", "true" if api_configured else "false").strip().lower()
    if require_api == "true":
        raise RuntimeError(
            "No valid workflow model response received. Configure WORKFLOW_MODEL_ENDPOINTS "
            "or set WORKFLOW_REQUIRE_API=false for local development fallback."
        )
    return WorkflowGraph(tasks=_domain_tasks(requirement))


def workflow_source() -> str:
    if any(os.getenv(key) for key in (
        "WORKFLOW_MODEL_ENDPOINTS", "GROQ_API_KEY", "ZAI_API_KEY",
        "OPENAI_API_KEY", "OPEN_AI_API_KEY", "GEMINI_API_KEY", "MINIMAX_API_KEY",
    )):
        return "configured workflow APIs (consensus when multiple providers respond)"
    return "local development fallback (no workflow API configured)"
