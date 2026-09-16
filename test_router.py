# test_router.py
from pipeline import get_valid_workflow, decide_algorithms, decide_ai_models

req = ("Build an e-commerce platform with authentication, product search, payments and order tracking, "
       "1 million products, <100ms search target.")

graph = get_valid_workflow(req)
algo_report = decide_algorithms(graph, req)

print("=== Cost-optimized (risk_tolerance=0.1) ===")
report_cost = decide_ai_models(graph, algo_report, risk_tolerance=0.1)
for d in report_cost.decisions:
    print(f"  [{d.task_id}] {d.chosen_model} ({d.chosen_provider}) tier={d.required_capability_tier} tiebreak={d.requires_human_tiebreak}")

print("\n=== Capability-optimized (risk_tolerance=0.9) ===")
report_cap = decide_ai_models(graph, algo_report, risk_tolerance=0.9)
for d in report_cap.decisions:
    print(f"  [{d.task_id}] {d.chosen_model} ({d.chosen_provider}) tier={d.required_capability_tier} tiebreak={d.requires_human_tiebreak}")

print("\n=== Detail view: one decision's full reasoning ===")
sample = report_cost.decisions[0]
print(f"Task: {sample.task_id}")
print(f"Reasoning: {sample.reasoning}")
print(f"Breakdown: {sample.complexity_breakdown}")