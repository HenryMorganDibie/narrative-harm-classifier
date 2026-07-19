# Narrative Harm Classifier

Open-source narrative harm detection: a rule-based classification engine, escalation-chain tracking
across sources over time, and a templated benchmark suite — installable as a library, a CLI, an API,
or a container.

Detects dehumanizing, incitement, and narrative-distortion language against target groups (ethnic,
religious, gender, national-origin, political), and tracks whether a given source's rhetoric is
escalating up the harm ladder (othering → dehumanization → criminalization → violence calls) rather
than treating each text as an isolated event.

---

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

---

## Quickstart

### As a CLI

```bash
nhc classify "These immigrants are nothing but vermin infesting our cities"

nhc track observe my-monitored-account "Immigration policy is a complex issue"
nhc track observe my-monitored-account "All immigrants are criminals, deport them all"
nhc track observe my-monitored-account "We must attack immigrants and eliminate them"
nhc track show my-monitored-account
nhc track list

nhc benchmark run

nhc serve  # API at http://localhost:8000/docs
```

### As a library

```python
from narrative_harm_classifier import classify

result = classify("These immigrants are nothing but vermin infesting our cities")
print(result.is_harmful, result.harm_category, result.confidence, result.decision_rationale)
```

### As an API

```bash
curl -X POST http://localhost:8000/classify/ \
  -H "Content-Type: application/json" \
  -d '{"text": "These immigrants are nothing but vermin infesting our cities"}'
```

---

## Architecture

```
Input Text
    │
    ▼
Identity Anchor Detection ──► No group identity found → NO HARM
    │
    ▼
Azure Text Analytics (sentiment + NER, optional)
    │
    ▼
Multi-Signal Pattern Matching (taxonomy rows)
    │   ├── animalization        ├── criminalization
    │   ├── demonization          ├── direct_call_to_violence
    │   └── objectification       └── false_attribution
    │
    ▼
Weighted Score Aggregation (signal_weight × Azure amplifier)
    │
    ▼
Ambiguity Resolution (highest_weight_wins + conservative tie-break)
    │
    ▼
Threshold Decision → ClassificationResult
    │
    ▼
Escalation Tracking (optional) ──► Observation persisted against a source_id
                                    → SourceProfile (severity trend, risk level)
```

## Project Structure

```
narrative-harm-classifier/
├── pyproject.toml                 # pip-installable package, console script `nhc`
├── Dockerfile / docker-compose.yml
├── narrative_harm_classifier/
│   ├── cli.py                     # `nhc` CLI — classify / serve / track / benchmark
│   ├── api/
│   │   ├── main.py
│   │   └── routes/
│   │       ├── classify.py        # POST /classify + /classify/batch
│   │       ├── validate.py        # POST /validate/dehumanization + /custom
│   │       ├── tracking.py        # POST /tracking/{source_id}/observe, GET /tracking[/{source_id}]
│   │       ├── benchmark.py       # POST /benchmark/run
│   │       └── health.py
│   ├── classifier/
│   │   ├── taxonomy/loader.py     # Versioned taxonomy config loader (cached)
│   │   ├── rules/
│   │   │   ├── engine.py          # Core multi-dimensional classification engine
│   │   │   └── azure_nlp.py       # Azure Text Analytics connector (graceful fallback)
│   │   ├── validators/
│   │   │   ├── performance.py     # Legacy 18-sample held-out validator (Phase 1 gate)
│   │   │   └── benchmark.py       # Templated functional-test benchmark generator + runner
│   │   └── tracking/
│   │       ├── models.py          # Severity ladder, Observation, SourceProfile
│   │       ├── store.py           # SQLAlchemy-backed persistence (SQLite by default, Postgres-ready)
│   │       └── tracker.py         # Trend/risk computation
│   ├── core/
│   │   ├── config.py              # Settings via env vars (pydantic-settings)
│   │   └── models.py              # Pydantic request/response schemas
│   └── data/
│       ├── taxonomy_v1.yaml           # Versioned taxonomy spec, shipped as package data
│       └── benchmark_templates.yaml   # Templated benchmark cases, shipped as package data
├── tests/
│   ├── unit/                      # Engine + tracking unit tests
│   ├── integration/                # Phase 1 milestone validation gate
│   └── benchmark/                  # Benchmark structural tests
└── .github/workflows/ci.yml
```

---

## Escalation-chain tracking

Most moderation tooling scores a single piece of text in isolation. This tracks a **source** — an
account, an outlet, a document stream, any caller-supplied `source_id` — across a sequence of
observations, and computes:

- **current severity** — the harm level of the most recent observation
- **rolling average severity** over a configurable window (default: last 20 observations)
- **trend** — `escalating` / `stable` / `de-escalating`, from a first-half-vs-second-half average
  severity comparison over the window (simple, explainable arithmetic — not a black-box model)
- **risk level** — `low` / `watch` / `elevated` / `critical`, derived from current severity bumped
  up one level when the trend is escalating

The severity ladder (`narrative_harm_classifier/classifier/tracking/models.py`) —
`none < narrative_distortion < demonization/objectification < animalization/criminalization <
direct_call_to_violence` — is a simplified, project-specific model inspired by general
narrative-escalation research. It is **not** a validated academic scale; it exists to give a
consistent, explainable ordering for trend computation.

Persistence uses SQLAlchemy against `DATABASE_URL`/`TRACKING_DB_URL` — SQLite by default (zero
config), Postgres or Azure SQL for real deployments, same code path.

---

## Benchmark suite

The original validation set was 18 hand-picked examples. `narrative_harm_classifier/data/benchmark_templates.yaml`
generates a much larger, systematic test suite (~190 cases) modeled on the
[HateCheck](https://arxiv.org/abs/2012.15606) methodology: templates are tagged with a `test_type` and
slot-filled across five identity groups, so a regression in one specific capability is visible even
when the aggregate looks fine, and the same rhetorical pattern is tested identically across groups
(cross-group consistency).

| test_type | what it checks |
|---|---|
| `explicit_positive` | clear, unambiguous harmful language |
| `implicit_positive` | harmful meaning without trigger words (recall probe) |
| `negation` | the harmful claim is negated — should NOT be flagged |
| `counter_speech` | harmful rhetoric quoted to condemn it — should NOT be flagged |
| `obfuscated_spelling` | trigger words altered to evade literal matching |
| `benign_trigger_word` | standalone hard negatives (trigger words in benign context, some with a group present) |

Run it with `nhc benchmark run` or `POST /benchmark/run`.

**This is expected to show real weaknesses**, not a clean sweep: the current regex engine does not
handle negation, counter-speech, or spelling obfuscation. That's the point of building a real
benchmark — honest measurement instead of a vanity metric. See [CONTRIBUTING.md](CONTRIBUTING.md) for
what a fix would look like.

---

## API Reference

### `POST /classify/` — classify a single text item

**Request:**
```json
{
  "text": "These immigrants are nothing but vermin infesting our cities",
  "context": "optional surrounding context"
}
```

**Response:**
```json
{
  "is_harmful": true,
  "harm_category": "dehumanization",
  "confidence": 0.9,
  "target_type": "national_origin_group",
  "identity_axis": "national_origin",
  "harm_mechanism": "animalization",
  "signals_matched": [...],
  "decision_rationale": "HARM DETECTED: animalization targeting national_origin. Confidence 0.900 ≥ threshold 0.650. Matched row D2.4a-001.",
  "taxonomy_version": "1.0.0"
}
```

### `POST /classify/batch` — classify up to 100 items

### `POST /tracking/{source_id}/observe` — classify and append to a source's history

### `GET /tracking/{source_id}` — a source's escalation profile (severity, trend, risk level)

### `GET /tracking` — all tracked sources, sorted by risk

### `POST /benchmark/run` — run the templated benchmark suite

### `POST /validate/dehumanization` — legacy Phase 1 milestone gate (18-sample set)

### `GET /health` — app version, taxonomy version, baseline tag, Azure connection status

---

## Classification Logic (D2.4a Spec)

1. **Identity anchor check** — text must reference a target group. Configurable via
   `require_target_present` in the taxonomy YAML.
2. **Harm pattern matching** — regex patterns per `harm_mechanism` across all taxonomy rows.
3. **Azure NLP amplification** — optional sentiment amplification; degrades gracefully without
   credentials.
4. **Weighted aggregation** — `score = signal_weight × azure_amplifier`.
5. **Ambiguity resolution** — `highest_weight_wins` for multi-signal conflicts; `conservative`
   tie-break.
6. **Decision** — `score ≥ decision_threshold` → harmful, with a full rationale string.

All classification parameters live in `narrative_harm_classifier/data/taxonomy_v1.yaml`, versioned and
pinned in every `ClassificationResult` for reproducibility.

---

## Configuration

Copy `.env.example` to `.env`. Key settings:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./dev.db` | General DB URL (Postgres/Azure SQL in prod) |
| `TRACKING_DB_URL` | falls back to `DATABASE_URL` | Escalation-tracking store |
| `AZURE_TEXT_ANALYTICS_ENDPOINT` / `_KEY` | unset | Optional NLP amplification |
| `TAXONOMY_CONFIG_PATH` | packaged `taxonomy_v1.yaml` | Override with a custom taxonomy |
| `BENCHMARK_TEMPLATES_PATH` | packaged `benchmark_templates.yaml` | Override with custom benchmark cases |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — how to add a taxonomy row, add a benchmark case, and the
known limitations that make good first contributions.

## License

[Apache License 2.0](LICENSE).
