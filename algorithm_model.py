import os
import json
from groq import Groq
from dotenv import load_dotenv
from schema import AlgorithmReport, WorkflowGraph
from prompts import ALGORITHM_RECOMMENDATION_PROMPT
from algorithm_filter import tasks_needing_algorithm_decision
from ml_problem_classifier import classify_ml_problem_type
from ml_algorithm_model import recommend_ml_algorithm

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def _general_algorithm_recommendation(tasks, original_requirement):
    """Existing path — handles backend/database tasks (non-ML)."""
    if not tasks:
        return []

    tasks_summary = "\n".join(
        f"- {t.id}: {t.name} ({t.type}) — {t.description}" for t in tasks
    )
    messages = [
        {"role": "system", "content": ALGORITHM_RECOMMENDATION_PROMPT + "\nRespond with ONLY valid JSON."},
        {"role": "user", "content": f"Original requirement: {original_requirement}\n\nTasks:\n{tasks_summary}"}
    ]
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0
        )
    except Exception as error:
        if not error.__class__.__name__ in {"BadRequestError", "UnprocessableEntityError"}:
            raise
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages + [{"role": "user", "content": "Return a single valid JSON object only. Do not use markdown or trailing commas."}],
            temperature=0
        )
    raw = response.choices[0].message.content
    payload = json.loads(raw)
    payload["decisions"] = [
        decision for decision in payload.get("decisions", [])
        if isinstance(decision, dict)
    ]
    for decision in payload["decisions"]:
        decision["source"] = "general"
        decision["problem_type"] = ""
    report = AlgorithmReport(**payload)
    return report.decisions


def recommend_algorithms(graph: WorkflowGraph, original_requirement: str) -> AlgorithmReport:
    relevant_tasks = tasks_needing_algorithm_decision(graph)

    ml_tasks = [t for t in relevant_tasks if t.type == "ml"]
    general_tasks = [t for t in relevant_tasks if t.type != "ml"]

    # Path 1: general algorithm decisions (backend/database)
    general_decisions = _general_algorithm_recommendation(general_tasks, original_requirement)

    # Path 2: specialized ML benchmark-grounded decisions
    ml_decisions = []
    for t in ml_tasks:
        problem_type = classify_ml_problem_type(t.name, t.description, original_requirement)
        decision = recommend_ml_algorithm(t.id, t.description, problem_type, original_requirement)
        ml_decisions.append(decision)

    # Merge both into one unified report
    return AlgorithmReport(decisions=general_decisions + ml_decisions)