import os
import json
from groq import Groq
from dotenv import load_dotenv
from schema import WorkflowGraph
from prompts import SYSTEM_PROMPT

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def understand_workflow(requirement: str) -> WorkflowGraph:
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\nRespond with ONLY valid JSON, no other text."},
            {"role": "user", "content": requirement}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    raw = response.choices[0].message.content
    return WorkflowGraph(**json.loads(raw))