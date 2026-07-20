# Architecture

![Classification pipeline overview](assets/architecture-hero.png)

The diagram above is the high-level shape; every stage below expands into the actual signal-level
decision logic.

```mermaid
flowchart TD
    A["Input text + language"] --> LP["Load language patterns\n(falls back to en if unavailable)"]
    LP --> B{"Identity anchor\ndetected?"}
    B -- "no" --> Z["NO HARM"]
    B -- "yes" --> C["Azure Text Analytics\n(sentiment + NER, optional)"]
    C --> D["Multi-signal pattern matching\n(taxonomy rows, per language)"]
    C --> DW["Dog-whistle lexicon match\n(English-only, requires anchor too)"]

    subgraph M["Harm mechanisms checked"]
        direction LR
        M1["animalization"]
        M2["demonization"]
        M3["objectification"]
        M4["criminalization"]
        M5["direct_call_to_violence"]
        M6["false_attribution"]
    end

    D --> M
    DW --> M
    M --> E{"Negated / counter-speech /\nbenign context?"}
    E -- "yes, suppress" --> Z
    E -- "no" --> F["Weighted score aggregation\n(signal_weight × Azure amplifier)"]
    F --> G["Ambiguity resolution\n(highest_weight_wins + conservative tie-break)"]
    G --> H{"score ≥ decision_threshold?"}
    H -- "no" --> Z
    H -- "yes" --> I["ClassificationResult\n(harm_category, confidence, rationale,\ncounter_narrative_guidance, content_hash)"]
    I -.->|"optional"| J["Escalation tracking:\npersist Observation\n(chained record_hash) against source_id"]
    J --> K["SourceProfile\n(severity trend, risk level)"]
```

Escalation tracking, in sequence — a source is scored on trend, not on any single text in isolation:

```mermaid
sequenceDiagram
    participant U as Caller
    participant E as ClassificationEngine
    participant T as EscalationTracker
    participant D as Store (SQLite/Postgres)

    U->>T: observe(source_id, text_1)
    T->>E: classify(text_1)
    E-->>T: harm_mechanism, severity
    T->>D: persist Observation
    U->>T: observe(source_id, text_2)
    Note over T: ...repeated per new text...
    U->>T: profile(source_id)
    T->>D: fetch observation history (window)
    D-->>T: severities over time
    T-->>U: SourceProfile (trend, risk_level)
```

## Project structure

```text
narrative-harm-classifier/
├── pyproject.toml                 # pip-installable package, console script `nhc`
├── Dockerfile / docker-compose.yml
├── scripts/measure_performance.py # Reproducible latency/memory/throughput measurement
├── narrative_harm_classifier/
│   ├── cli.py                     # `nhc` CLI — classify / serve / track / benchmark
│   ├── api/
│   │   ├── main.py
│   │   └── routes/
│   │       ├── classify.py        # POST /classify + /classify/batch
│   │       ├── validate.py        # POST /validate/dehumanization + /custom
│   │       ├── tracking.py        # POST /tracking/{source_id}/observe|verify, GET /tracking[/{source_id}]
│   │       ├── benchmark.py       # POST /benchmark/run
│   │       └── health.py
│   ├── classifier/
│   │   ├── factory.py             # Shared engine/tracker/runner/validator construction (no duplicated wiring)
│   │   ├── counter_narrative.py   # harm_mechanism -> general counter-messaging guidance
│   │   ├── provenance.py          # content_hash + tamper-evident record_hash chain
│   │   ├── taxonomy/loader.py     # Versioned taxonomy config loader (cached)
│   │   ├── rules/
│   │   │   ├── engine.py          # Core multi-language, multi-signal classification engine
│   │   │   ├── patterns_loader.py # Per-language vocabulary loader (precompiled regex)
│   │   │   ├── dogwhistles.py     # Coded-language lexicon loader + detector
│   │   │   └── azure_nlp.py       # Azure Text Analytics connector (graceful fallback)
│   │   ├── validators/
│   │   │   ├── performance.py     # Legacy 18-sample held-out validator (Phase 1 gate)
│   │   │   ├── benchmark.py       # Templated functional-test benchmark generator + runner
│   │   │   └── i18n_smoke.py      # Per-language smoke test runner
│   │   └── tracking/
│   │       ├── models.py          # Severity ladder, Observation (+ hash chain fields), SourceProfile
│   │       ├── store.py           # SQLAlchemy-backed persistence (SQLite by default, Postgres-ready)
│   │       └── tracker.py         # Trend/risk computation + verify_chain()
│   ├── core/
│   │   ├── config.py              # Settings via env vars (pydantic-settings)
│   │   ├── models.py              # Pydantic request/response schemas
│   │   └── yaml_loader.py         # Shared YAML-load helper (used by every loader above)
│   └── data/
│       ├── taxonomy_v1.yaml           # Versioned taxonomy spec, shipped as package data
│       ├── benchmark_templates.yaml   # Templated benchmark cases, shipped as package data
│       ├── i18n_smoke_tests.yaml      # Small per-language smoke test cases
│       ├── dogwhistles.yaml           # Coded-language lexicon seed list
│       └── patterns/                  # One file per language: en, es, fr, ru, ar, ig, yo, ha
├── tests/
│   ├── unit/                      # Engine, tracking, multilingual, dogwhistle, provenance, CLI tests
│   ├── integration/                # Phase 1 milestone validation gate
│   ├── api/                       # FastAPI route tests
│   └── benchmark/                  # Benchmark structural tests
└── .github/workflows/
```
