# Testing Strategy

The test suite combines focused unit checks with pipeline-level regression coverage. Provider integrations are exercised through deterministic local fallbacks or mocked responses so the suite remains repeatable.

Run the suite with `python -m pytest -q`.
