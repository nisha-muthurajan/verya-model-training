import re
from schema import VerificationIssue

SECRET_PATTERNS = [
    (r"(?i)\b(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]", "Hardcoded credential-like value found"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key pattern detected"),
    (r"\bsk-[a-zA-Z0-9]{20,}\b", "API secret key pattern detected"),
]

SQL_INJECTION_PATTERN = r"(?is)\b(?:cursor\.)?execute\s*\(\s*(['\"])(?=[^'\"]*\b(?:select|insert|update|delete)\b)[^'\"]*%s[^'\"]*\1\s*%"
SQL_FORMAT_PATTERN = r"(?is)(['\"])(?=[^'\"]*\b(?:select|insert|update|delete)\b)[^'\"]*%s[^'\"]*\1\s*%"

PLACEHOLDER_SECRET_VALUES = {
    "changeme", "change_me", "dummy", "example", "placeholder", "password",
    "replace_me", "replace-this", "test", "your_api_key", "your-api-key",
    "your_secret", "your-secret",
}


def _normalized_output(output: object) -> str:
    return output if isinstance(output, str) else ""


def _is_placeholder_secret(match: re.Match[str]) -> bool:
    assignment = re.search(r"=\s*(['\"])(?P<value>[^'\"]*)\1", match.group(0))
    if not assignment:
        return False
    value = assignment.group("value").strip().lower()
    return (
        value in PLACEHOLDER_SECRET_VALUES
        or re.fullmatch(r"(?:<[^>]+>|\$\{[^}]+\})", value) is not None
        or value.startswith("your_")
        or value.startswith("your-")
        or value.startswith("replace_")
        or value.startswith("replace-")
    )


def _redacted_evidence(description: str) -> str:
    return f"{description} (value redacted)"


def rule_based_verification(output: str) -> list[VerificationIssue]:
    output = _normalized_output(output)
    issues = []

    for pattern, description in SECRET_PATTERNS:
        match = re.search(pattern, output)
        if match and not _is_placeholder_secret(match):
            issues.append(VerificationIssue(
                category="security",
                description=description,
                evidence=_redacted_evidence(description),
                severity="critical"
            ))

    if re.search(SQL_INJECTION_PATTERN, output) or re.search(SQL_FORMAT_PATTERN, output):
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