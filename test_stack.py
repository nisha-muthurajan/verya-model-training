# test_stack.py
from pipeline import get_valid_workflow, decide_stack

req = "Build an e-commerce platform with authentication, product search, payments and order tracking."
graph = get_valid_workflow(req)

print("=== Case A: no stack given (recommend) ===")
result_a = decide_stack(graph)
rec = result_a["recommendation"]
print(f"Summary: {rec.summary}\n")
for c in rec.components:
    print(f"  [{c.category}] {c.name} (confidence={c.confidence}) — {c.reasoning}")

print("\n=== Case B: user gives a stack (validate) ===")
user_stack = {"frontend": "React", "backend": "PHP", "database": "SQLite"}
result_b = decide_stack(graph, user_stack=user_stack)
report = result_b["report"]
print(f"Is compatible: {report.is_compatible}")
for i in report.issues:
    print(f"  [{i.severity.upper()}] ({i.category}) {i.issue}")
    if i.suggested_alternative:
        print(f"    Suggested: {i.suggested_alternative}")