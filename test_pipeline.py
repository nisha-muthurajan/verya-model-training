from pipeline import get_valid_workflow

test_requirements = [
    "Build a blog where users can write and read posts.",
    "Build a task management app with teams and deadlines.",
    "Build a food delivery app with restaurant listings, cart, and live tracking.",
    "Build an internal HR portal for leave requests and approvals.",
]

for req in test_requirements:
    graph = get_valid_workflow(req)
    print(f"\nREQUIREMENT: {req}")
    for t in graph.tasks:
        print(f"  [{t.id}] {t.name} ({t.type}) depends_on={t.depends_on}")