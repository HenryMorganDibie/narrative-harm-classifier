# API Reference

Full interactive docs are always available at `/docs` (Swagger UI) or `/openapi.json` on a running
instance.

## `POST /classify/` — classify a single text item

**Request:**
```json
{
  "text": "These immigrants are nothing but vermin infesting our cities",
  "context": "optional surrounding context",
  "language": "en"
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
  "taxonomy_version": "1.0.0",
  "language": "en",
  "language_confidence": "verified",
  "dogwhistle_matched": null,
  "counter_narrative_guidance": "Dehumanizing comparisons (to animals, vermin, disease) are a documented precursor to real-world violence against targeted groups...",
  "content_hash": "f4505a843cabeb7f497910caa9d657d129aa58c47633e42364d402317dd4ff27"
}
```

## Endpoint index

| Endpoint | Purpose |
|---|---|
| `POST /classify/` | Classify a single text item |
| `POST /classify/batch` | Classify up to 100 items |
| `POST /tracking/{source_id}/observe` | Classify and append to a source's history |
| `GET /tracking/{source_id}` | A source's escalation profile (severity, trend, risk level) |
| `GET /tracking` | All tracked sources, sorted by risk |
| `GET /tracking/{source_id}/verify` | Recompute the hash chain and confirm it's intact |
| `POST /benchmark/run` | Run the templated benchmark suite |
| `POST /validate/dehumanization` | Legacy Phase 1 milestone gate (18-sample set) |
| `POST /validate/custom` | Run validation against a custom sample set |
| `GET /health` | App version, taxonomy version, baseline tag, Azure connection status |

## Classification logic (D2.4a spec)

1. **Language vocabulary load** — resolves `language` to a `LanguagePatterns` set; unrecognized codes
   fall back to English with a note in the rationale.
2. **Identity anchor check** — text must reference a target group. Configurable via
   `require_target_present` in the taxonomy YAML.
3. **Harm pattern matching** — regex patterns per `harm_mechanism` across all taxonomy rows, plus a
   dog-whistle lexicon match (English-only) contributing an additional signal through the same
   pipeline.
4. **Suppression** — negation-cue window, counter-speech (reporting + condemnation cues), and
   benign-context heuristics can discard a match before it's scored.
5. **Azure NLP amplification** — optional sentiment amplification; degrades gracefully without
   credentials.
6. **Weighted aggregation** — `score = signal_weight × azure_amplifier`.
7. **Ambiguity resolution** — `highest_weight_wins` for multi-signal conflicts; `conservative`
   tie-break.
8. **Decision** — `score ≥ decision_threshold` → harmful, with a full rationale string, a
   `content_hash`, and (when harmful) `counter_narrative_guidance`.

All classification parameters live in `narrative_harm_classifier/data/taxonomy_v1.yaml`, versioned and
pinned in every `ClassificationResult` for reproducibility.
