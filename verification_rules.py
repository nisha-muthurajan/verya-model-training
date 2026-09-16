import re
from schema import VerificationIssue

SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]", "Hardcoded credential-like value found"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key pattern detected"),
    (r"sk-[a-zA-Z0-9]{20,}", "API secret key pattern detected"),
]

SQL_INJECTION_PATTERN = r"(?i)(execute|cursor\.execute)\s*\(\s*[\"'].*%s.*[\"']\s*%"


def rule_based_verification(output: str) -> list[VerificationIssue]:
    issues = []

    for pattern, description in SECRET_PATTERNS:
        match = re.search(pattern, output)
        if match:
            issues.append(VerificationIssue(
                category="security",
                description=description,
                evidence=match.group(0)[:60] + "...",
                severity="critical"
            ))

    if re.search(SQL_INJECTION_PATTERN, output):
        issues.append(VerificationIssue(
            category="policy_violation",
            description="Possible SQL injection risk: string formatting used to build a query instead of parameterized queries",
            evidence="detected string-formatted SQL execute() call",
            severity="high"
        ))

    if not output.strip():
        issues.append(VerificationIssue(
            category="error",
            description="Output is empty",
            evidence="(no content)",
            severity="critical"
        ))

    return issues