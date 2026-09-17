# test_reputation.py
from pipeline import get_valid_workflow, decide_algorithms, decide_ai_models, record_task_outcome
from reputation_model import get_all_reputation_scores, compute_trust_score
from schema import VerificationReport

req = "Build a blog where users can write and read posts."
graph = get_valid_workflow(req)
algo_report = decide_algorithms(graph, req)
model_report = decide_ai_models(graph, algo_report, risk_tolerance=0.5)

print("=== Before any outcomes recorded ===")
for t in graph.tasks[:2]:
    md = next(d for d in model_report.decisions if d.task_id == t.id)
    rep = compute_trust_score(md.chosen_model, t.type)
    print(f"[{t.type}] {md.chosen_model}: trust={rep.trust_score} ({rep.confidence_level})")

print("\n=== Simulating 15 successful outcomes for gemini-2.5-flash on 'backend' tasks ===")
for i in range(15):
    fake_report = VerificationReport(task_id="sim", passed=True, verifier_agreement=1.0, requires_human_review=False)
    record_task_outcome(
        model_decision=type("obj", (), {"chosen_model": "gemini-2.5-flash"})(),
        task=type("obj", (), {"type": "backend"})(),
        verification_report=fake_report
    )

print("\n=== Simulating 4 failures for openai/gpt-oss-20b on 'backend' tasks ===")
for i in range(4):
    fake_report = VerificationReport(task_id="sim", passed=False, verifier_agreement=1.0, requires_human_review=True)
    record_task_outcome(
        model_decision=type("obj", (), {"chosen_model": "openai/gpt-oss-20b"})(),
        task=type("obj", (), {"type": "backend"})(),
        verification_report=fake_report
    )

print("\n=== All reputation scores after simulated history ===")
for score in get_all_reputation_scores():
    print(f"  {score.model_name} / {score.task_type}: trust={score.trust_score} "
          f"({score.successes}✓ {score.failures}✗, {score.confidence_level})")

print("\n=== Re-run routing for a NEW backend task — does it now avoid the low-trust model? ===")
model_report_2 = decide_ai_models(graph, algo_report, risk_tolerance=0.3)
for d in model_report_2.decisions:
    if d.task_id in [t.id for t in graph.tasks if t.type == "backend"]:
        print(f"  [{d.task_id}] chosen: {d.chosen_model}")