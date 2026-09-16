# test_tiebreak_fires.py
from pipeline import get_valid_workflow, decide_algorithms, decide_ai_models

# Deliberately vague requirement — should produce low algorithm_confidence on some tasks
req = "Build a simple internal tool to look up employee records by ID."
graph = get_valid_workflow(req)
algo_report = decide_algorithms(graph, req)

print("Algorithm confidences:")
for d in algo_report.decisions:
    print(f"  [{d.task_id}] confidence={d.confidence} tiebreak={d.requires_human_tiebreak}")

model_report = decide_ai_models(graph, algo_report, risk_tolerance=0.5)
print("\nModel routing:")
for d in model_report.decisions:
    print(f"  [{d.task_id}] {d.chosen_model} tiebreak={d.requires_human_tiebreak}")