import os
import json
from groq import Groq
from dotenv import load_dotenv
from schema import FlawReport, WorkflowGraph
from prompts import FLAW_DETECTION_PROMPT

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def detect_flaws(graph: WorkflowGraph) -> FlawReport:
    graph_json = graph.model_dump_json()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": FLAW_DETECTION_PROMPT + "\nRespond with ONLY valid JSON."},
            {"role": "user", "content": f"Task graph:\n{graph_json}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    raw = response.choices[0].message.content
    return FlawReport(**json.loads(raw))