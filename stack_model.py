import os
import json
from groq import Groq
from dotenv import load_dotenv
from schema import StackRecommendation, StackValidationReport, WorkflowGraph
from prompts import STACK_RECOMMENDATION_PROMPT, STACK_VALIDATION_PROMPT

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def recommend_stack(graph: WorkflowGraph) -> StackRecommendation:
    tasks_summary = "\n".join(
        f"- {t.name} ({t.type}): {t.description}" for t in graph.tasks
    )
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": STACK_RECOMMENDATION_PROMPT + "\nRespond with ONLY valid JSON."},
            {"role": "user", "content": f"Tasks:\n{tasks_summary}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )
    raw = response.choices[0].message.content
    return StackRecommendation(**json.loads(raw))


def validate_stack(graph: WorkflowGraph, user_stack: dict) -> StackValidationReport:
    tasks_summary = "\n".join(
        f"- {t.name} ({t.type}): {t.description}" for t in graph.tasks
    )
    stack_summary = json.dumps(user_stack)
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
    return StackValidationReport(**json.loads(raw))