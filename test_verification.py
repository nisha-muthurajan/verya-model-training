from verification_rules import rule_based_verification


def test_safe_parameterized_sql_has_no_findings():
    output = 'query = "SELECT * FROM users WHERE id = %s"\ncursor.execute(query, (user_id,))'

    assert rule_based_verification(output) == []


def test_secret_and_sql_injection_findings_are_detected_and_redacted():
    output = 'api_key = "sk-proj-abc123def456ghi789jklmno"\nquery = "SELECT * FROM users WHERE id = %s" % user_id'

    issues = rule_based_verification(output)

    assert [issue.category for issue in issues] == ["security", "policy_violation"]
    assert all("sk-proj" not in issue.evidence for issue in issues)


def test_placeholders_and_non_string_output_are_safe():
    assert rule_based_verification('api_key = "your_api_key"') == []
    assert len(rule_based_verification(None)) == 1
    assert rule_based_verification({"output": "not text"})[0].category == "error"