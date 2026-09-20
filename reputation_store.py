import json
import math
import os
import tempfile
from pathlib import Path

STORE_FILE = "reputation_store.json"


def _store_path() -> Path:
    configured_path = os.getenv("REPUTATION_STORE_PATH", "").strip()
    if configured_path:
        return Path(configured_path).expanduser()
    return Path(__file__).resolve().parent / STORE_FILE


def _normalize_count(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    if isinstance(value, float) and math.isfinite(value) and value.is_integer() and value >= 0:
        return int(value)
    return None


def _normalize_entry(entry: object) -> dict[str, int] | None:
    if not isinstance(entry, dict):
        return None
    successes = _normalize_count(entry.get("successes"))
    failures = _normalize_count(entry.get("failures"))
    if successes is None or failures is None:
        return None
    return {"successes": successes, "failures": failures}


def _load_store() -> dict:
    path = _store_path()
    if not path.is_file():
        return {}
    try:
        if path.stat().st_size == 0:
            return {}
        with path.open("r", encoding="utf-8") as file:
            raw_store = json.load(file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(raw_store, dict):
        return {}
    return {
        key: normalized
        for key, entry in raw_store.items()
        if isinstance(key, str)
        and (normalized := _normalize_entry(entry)) is not None
    }


def _save_store(store: dict):
    path = _store_path()
    normalized_store = {
        key: normalized
        for key, entry in store.items()
        if isinstance(key, str)
        and (normalized := _normalize_entry(entry)) is not None
    }
    temporary_path = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(normalized_store, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    except (OSError, TypeError, ValueError) as error:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise RuntimeError("Could not save reputation data") from error


def _key(model_name: str, task_type: str) -> str:
    return f"{model_name}::{task_type}"


def get_raw_counts(model_name: str, task_type: str) -> tuple[int, int]:
    """Returns (successes, failures). Defaults to (0, 0) if never seen before."""
    store = _load_store()
    entry = store.get(_key(model_name, task_type))
    if entry is None:
        return 0, 0
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