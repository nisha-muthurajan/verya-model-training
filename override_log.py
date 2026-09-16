# override_log.py
import json
from datetime import datetime

LOG_FILE = "overrides.jsonl"


def log_override(task_id: str, original_model: str, overridden_to: str, reason: str = ""):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "task_id": task_id,
        "original_model": original_model,
        "overridden_to": overridden_to,
        "reason": reason
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")