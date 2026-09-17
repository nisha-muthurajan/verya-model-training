import os
import json
from groq import Groq
from dotenv import load_dotenv
from schema import VerificationIssue
from prompts import OUTPUT_VERIFICATION_PROMPT

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def _run_single_verifier(task_description: str, output: str, temperature: float) -> dict:
    prompt = OUTPUT_VERIFICATION_PROMPT.format(task_description=task_description, output=output)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": prompt + "\nRespond with ONLY valid JSON."},
            {"role": "user", "content": "Review the output above."}
        ],
        response_format={"type": "json_object"},
        temperature=temperature
    )
    return json.loads(response.choices[0].message.content)


def verify_output_ensemble(task_id: str, task_description: str, output: str) -> dict:
    """
    Runs two independent verification passes at different temperatures — this is our
    ensemble: same model, two independent 'opinions', reducing the chance a single
    pass misses something due to one particular reasoning path.
    """
    if client is None:
        from verification_rules import rule_based_verification

        issues = [issue.model_dump(mode="json") for issue in rule_based_verification(output)]
        result = {"issues": issues, "passed": not issues}
        return {"pass_1": result, "pass_2": result}

    pass_1 = _run_single_verifier(task_description, output, temperature=0.1)
    pass_2 = _run_single_verifier(task_description, output, temperature=0.6)

    return {"pass_1": pass_1, "pass_2": pass_2}