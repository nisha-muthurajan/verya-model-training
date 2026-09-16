# test_full_pipeline.py
from pipeline import run_full_pipeline, verify_and_record
import json

req = "Build an e-commerce platform with authentication, product search, payments and order tracking."

result = run_full_pipeline(req, risk_tolerance=0.4)

print(f"REQUIREMENT: {req}\n")
print(f"Halted early: {result['halted_at']}")

if result["halted_at"] is not None:
    print(f"\n⚠ PIPELINE HALTED — Verya caught a problem before execution\n")
    print(f"Stage: {result['halted_at']}")
    print(f"Reason: {result['halt_reason']}\n")
    print("Details:")
    for f in result["flaws"].flaws:
        print(f"  [{f.severity.upper()}] ({f.type}) — tasks {f.task_ids}")
        print(f"    Problem: {f.description}")
        print(f"    Fix: {f.suggested_fix}\n")
    print("This is Verya's Flaw Detection layer working as intended:")
    print("it stops the pipeline from wasting further API cost on a flawed plan,")
    print("and gives a human a specific, actionable fix rather than a vague warning.")