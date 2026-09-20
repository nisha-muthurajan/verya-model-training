from __future__ import annotations

from pathlib import Path

from schema import Flaw, WorkflowGraph


def _report_event_log_issue(message: str) -> None:
    print(f"  [Process mining] {message}")


def _load_event_log(path: Path, pm4py):
    suffix = path.suffix.lower()
    if suffix not in {".csv", ".xes"}:
        _report_event_log_issue("event log must be a CSV or XES file")
        return None

    try:
        if suffix == ".xes":
            log = pm4py.read_xes(str(path))
        else:
            raw_log = pm4py.read_csv(str(path))
            columns = set(getattr(raw_log, "columns", ()))
            required_columns = {"case_id", "activity", "timestamp"}
            missing_columns = sorted(required_columns - columns)
            if missing_columns:
                _report_event_log_issue(
                    f"CSV event log is missing required columns: {', '.join(missing_columns)}"
                )
                return None
            if len(raw_log) == 0:
                _report_event_log_issue("event log is empty")
                return None
            log = pm4py.format_dataframe(
                raw_log,
                case_id="case_id",
                activity_key="activity",
                timestamp_key="timestamp",
            )
    except Exception:
        _report_event_log_issue("event log could not be read or validated")
        return None

    try:
        if len(log) == 0:
            _report_event_log_issue("event log is empty")
            return None
    except TypeError:
        _report_event_log_issue("event log has an invalid structure")
        return None
    return log


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

    try:
        path = Path(event_log_path)
    except TypeError:
        _report_event_log_issue("event log path must be a valid file path")
        return []
    if not path.is_file():
        return []

    log = _load_event_log(path, pm4py)
    if log is None:
        return []

    try:
        pm4py.discover_process_tree_inductive(log)
        variants = pm4py.get_variants_as_tuples(log)
    except Exception:
        _report_event_log_issue("event log could not be analyzed")
        return []
    if not variants:
        return []

    most_common = max(variants.values(), key=len)
    outliers = sum(len(cases) for variant, cases in variants.items() if variant != most_common)
    if outliers == 0:
        return []

    known_ids = {task.id for task in graph.tasks}
    activity_names = {
        step.lower() for step in most_common if isinstance(step, str)
    }
    affected = [task.id for task in graph.tasks if task.name.lower() in activity_names]
    if not affected:
        affected = list(known_ids)[:1]

    return [Flaw(
        task_ids=affected,
        type="logic",
        severity="medium",
        description=f"Process mining found {outliers} case(s) on a path different from the dominant discovered process tree.",
        suggested_fix="Inspect the variant cases for rework, skipped controls, or undocumented exception paths and update the workflow model.",
    )]
