import json
import os

STORE_FILE = "reputation_store.json"


def _load_store() -> dict:
    if not os.path.exists(STORE_FILE):
        return {}
    with open(STORE_FILE, "r") as f:
        return json.load(f)


def _save_store(store: dict):
    with open(STORE_FILE, "w") as f:
        json.dump(store, f, indent=2)


def _key(model_name: str, task_type: str) -> str:
    return f"{model_name}::{task_type}"


def get_raw_counts(model_name: str, task_type: str) -> tuple[int, int]:
    """Returns (successes, failures). Defaults to (0, 0) if never seen before."""
    store = _load_store()
    entry = store.get(_key(model_name, task_type), {"successes": 0, "failures": 0})
    return entry["successes"], entry["failures"]


def record_outcome(model_name: str, task_type: str, succeeded: bool):
    store = _load_store()
    key = _key(model_name, task_type)
    entry = store.get(key, {"successes": 0, "failures": 0})
    if succeeded:
        entry["successes"] += 1
    else:
        entry["failures"] += 1
    store[key] = entry
    _save_store(store)


def get_all_scores() -> dict:
    return _load_store()