# Contributing

## Setup

```bash
git clone https://github.com/HenryMorganDibie/narrative-harm-classifier.git
cd narrative-harm-classifier
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
pytest tests/ -v
```

## Adding a taxonomy row

Taxonomy rows live in `narrative_harm_classifier/data/taxonomy_v1.yaml`. Each row needs a `row_id`,
`target_type`, `harm_mechanism`, `identity_axis`, `signal_weight`, and `decision_threshold`. Corresponding
regex patterns for a new `harm_mechanism` go in `HARM_PATTERNS` in
`narrative_harm_classifier/classifier/rules/engine.py`.

If a new `harm_mechanism` should participate in escalation tracking, add it to
`HARM_MECHANISM_SEVERITY` in `narrative_harm_classifier/classifier/tracking/models.py` so it maps to a
severity level.

## Adding a benchmark case

Benchmark templates live in `narrative_harm_classifier/data/benchmark_templates.yaml`.

- To test a new phrasing for an existing harm mechanism, add a template with a `{group}` placeholder — it
  will automatically be expanded across every group in the `groups` list, which also feeds the
  cross-group-consistency check.
- To add a one-off hard negative that shouldn't be slot-filled, add it to `standalone_cases` instead.
- Every template/case needs a `test_type` (`explicit_positive`, `implicit_positive`, `negation`,
  `counter_speech`, `obfuscated_spelling`, or `benign_trigger_word`) so regressions in a specific capability
  are visible in the per-test-type breakdown, not just the aggregate.

Run `nhc benchmark run` (or `pytest tests/benchmark -v`) to see the effect of your change.

## CI gate

Pull requests run the full test suite plus the Phase 1 milestone gate
(`tests/integration/test_validation.py`), which fails the build if the dehumanization category's
precision/recall/FPR regress below the thresholds in `taxonomy_v1.yaml`. The templated benchmark
(`nhc benchmark run`) is currently informational rather than a hard gate — it's expected to show known
gaps (negation, counter-speech, obfuscated spelling) that are open problems, not regressions to block on.
If you improve one of those, feel free to propose tightening the gate.

## Known limitations (good first contributions)

- The regex engine does not handle negation ("X are NOT vermin" still matches as harmful).
- It does not handle counter-speech (quoting harmful rhetoric to condemn it still matches).
- It does not handle obfuscated/leetspeak spelling ("v3rmin" does not match `vermin`).
- The `political_affiliation` identity anchors in `IDENTITY_ANCHORS`
  (`narrative_harm_classifier/classifier/rules/engine.py`) only match singular forms
  (`democrat`, `republican`, `socialist`, ...), not plurals (`democrats`, `republicans`,
  `socialists`, ...). Since `require_target_present` gates every other check, any text
  naming a political group in the plural is silently classified as "no harm" regardless
  of what else it says — the benchmark's cross-group consistency check
  (`nhc benchmark run`) surfaces this directly: templates that fire for every other
  identity group consistently fail to fire when the group is "Democrats". Fixing the
  regex to `democrats?` etc. (and checking the other axes for the same plural gap) is a
  quick, high-value fix.

These are all visible in `nhc benchmark run` output broken out by `test_type`.
