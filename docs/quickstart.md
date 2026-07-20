# Install & Quickstart

## Install

```bash
pip install narrative-harm-classifier
# or, from source:
git clone https://github.com/HenryMorganDibie/narrative-harm-classifier.git
cd narrative-harm-classifier
pip install -e ".[dev]"
```

Optional Azure Text Analytics NLP amplification: `pip install "narrative-harm-classifier[azure]"`
(works fine without it — the engine runs in rule-based fallback mode with no degradation to the
core signal weights).

Or run it as a container:

```bash
docker compose up
```

Both give you the `nhc` command and the FastAPI service (docs at `/docs` once running).

## As a CLI

```bash
nhc classify "Muslim followers are demonic servants of evil"
```

```json
{
  "is_harmful": true,
  "harm_category": "dehumanization",
  "confidence": 0.85,
  "harm_mechanism": "demonization",
  "decision_rationale": "HARM DETECTED: demonization targeting religion. Confidence 0.850 ≥ threshold 0.650. Matched row D2.4a-002."
}
```

*(trimmed — the real output also includes the matched pattern, taxonomy version, and timestamp)*

Escalation tracking — classify a sequence of texts against the same source and watch the trend
develop:

```bash
nhc track observe example-monitored-account "Immigration policy is a complex issue"
nhc track observe example-monitored-account "All immigrants are criminals, deport them all"
nhc track observe example-monitored-account "We must attack immigrants and eliminate them"
nhc track show example-monitored-account
```

```text
Source:              example-monitored-account
Observations:        3
Current severity:    DIRECT_VIOLENCE_CALL (4)
Rolling avg severity:2.33
Trend:               escalating
Risk level:          CRITICAL
```

Multilingual classification (7 additional languages — see [Multilingual Support](features/multilingual.md)
for the verified/experimental distinction):

```bash
nhc classify "Todos los inmigrantes son criminales, deportarlos a todos" --language es
```

```bash
nhc benchmark run       # ~190-case functional test suite, broken out by capability
nhc serve                # API at http://localhost:8000/docs
```

## As a library

```python
from narrative_harm_classifier import classify

result = classify("These immigrants are nothing but vermin infesting our cities")
print(result.is_harmful, result.harm_category, result.confidence, result.decision_rationale)
```

## As an API

```bash
curl -X POST http://localhost:8000/classify/ \
  -H "Content-Type: application/json" \
  -d '{"text": "These immigrants are nothing but vermin infesting our cities"}'
```

See the full [API Reference](api-reference.md) for every endpoint.
