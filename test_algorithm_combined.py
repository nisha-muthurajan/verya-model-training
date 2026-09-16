# test_algorithm_combined.py
from pipeline import get_valid_workflow, decide_algorithms

req = ("Build a product recommendation system that uses machine learning to suggest items, "
       "with 1 million products, high read frequency, and search results needed under 100ms.")

graph = get_valid_workflow(req)
report = decide_algorithms(graph, req)

for d in report.decisions:
    tag = f"[{d.source.upper()}: {d.problem_type}]" if d.source == "ml_benchmark" else "[GENERAL]"
    print(f"\n{tag} [{d.task_id}] {d.chosen_algorithm} (confidence={d.confidence})")
    print(f"  Reasoning: {d.reasoning}")
    print(f"  Human tiebreak: {d.requires_human_tiebreak}")
    for alt in d.alternatives_considered:
        print(f"    Alt: {alt.name} — {alt.pros} | {alt.cons}")