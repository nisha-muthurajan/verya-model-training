# test_php_ml_rule.py
from pipeline import get_valid_workflow, decide_stack

req = "Build a product recommendation system that uses machine learning to suggest items to users."
graph = get_valid_workflow(req)

print("Tasks:")
for t in graph.tasks:
    print(f"  [{t.id}] {t.name} ({t.type})")

user_stack = {"frontend": "React", "backend": "PHP", "database": "PostgreSQL"}
result = decide_stack(graph, user_stack=user_stack)
report = result["report"]

print(f"\nIs compatible: {report.is_compatible}")
for i in report.issues:
    print(f"  [{i.severity.upper()}] ({i.category}) {i.issue}")