# quick_check_flaws.py
from pipeline import get_valid_workflow, get_flaw_report

req = "Build an e-commerce platform with authentication, product search, payments and order tracking."
graph = get_valid_workflow(req)
report = get_flaw_report(graph)

print(f"Safe to proceed: {report.is_safe_to_proceed}\n")
for f in report.flaws:
    print(f"[{f.severity.upper()}] ({f.type}) tasks={f.task_ids}")
    print(f"  {f.description}")
    print(f"  Fix: {f.suggested_fix}\n")