# test_verification.py
from pipeline import verify_output

print("=== Test 1: clean output ===")
clean_code = """
def get_user_by_id(cursor, user_id: int):
    query = "SELECT * FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    return cursor.fetchone()
"""
report = verify_output("t1", "Fetch a user record by ID", clean_code)
print(f"Passed: {report.passed} | Agreement: {report.verifier_agreement} | Human review: {report.requires_human_review}")
for i in report.issues:
    print(f"  [{i.severity.upper()}] ({i.category}) {i.description}")

print("\n=== Test 2: output with a hardcoded secret + SQL injection risk ===")
bad_code = """
import requests

api_key = "sk-proj-abc123def456ghi789jklmno"

def get_user_by_id(user_id):
    query = "SELECT * FROM users WHERE id = %s" % user_id
    cursor.execute(query)
    return cursor.fetchone()
"""
report2 = verify_output("t2", "Fetch a user record by ID", bad_code)
print(f"Passed: {report2.passed} | Agreement: {report2.verifier_agreement} | Human review: {report2.requires_human_review}")
for i in report2.issues:
    print(f"  [{i.severity.upper()}] ({i.category}) {i.description}")
    print(f"    Evidence: {i.evidence}")

print("\n=== Test 3: empty output ===")
report3 = verify_output("t3", "Fetch a user record by ID", "")
print(f"Passed: {report3.passed} | Human review: {report3.requires_human_review}")
for i in report3.issues:
    print(f"  [{i.severity.upper()}] ({i.category}) {i.description}")