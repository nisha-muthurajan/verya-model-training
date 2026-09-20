from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from schema import AlgorithmCandidate, AlgorithmDecision, Task
from ml_benchmark_kb import get_relevant_benchmarks


@dataclass(frozen=True)
class SelectorProfile:
    name: str
    focus: str
    weight: float


# These profiles capture the selection criteria used by the listed tools. They are
# advisory profiles because Model 4 receives a task graph, not a training dataset.
SELECTOR_PROFILES = (
    SelectorProfile("KidML", "beginner-friendly problem framing", 1.0),
    SelectorProfile("scikit-learn", "classical algorithms and validation", 1.2),
    SelectorProfile("Auto-sklearn", "automated preprocessing and model search", 1.0),
    SelectorProfile("TPOT", "pipeline and hyperparameter optimization", 1.0),
    SelectorProfile("FLAML", "fast, low-cost tabular  search", 1.1),
    SelectorProfile("PyCaret", "rapid baseline comparison", 0.9),
    SelectorProfile("H2O AutoML", "broad tabular leaderboard and ensembles", 1.0),
    SelectorProfile("MLJAR Supervised", "explainable AutoML reports", 0.9),
    SelectorProfile("KNIME", "visual workflow experimentation", 0.8),
    SelectorProfile("Google Colab", "reproducible hosted experimentation", 0.8),
)


def _source_summary() -> str:
    return ", ".join(profile.name for profile in SELECTOR_PROFILES)


def _candidate(name: str, pros: str, cons: str) -> AlgorithmCandidate:
    return AlgorithmCandidate(name=name, pros=pros, cons=cons)


def _general_candidates(task: Task) -> list[AlgorithmCandidate]:
    text = f"{task.name} {task.description}".lower()
    if any(word in text for word in ("search", "catalog", "keyword", "text")):
        return [
            _candidate("Inverted index", "Fast keyword lookup and relevance ranking", "Requires index maintenance and storage"),
            _candidate("B-tree index", "Simple filtering and range queries", "Less suitable for full-text relevance"),
            _candidate("Trie", "Fast prefix matching", "Poor fit for arbitrary multi-term search"),
        ]
    if any(word in text for word in ("cart", "session", "lookup", "cache")):
        return [
            _candidate("Hash table with optimistic concurrency", "Fast key-based access with conflict detection", "Needs durable persistence and retry handling"),
            _candidate("B-tree indexed relational table", "Durable transactions and flexible queries", "More overhead for simple key lookups"),
            _candidate("Append-only log with snapshots", "Recoverable writes and efficient replay", "More complex compaction and reads"),
        ]
    if any(word in text for word in ("order", "payment", "checkout")):
        return [
            _candidate("Idempotent state machine", "Makes retries safe across payment and order states", "Requires explicit state-transition rules"),
            _candidate("Serializable transaction", "Strong consistency for related records", "Can reduce throughput under contention"),
            _candidate("Event log with projection", "Durable audit trail and replayable state", "Adds eventual-consistency complexity"),
        ]
    if task.type == "database":
        return [
            _candidate("B-tree indexes with ACID transactions", "Reliable point, range, and relational access", "Write overhead grows with index count"),
            _candidate("LSM tree", "High write throughput", "Reads and compaction require tuning"),
            _candidate("Hash index", "Fast equality lookups", "Not suitable for range queries"),
        ]
    return [
        _candidate("Validated iterative implementation", "Keeps behavior simple and testable", "Needs profiling before optimization"),
        _candidate("Queue-backed worker", "Handles bursty asynchronous work", "Adds operational and retry complexity"),
        _candidate("Batch processing", "Efficient for high-volume workloads", "Not appropriate for strict real-time latency"),
    ]


def recommend_general_algorithm(task: Task, requirement: str) -> AlgorithmDecision:
    candidates = _general_candidates(task)
    return AlgorithmDecision(
        task_id=task.id,
        chosen_algorithm=candidates[0].name,
        reasoning=(
            f"Selected by the local consensus profiles ({_source_summary()}) for {task.type} work. "
            f"The task text favors {candidates[0].name}; the remaining candidates are retained for comparison."
        ),
        confidence=0.72,
        alternatives_considered=candidates[1:],
        requires_human_tiebreak=False,
        assumed_constraints=f"No runtime dataset or benchmark was supplied; requirement: {requirement}",
        source="ensemble",
        problem_type="",
    )


def recommend_ml_algorithm(
    task: Task, problem_type: str, requirement: str
) -> AlgorithmDecision:
    benchmark_candidates = get_relevant_benchmarks(problem_type)
    if not benchmark_candidates:
        return recommend_general_algorithm(task, requirement)

    text = f"{task.name} {task.description} {requirement}".lower()
    scored = []
    for index, candidate in enumerate(benchmark_candidates):
        score = 0.0
        if "explain" in text or "interpretabl" in text:
            score += 2.0 if "regression" in candidate["name"].lower() or "logistic" in candidate["name"].lower() else 0.0
        if "large" in text or "million" in text:
            score += 1.5 if "lightgbm" in candidate["name"].lower() else 0.0
        if "latency" in text or "fast" in text or "real-time" in text:
            score += 1.0 if candidate.get("inference") in {"instant", "very fast"} else 0.0
        score += max(0.0, 1.0 - index * 0.1)
        scored.append((score, candidate))

    scored.sort(key=lambda item: item[0], reverse=True)
    chosen = scored[0][1]
    alternatives = [
        _candidate(item["name"], item.get("notes", ""), f"Trade-offs: accuracy={item.get('accuracy', 'unknown')}, inference={item.get('inference', 'unknown')}")
        for _, item in scored[1:]
    ]
    confidence = 0.68 if len(scored) == 1 or scored[0][0] - scored[1][0] > 0.8 else 0.58
    return AlgorithmDecision(
        task_id=task.id,
        chosen_algorithm=chosen["name"],
        reasoning=(
            f"Consensus profile selected this benchmarked candidate for {problem_type}. "
            f"The selector profiles are: {_source_summary()}."
        ),
        confidence=confidence,
        alternatives_considered=alternatives,
        requires_human_tiebreak=confidence < 0.65,
        assumed_constraints=f"No training data or measured benchmark was supplied; requirement: {requirement}",
        source="ensemble",
        problem_type=problem_type,
    )


def recommend_ensemble(tasks: Iterable[Task], requirement: str) -> list[AlgorithmDecision]:
    decisions = []
    for task in tasks:
        if task.type not in {"backend", "database", "ml"}:
            continue
        if task.type == "ml":
            problem_type = "classification_tabular"
            decisions.append(recommend_ml_algorithm(task, problem_type, requirement))
        else:
            decisions.append(recommend_general_algorithm(task, requirement))
    return decisions
