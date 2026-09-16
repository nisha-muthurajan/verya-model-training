from pipeline import get_valid_workflow, get_flaw_report, run_full_pipeline

print("=== Test 1: single requirement, flaw detection only ===")
req = "Build a blog where users can write and read posts."
graph = get_valid_workflow(req)
report = get_flaw_report(graph)

print(f"REQUIREMENT: {req}")
print(f"Safe to proceed: {report.is_safe_to_proceed}")
for f in report.flaws:
    print(f"  [{f.severity.upper()}] ({f.type}) tasks={f.task_ids}: {f.description}")
    print(f"    Fix: {f.suggested_fix}")

print("\n=== Test 2: full pipeline on multiple requirements ===")
test_requirements = [
    "Build a blog where users can write and read posts.",
    "Build a food delivery app with restaurant listings, cart, and live tracking.",
    "Build an internal HR portal for leave requests and approvals.",
]

for req in test_requirements:
    graph, report = run_full_pipeline(req)
    print(f"\nREQUIREMENT: {req}")
    print(f"Tasks: {len(graph.tasks)} | Safe to proceed: {report.is_safe_to_proceed}")
    if report.flaws:
        for f in report.flaws:
            print(f"  [{f.severity.upper()}] ({f.type}) tasks={f.task_ids}: {f.description}")
    else:
        print("  No flaws found.")