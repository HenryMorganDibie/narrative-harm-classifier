# Coverage Report

Test coverage is measured with `pytest-cov` and enforced in CI at a minimum of 80%
(`--cov-fail-under=80`); the actual current figure is **91%**.

**[Open the full, browsable HTML coverage report →](coverage/index.html)**

This report is regenerated and published on every push to `main` (see
`.github/workflows/pages.yml`), so it always reflects the current state of `main` — not a stale
snapshot. It shows exactly which lines are covered per file, which is the honest version of "what
does 91% actually mean" rather than just a single number.

To generate it yourself locally:

```bash
pytest tests/unit tests/integration tests/api --cov=narrative_harm_classifier --cov-report=html
# open htmlcov/index.html
```
