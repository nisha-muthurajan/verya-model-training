# Verya

Verya analyzes a plain-English software requirement through eight stages:

1. Workflow understanding
2. Workflow flaw detection
3. Stack recommendation or validation
4. Algorithm recommendation
5. AI model routing
6. Failure and risk prediction
7. Output verification
8. Reputation update

## Run

From the project folder:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python demo.py
```

The demo prints every task, dependency, selected approach, model rationale, alternatives, risk signals, and verification result.

## Tests

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

## Configuration

Copy `.env.example` to `.env` and add only the provider keys you intend to use. Never commit `.env` or paste keys into source files. Model 1 uses configured workflow APIs when available; set `WORKFLOW_REQUIRE_API=true` to disable the local development fallback.

Optional process-mining input uses CSV or XES event logs:

```python
from pipeline import run_full_pipeline

result = run_full_pipeline(
    "Build an e-commerce platform.",
    event_log_path="events.csv",
)
```

CSV event logs require `case_id`, `activity`, and `timestamp` columns.

## Project Layout

- Root Python modules: the pipeline stages and shared schemas.
- `demo.py`: user-facing end-to-end runner.
- `test_*.py`: regression and integration checks.
- `.env.example`: safe configuration template.
- `docs/`: project documentation.
- `reputation_store.json`: local reputation data.
