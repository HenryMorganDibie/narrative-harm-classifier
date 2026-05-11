# Narrative Harm Classifier

**Phase 1 — Milestone 2 Implementation**  
AI content moderation backend for detecting narrative harm in online text.

Built with FastAPI + Azure Text Analytics. Implements the D2.4a classification specification with multi-dimensional rule-based logic across targets, identities, harm mechanisms, and decision thresholds.

---

## Phase 1 Validation Results

| Metric | Result | Threshold | Status |
|--------|--------|-----------|--------|
| Precision | **1.000** | ≥ 0.70 | ✅ PASS |
| Recall | **0.875** | ≥ 0.65 | ✅ PASS |
| FPR | **0.000** | ≤ 0.20 | ✅ PASS |

Category: `dehumanization` (priority category, 19-sample held-out validation set)

---

## Architecture

```
Input Text
    │
    ▼
Identity Anchor Detection ──► No group identity found → NO HARM
    │
    ▼
Azure Text Analytics (sentiment + NER)
    │
    ▼
Multi-Signal Pattern Matching (D2.4a taxonomy rows)
    │   ├── animalization
    │   ├── demonization
    │   ├── objectification
    │   ├── criminalization
    │   ├── direct_call_to_violence
    │   └── false_attribution
    │
    ▼
Weighted Score Aggregation (signal_weight × Azure amplifier)
    │
    ▼
Ambiguity Resolution (highest_weight_wins + conservative tie-break)
    │
    ▼
Threshold Decision → ClassificationResult
```

---

## Project Structure

```
narrative-harm-classifier/
├── api/
│   ├── main.py                    # FastAPI app entry point
│   └── routes/
│       ├── classify.py            # POST /classify + POST /classify/batch
│       ├── validate.py            # POST /validate/dehumanization + /validate/custom
│       └── health.py              # GET /health
├── classifier/
│   ├── taxonomy/
│   │   └── loader.py              # Versioned taxonomy config loader (cached)
│   ├── rules/
│   │   ├── engine.py              # Core multi-dimensional classification engine
│   │   └── azure_nlp.py           # Azure Text Analytics connector (graceful fallback)
│   └── validators/
│       └── performance.py         # Precision/Recall/FPR validator + held-out samples
├── core/
│   ├── config.py                  # Settings via env vars (pydantic-settings)
│   └── models.py                  # Pydantic request/response schemas
├── config/
│   └── taxonomy_v1.yaml           # Versioned taxonomy spec (D2.4a rows, thresholds)
├── tests/
│   ├── unit/test_engine.py        # Signal detection, anchor, threshold unit tests
│   └── integration/test_validation.py  # Phase 1 end-to-end milestone gate
├── .env.example
└── requirements.txt
```

---

## Quickstart

### 1. Clone and configure

```bash
git clone <repo-url>
cd narrative-harm-classifier
cp .env.example .env
# Optional: add Azure Text Analytics credentials for NLP amplification
# Works without them (fallback mode) — patterns fire on rule-based signals alone
```

### 2. Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the API

```bash
uvicorn api.main:app --reload
```

API live at `http://localhost:8000/docs`

### 4. Run all tests (including Phase 1 validation gate)

```bash
pytest tests/ -v -s
```

---

## API Reference

### `POST /classify`

Classify a single text item.

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

### `POST /classify/batch`

Classify up to 100 items in a single call.

### `POST /validate/dehumanization`

Run Phase 1 milestone validation against the built-in held-out sample set.
Returns full `ValidationReport` with precision, recall, FPR, TP/FP/TN/FN counts.

### `GET /health`

Returns app version, taxonomy version, baseline tag, Azure connection status.

---

## Classification Logic (D2.4a Spec)

### Signal Resolution Pipeline

1. **Identity anchor check** — text must reference a target group (ethnic, religious, gender, national origin, political). Configurable via `require_target_present` in taxonomy YAML.

2. **Harm pattern matching** — regex patterns per `harm_mechanism` across all taxonomy rows. Patterns reflect harm signal semantics, not just keyword lists.

3. **Azure NLP amplification** — Azure Text Analytics sentiment score amplifies confidence when available. Degrades gracefully to rule-based-only in fallback mode.

4. **Weighted aggregation** — `score = signal_weight × azure_amplifier`. Each row carries its own `signal_weight` (0.70–0.95) and `decision_threshold` (0.55–0.70).

5. **Ambiguity resolution** — `highest_weight_wins` for multi-signal conflicts; `conservative` tie-break (classify as harm when score equals threshold).

6. **Decision** — `score ≥ decision_threshold` → harmful. Full rationale string included in every response.

### Taxonomy Config (versioned)

All classification parameters live in `config/taxonomy_v1.yaml`:

- Taxonomy rows per D2.4a (row_id, target_type, harm_mechanism, identity_axis, signal_weight, decision_threshold)
- Per-category performance thresholds
- Ambiguity resolution rules
- M1 baseline lock flag

Version is pinned in every `ClassificationResult` for M1 baseline reproducibility.

---

## Azure Integration

Set in `.env`:
```
AZURE_TEXT_ANALYTICS_ENDPOINT=https://<resource>.cognitiveservices.azure.com/
AZURE_TEXT_ANALYTICS_KEY=<key>
```

When configured, Azure Text Analytics provides:
- **Sentiment analysis** — negative score amplifies harm confidence
- **Named Entity Recognition** — group/identity entity detection
- **Key phrase extraction** — surface-level signal augmentation

When not configured, the engine runs in **rule-based fallback mode** with full signal_weight applied (no Azure penalty). All 14 tests pass in fallback mode.

---

## Phase 2 Scope (Optional Extension)

- Implement 2–3 additional priority taxonomy rows (`incitement`, `narrative_distortion`)
- Calibration against expanded held-out sample sets
- Edge case and ambiguity handling refinement
- Complete validation workflow for all implemented categories

---

## Test Coverage

| Test | What it validates |
|------|-------------------|
| `test_detects_ethnic_group_anchor` | Race/ethnicity identity detection |
| `test_detects_religious_group_anchor` | Religion identity detection |
| `test_detects_gender_anchor` | Gender identity detection |
| `test_no_anchor_returns_none` | No false anchor positives |
| `test_animalization_pattern` | Core harm pattern matching |
| `test_no_harm_pattern` | No false pattern positives |
| `test_dehumanization_detected` | End-to-end harm classification |
| `test_benign_text_not_harmful` | No false positives on benign text |
| `test_no_identity_anchor_returns_no_harm` | Ambiguity rule enforcement |
| `test_result_has_rationale` | Decision rationale generation |
| `test_result_has_taxonomy_version` | Version traceability |
| `test_confidence_bounded` | Confidence score bounds [0, 1] |
| `test_batch_classify` | Multi-item batch classification |
| `test_dehumanization_end_to_end_validation` | **Phase 1 milestone gate** — P/R/FPR thresholds |
