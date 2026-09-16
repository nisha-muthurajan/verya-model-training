# test_risk.py
from pipeline import get_valid_workflow, decide_algorithms, decide_ai_models, predict_risks

req = ("Build an e-commerce platform with authentication, product search, payments and order tracking, "
       "1 million products, <100ms search target.")

graph = get_valid_workflow(req)
algo_report = decide_algorithms(graph, req)
model_report = decide_ai_models(graph, algo_report, risk_tolerance=0.5)
risk_report = predict_risks(graph, algo_report, model_report)

for p in sorted(risk_report.predictions, key=lambda x: -x.failure_probability):
    print(f"[{p.task_id}] risk={p.failure_probability} severity={p.severity_if_failed}")
    for f in p.risk_factors:
        print(f"    - {f}")