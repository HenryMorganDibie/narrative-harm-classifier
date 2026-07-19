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
precision/recall/FPR regress below the thresholds in `taxonomy_v1.yaml`. `tests/benchmark/` asserts the
templated benchmark suite stays at precision 1.0 / recall 1.0 / FPR 0.0 overall and 100% cross-group
consistency — this **is** a hard gate: a PR that regresses any of those numbers fails CI.

## How the engine handles negation, counter-speech, and obfuscation

The engine is still a regex/rule engine, not a trained model — these are handled with explainable
heuristics in `narrative_harm_classifier/classifier/rules/engine.py`, not by understanding language in
general:

- **Negation** (`_is_negated`) — a matched harm pattern is discarded if a negation cue (`not`, `never`,
  `isn't`, `false that`, ...) appears in the ~60 characters immediately before the match. This is a
  local window, not full-sentence parsing, so it can be evaded by negation placed far from the trigger
  word, or fooled by unrelated "not" elsewhere in a long sentence.
- **Counter-speech** (`_is_counter_speech`) — a match is discarded only when the text contains *both* a
  reporting/attribution cue ("some say", "calling", "rhetoric claiming", ...) *and* a condemnation cue
  ("dangerous", "bigoted", "led to violence", ...). Requiring both reduces false suppression, but a
  genuinely harmful post that happens to use one of these words in a non-condemning way could still slip
  through.
- **Obfuscated spelling** (`_deobfuscate`) — a fixed character-substitution map (`0→o`, `1→i`, `3→e`,
  `4→a`, `5→s`, `7→t`, `@→a`, `$→s`) is applied and matched alongside the original text. It only reverses
  substitutions in that map — homoglyphs, spacing tricks (`v e r m i n`), or substitutions outside the map
  will not be caught until someone extends `_LEET_MAP`.
- **Benign-context override** (`_is_benign_context`) — a short allowlist of domain cues (pest control,
  wildlife, film, academic theory, ...) suppresses a match when present, so a trigger word discussed in
  an unrelated literal context doesn't get flagged just because a group is also named nearby. This is a
  coarse allowlist, not sarcasm/context understanding — it covers the specific hard-negative categories in
  the benchmark, not every possible benign context.

**If you find real-world text that evades one of these** (and you will — this is fundamentally a
keyword/heuristic system, not semantic understanding), the fix is almost always to extend the relevant
cue list/map above, or add a new `HARM_PATTERNS` entry, then add a benchmark case for it so the gap
can't silently regress. That's the highest-value kind of contribution here: the benchmark passing cleanly
today means it's clean against *this* test suite, not that evasion is a solved problem in general.
