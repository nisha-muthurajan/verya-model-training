import os
import json
try:
    from groq import Groq
except ImportError:
    Groq = None
from dotenv import load_dotenv
from schema import StackRecommendation, StackValidationIssue, StackValidationReport, WorkflowGraph
from prompts import STACK_RECOMMENDATION_PROMPT, STACK_VALIDATION_PROMPT
from stack_ensemble import recommend_stack_ensemble

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def _provider_warning(message: str) -> StackValidationReport:
    return StackValidationReport(
        issues=[StackValidationIssue(
            category="infra",
            issue=message,
            severity="medium",
            suggested_alternative="Configure a working stack-validation provider and review the stack manually.",
        )],
        is_compatible=True,
    )


def _validate_user_stack(user_stack: object) -> None:
    if not isinstance(user_stack, dict) or not user_stack:
        raise ValueError("user_stack must be a non-empty dictionary")
    for key, value in user_stack.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("user_stack component names must be non-empty strings")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("user_stack component values must be non-empty strings")


def recommend_stack(graph: WorkflowGraph) -> StackRecommendation:
    return recommend_stack_ensemble(graph.tasks)


def validate_stack(graph: WorkflowGraph, user_stack: dict) -> StackValidationReport:
    _validate_user_stack(user_stack)
    if client is None:
        return _provider_warning("Stack validation provider is not configured; compatibility was not fully checked.")
    tasks_summary = "\n".join(
        f"- {t.name} ({t.type}): {t.description}" for t in graph.tasks
    )
    stack_summary = json.dumps(user_stack)
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": STACK_VALIDATION_PROMPT + "\nRespond with ONLY valid JSON."},
                {"role": "user", "content": f"Tasks:\n{tasks_summary}\n\nUser stack: {stack_summary}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        raw = response.choices[0].message.content
        if not isinstance(raw, str) or not raw.strip():
            return _provider_warning("Stack validation provider returned an empty response.")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return _provider_warning("Stack validation provider returned an unexpected response.")
        return StackValidationReport(**payload)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return _provider_warning("Stack validation provider returned an invalid response.")
    except Exception:
        return _provider_warning("Stack validation provider could not be reached.")