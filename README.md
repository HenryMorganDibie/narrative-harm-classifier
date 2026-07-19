# Narrative Harm Classifier

Open-source narrative harm detection: a rule-based classification engine, escalation-chain tracking
across sources over time, and a templated benchmark suite — installable as a library, a CLI, an API,
or a container.

Detects dehumanizing, incitement, and narrative-distortion language against target groups (ethnic,
religious, gender, national-origin, political), and tracks whether a given source's rhetoric is
escalating up the harm ladder (othering → dehumanization → criminalization → violence calls) rather
than treating each text as an isolated event.

**License:** [Apache 2.0](LICENSE) · **Status:** Phase 2 (see [Status & roadmap](#status--roadmap))

---

## Table of contents

- [Why this exists](#why-this-exists)
- [Install](#install)
- [Quickstart](#quickstart)
- [Core concepts](#core-concepts)
- [Escalation-chain tracking](#escalation-chain-tracking-in-depth)
- [Benchmark suite](#benchmark-suite-in-depth)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [API reference](#api-reference)
- [Classification logic (D2.4a spec)](#classification-logic-d24a-spec)
- [Configuration](#configuration)
- [FAQ](#faq)
- [Status & roadmap](#status--roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Why this exists

Most content-moderation tooling scores a single piece of text and stops there: is *this sentence*
toxic, yes or no. But real-world incitement rarely looks like a single bad sentence — it looks like a
pattern that builds over time. Researchers who study genocide and mass-atrocity prevention (e.g.
Gregory Stanton's "10 Stages of Genocide," the escalation frameworks used by atrocity early-warning
groups) describe a recognizable progression: a group is first "othered," then dehumanized (compared
to animals, vermin, disease), then criminalized, and eventually rhetoric turns to explicit calls for
violence. By the time the violent language shows up, the earlier stages have usually been visible
for a while — the pattern is often more informative than any single post.

This project has two goals:

1. **Classify individual text** for dehumanizing, incitement, and narrative-distortion language
   against a target group — the same job most moderation tools do, done transparently (every
   decision comes with a plain-language rationale, not just a score).
2. **Track a source over time** — a social account, an outlet, a document stream — and surface
   whether its rhetoric is climbing that ladder, so a human reviewer can be pointed at "this account
   is escalating" instead of drowning in individually-unremarkable posts.

It is a **rule-based, transparent system**, not a trained ML model and not a claim to predict
violence. It's deliberately simple and inspectable — every classification and every escalation score
can be explained in plain English — which is a real trade-off against the higher raw accuracy a
large language model might offer. Section [FAQ](#faq) goes into this trade-off directly, and
[Status & roadmap](#status--roadmap) is explicit about what still doesn't work well.

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
```

```json
{
  "is_harmful": true,
  "harm_category": "dehumanization",
  "confidence": 0.9,
  "harm_mechanism": "animalization",
  "decision_rationale": "HARM DETECTED: animalization targeting race_ethnicity. Confidence 0.900 ≥ threshold 0.650. Matched row D2.4a-001."
}
```

*(trimmed — the real output also includes the matched pattern, taxonomy version, and timestamp)*

Escalation tracking — classify a sequence of texts against the same source and watch the trend
develop:

```bash
nhc track observe my-monitored-account "Immigration policy is a complex issue"
nhc track observe my-monitored-account "All immigrants are criminals, deport them all"
nhc track observe my-monitored-account "We must attack immigrants and eliminate them"
nhc track show my-monitored-account
```

```text
Source:              my-monitored-account
Observations:        3
Current severity:    DIRECT_VIOLENCE_CALL (4)
Rolling avg severity:2.33
Trend:               escalating
Risk level:          CRITICAL
```

*(this is real, captured output from running these exact three commands — not illustrative)*

```bash
nhc benchmark run       # ~190-case functional test suite, broken out by capability
nhc serve                # API at http://localhost:8000/docs
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

## Core concepts

A short glossary — useful if you're reading this after hearing a talk about the project rather than
coming in as an engineer.

- **Target group / identity axis** — who the text is about: an ethnic, religious, gender,
  national-origin, or political group. The engine only ever flags harm *against* a named group — text
  with no identifiable target group is never flagged (`require_target_present` in the taxonomy).
- **Harm mechanism** — *how* the text is harmful. Six are currently implemented:
  `animalization`, `demonization`, `objectification`, `criminalization`, `direct_call_to_violence`,
  and `false_attribution`. These map to three broader categories: `dehumanization`, `incitement`,
  and `narrative_distortion`.
- **Taxonomy** — the versioned YAML file (`taxonomy_v1.yaml`) that defines every harm mechanism, its
  detection weight, and its decision threshold. Every classification result is stamped with the
  taxonomy version it was produced under, so results stay reproducible even as the taxonomy evolves.
- **Severity ladder** — a simplified ordering of harm mechanisms from least to most severe
  (`none → narrative_distortion → demonization/objectification → animalization/criminalization →
  direct_call_to_violence`), used only for escalation tracking. It is a project-specific model
  inspired by general atrocity-escalation literature, **not** a validated academic scale — see
  [Escalation-chain tracking](#escalation-chain-tracking-in-depth).
- **Source** — an arbitrary identifier you choose (an account handle, a URL, a document ID) that
  ties a sequence of classified texts together so escalation can be tracked across them.
- **Benchmark test type** — a label on each benchmark case describing *what capability it tests*
  (does the engine handle negation? counter-speech? disguised spelling?), so a single aggregate
  accuracy number can't hide a specific, important blind spot. See
  [Benchmark suite](#benchmark-suite-in-depth).

---

## Escalation-chain tracking (in depth)

Most moderation tooling scores a single piece of text in isolation. This tracks a **source** — an
account, an outlet, a document stream, any caller-supplied `source_id` — across a sequence of
observations, and computes:

- **current severity** — the harm level of the most recent observation
- **rolling average severity** over a configurable window (default: last 20 observations)
- **trend** — `escalating` / `stable` / `de-escalating`, from a first-half-vs-second-half average
  severity comparison over the window (simple, explainable arithmetic — not a black-box model)
- **risk level** — `low` / `watch` / `elevated` / `critical`, derived from current severity bumped
  up one level when the trend is escalating

**Why arithmetic instead of a model?** Because the whole point of this project is that a human
reviewer, an auditor, or a journalist can look at *why* a source was flagged and verify it themselves
— "the last 10 posts averaged severity 2.3 and the second half of the window is worse than the
first half" is checkable by hand. A learned trend model might be more accurate but would trade away
exactly the transparency this tool is trying to offer.

The severity ladder (`narrative_harm_classifier/classifier/tracking/models.py`) —
`none < narrative_distortion < demonization/objectification < animalization/criminalization <
direct_call_to_violence` — is a simplified, project-specific model inspired by general
narrative-escalation research (see [Why this exists](#why-this-exists)). It is **not** a validated
academic scale; it exists to give a consistent, explainable ordering for trend computation, not to
represent a scientifically calibrated risk score.

Persistence uses SQLAlchemy against `DATABASE_URL`/`TRACKING_DB_URL` — SQLite by default (zero
config), Postgres or Azure SQL for real deployments, same code path.

---

## Benchmark suite (in depth)

The original validation set was 18 hand-picked examples, and it reported precision 1.0 / recall
0.875 — numbers that sound clean mostly because the test set was small and easy.
`narrative_harm_classifier/data/benchmark_templates.yaml` instead generates a much larger, systematic
test suite (~190 cases) modeled on the [HateCheck](https://arxiv.org/abs/2012.15606) methodology:
templates are tagged with a `test_type` and slot-filled across five identity groups, so a regression
in one specific capability is visible even when the aggregate looks fine, and the same rhetorical
pattern is tested identically across groups (cross-group consistency — does the engine behave the
same regardless of *which* group is named).

| test_type | what it checks |
|---|---|
| `explicit_positive` | clear, unambiguous harmful language |
| `implicit_positive` | harmful meaning without trigger words (recall probe) |
| `negation` | the harmful claim is negated — should NOT be flagged |
| `counter_speech` | harmful rhetoric quoted to condemn it — should NOT be flagged |
| `obfuscated_spelling` | trigger words altered to evade literal matching |
| `benign_trigger_word` | standalone hard negatives (trigger words in benign context, some with a group present) |

Run it with `nhc benchmark run` or `POST /benchmark/run`. Here is real, current output (not a
projection — this is what the benchmark actually reports as of this taxonomy version):

```text
Taxonomy version: 1.0.0
Total cases:      192

TEST TYPE             N     PRECISION  RECALL   FPR     F1
overall               192   1.0        1.0      0.0     1.0
benign_trigger_word   12    0.0        0.0      0.0     0.0
counter_speech        30    0.0        0.0      0.0     0.0
explicit_positive     60    1.0        1.0      0.0     1.0
implicit_positive     30    1.0        1.0      0.0     1.0
negation              30    0.0        0.0      0.0     0.0
obfuscated_spelling   30    1.0        1.0      0.0     1.0

Cross-group consistency: 36/36 templates consistent across groups
```

(`negation`, `counter_speech`, and `benign_trigger_word` are entirely hard negatives — no positives
exist in those buckets, so precision/recall are mathematically undefined and reported as `0.0` by
convention. **FPR is the number that matters for those rows, and it's `0.0`**: zero false positives.)

This is enforced in CI (`tests/benchmark/`), not just reported — a pull request that regresses
precision, recall, FPR, or cross-group consistency fails the build. The engine now handles negation
(via a negation-cue window before a match), counter-speech (via a reporting-cue + condemnation-cue
heuristic), obfuscated/leetspeak spelling (via character-substitution normalization), and a set of
implicit phrasings (via additional patterns) — see
[CONTRIBUTING.md](CONTRIBUTING.md#how-the-engine-handles-negation-counter-speech-and-obfuscation) for
exactly how each heuristic works and its limits.

**Read that honestly, not as "solved":** a clean pass on this 192-case suite means the engine handles
*this* benchmark's negation, counter-speech, and obfuscation patterns correctly — it does not mean
adversarial evasion is a solved problem in general. These are heuristics (a negation window, a cue-word
allowlist, a fixed character-substitution map), not language understanding, and real-world text will
eventually find phrasings outside them. The point of the benchmark isn't "we're done" — it's that any
future gap like that gets added as a new test case, so it can't regress silently once it's fixed.
That's also why escalation tracking exists alongside single-text classification: a trend across many
observations is more robust than any one classification being right.

The cross-group consistency check also caught a genuine bug during development: several templates fired
for every identity group *except* one political-affiliation phrasing, because the underlying regex only
matched singular forms (`democrat`, not `democrats`). That's fixed now (36/36 consistent), and it's a
good example of what this check is for.

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

## Project structure

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

## API reference

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

## Classification logic (D2.4a spec)

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

## FAQ

**Is this a genocide/violence prediction tool?**
No. It classifies text against a harm taxonomy and tracks whether a source's rhetoric is trending
toward more severe categories over time. It does not predict real-world violence, and the severity
ladder it uses is a simplified, project-specific model *inspired by* general escalation research —
not a validated academic or forecasting instrument. Treat its output as a prioritization signal for
human review, not a verdict.

**How is this different from Perspective API / other toxicity classifiers?**
Most toxicity APIs score a single message for general toxicity. This is narrower and more specific
(it requires a named target group and a specific harm mechanism, not general rudeness), fully
transparent (every decision has a plain-language rationale and a versioned taxonomy behind it, no
black-box model), and adds a temporal dimension (escalation tracking across a source) that most
single-message APIs don't attempt.

**Why rules/regex instead of a machine-learning or LLM-based classifier?**
Transparency and reproducibility were prioritized over raw accuracy: every decision can be traced to
a specific matched pattern and taxonomy row, and results are stable across time given the same
taxonomy version. Negation, counter-speech, and obfuscated spelling are handled through explainable
heuristics (a negation-cue window, a reporting+condemnation cue pair, a character-substitution map —
see [CONTRIBUTING.md](CONTRIBUTING.md#how-the-engine-handles-negation-counter-speech-and-obfuscation))
rather than genuine language understanding, so they generalize only as far as those heuristics reach.
An LLM-assisted or hybrid engine is on the [roadmap](#status--roadmap) for the cases that fall outside
them, and contributions in that direction are welcome.

**Can I use my own taxonomy or add new harm mechanisms?**
Yes — the taxonomy is just a YAML file (`TAXONOMY_CONFIG_PATH` to override it), and the pattern list
per mechanism lives in `classifier/rules/engine.py`. See [CONTRIBUTING.md](CONTRIBUTING.md).

**Does it work in languages other than English?**
Not yet — the identity-anchor and harm-pattern regexes are English-only. This is a known gap and a
[roadmap](#status--roadmap) item, not a design constraint.

**Is the severity ladder / escalation model scientifically validated?**
No, and the README and code comments say so deliberately. It's a simplified, explainable ordering
inspired by general narrative-escalation research (see [Why this exists](#why-this-exists)), built
so a human can audit *why* a trend was flagged — not a peer-reviewed forecasting model.

---

## Status & roadmap

**Currently shipped (Phase 1 + Phase 2):**

- Rule-based classification across 6 harm mechanisms / 3 categories, with optional Azure NLP
  amplification
- Escalation-chain tracking across sources with persistent storage
- A ~190-case templated benchmark suite (precision 1.0 / recall 1.0 / FPR 0.0, 100% cross-group
  consistency, enforced as a CI gate) covering negation, counter-speech, obfuscated spelling, and
  cross-group consistency
- Installable package (`pip`/`docker`), CLI, library API, REST API, CI

**Known limitation:**

- English-only — the identity-anchor and harm-pattern regexes don't yet cover other languages

**Not yet built (ideas, not commitments):**

- Multilingual / low-resource-language support
- A curated dog-whistle / coded-language lexicon layer
- An LLM-assisted or hybrid classification path for the cases regex structurally can't handle
- Counter-narrative / intervention suggestions alongside detection
- Provenance/evidence-hashing for use in documentation or accountability workflows

If you want to work on any of these, open an issue or a PR — see [Contributing](#contributing).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — how to add a taxonomy row, add a benchmark case, and how the
negation/counter-speech/obfuscation heuristics work (and where they'll need extending as new evasion
patterns turn up).

## License

[Apache License 2.0](LICENSE).
