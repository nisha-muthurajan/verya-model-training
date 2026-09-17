from __future__ import annotations

from pathlib import Path

from schema import Flaw, WorkflowGraph


def detect_event_log_flaws(event_log_path: str | None, graph: WorkflowGraph) -> list[Flaw]:
    """Analyze an optional CSV/XES event log when PM4Py is installed.

    Expected CSV columns are case_id, activity, and timestamp. XES files are
    supported through PM4Py's native importer. Event-log findings are advisory;
    graph rules remain the source of structural guarantees.
    """
    if not event_log_path:
        return []

    try:
        import pm4py
    except ImportError:
        return []

    path = Path(event_log_path)
    if not path.exists():
        return []

    if path.suffix.lower() == ".xes":
        log = pm4py.read_xes(str(path))
    elif path.suffix.lower() == ".csv":
        log = pm4py.format_dataframe(
            pm4py.read_csv(str(path)),
            case_id="case_id",
            activity_key="activity",
            timestamp_key="timestamp",
        )
    else:
        raise ValueError("Event logs must be CSV or XES files")

    discovered = pm4py.discover_process_tree_inductive(log)
    variants = pm4py.get_variants_as_tuples(log)
    if not variants:
        return []

    most_common = max(variants.values(), key=len)
    outliers = sum(len(cases) for variant, cases in variants.items() if variant != most_common)
    if outliers == 0:
        return []

    known_ids = {task.id for task in graph.tasks}
    affected = [task.id for task in graph.tasks if task.name.lower() in {step.lower() for step in most_common}]
    if not affected:
        affected = list(known_ids)[:1]

    return [Flaw(
        task_ids=affected,
        type="logic",
        severity="medium",
        description=f"Process mining found {outliers} case(s) on a path different from the dominant discovered process tree.",
        suggested_fix="Inspect the variant cases for rework, skipped controls, or undocumented exception paths and update the workflow model.",
    )]
