import os, json
from groq import Groq
from dotenv import load_dotenv
from schema import AlgorithmDecision
from ml_benchmark_kb import get_relevant_benchmarks

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

ML_ALGORITHM_PROMPT = """You are Verya's ML Algorithm Selection engine. You choose the best 
ML/DL algorithm for a task, using ONLY the provided benchmark knowledge base — do not invent 
algorithms or stats not listed.

Rules:
- Choose from the given benchmark candidates only.
- Base your choice on stated constraints (latency, memory, accuracy priority, hardware, budget). 
  If none given, assume moderate constraints and say so in assumed_constraints.
- If two candidates are close in suitability, or constraints were assumed, set confidence below 
  0.65 and requires_human_tiebreak=true.
- Return JSON: {"chosen_algorithm": "...", "reasoning": "...", "confidence": 0.0, 
  "alternatives_considered": [{"name":"...","pros":"...","cons":"..."}], 
  "requires_human_tiebreak": true/false, "assumed_constraints": "..."}
"""

def recommend_ml_algorithm(task_id: str, task_description: str, problem_type: str, constraints: str = "") -> AlgorithmDecision:
    candidates = get_relevant_benchmarks(problem_type)
    candidates_text = json.dumps(candidates, indent=2)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": ML_ALGORITHM_PROMPT + "\nRespond with ONLY valid JSON."},
            {"role": "user", "content": f"Task: {task_description}\nProblem type: {problem_type}\nConstraints: {constraints or 'none stated'}\n\nAvailable benchmarked candidates:\n{candidates_text}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    raw = response.choices[0].message.content
    data = json.loads(raw)
    data["task_id"] = task_id
    data["problem_type"] = problem_type
    data["source"] = "ml_benchmark"
    return AlgorithmDecision(**data)