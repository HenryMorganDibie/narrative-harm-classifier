# Contributing

## Setup

```bash
git clone https://github.com/HenryMorganDibie/narrative-harm-classifier.git
cd narrative-harm-classifier
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
pytest tests/ -v
```

## Architecture overview

- `classifier/factory.py` — the single place that constructs a `ClassificationEngine`/`EscalationTracker`/
  `BenchmarkRunner`/`PerformanceValidator`. Every API route and CLI command goes through this instead of
  reconstructing dependencies itself — if you're adding a new route or command that needs the engine, use
  `build_engine(settings)` rather than wiring `load_taxonomy` + `AzureNLPClient` + `ClassificationEngine`
  by hand again.
- `classifier/rules/patterns_loader.py` — loads and precompiles a language's vocabulary
  (`data/patterns/<lang>.yaml`) into a `LanguagePatterns` object. `classifier/rules/engine.py` is
  language-agnostic; all per-language vocabulary lives in data, not code.
- `classifier/rules/dogwhistles.py` and `classifier/counter_narrative.py` and `classifier/provenance.py`
  are small, focused modules — see their docstrings and the corresponding README sections
  ([Dog-whistle lexicon](README.md#dog-whistle-lexicon-in-depth),
  [Counter-narrative guidance](README.md#counter-narrative-guidance),
  [Provenance & tamper-evidence](README.md#provenance--tamper-evidence-in-depth)).

## Adding a taxonomy row

Taxonomy rows live in `narrative_harm_classifier/data/taxonomy_v1.yaml`. Each row needs a `row_id`,
`target_type`, `harm_mechanism`, `identity_axis`, `signal_weight`, and `decision_threshold`. Corresponding
regex patterns for a new `harm_mechanism` go under `harm_patterns` in each language file under
`narrative_harm_classifier/data/patterns/` (at minimum `en.yaml` — a harm mechanism only checked in some
languages will simply never fire in the others until someone adds it there too).

If a new `harm_mechanism` should participate in escalation tracking, add it to
`HARM_MECHANISM_SEVERITY` in `narrative_harm_classifier/classifier/tracking/models.py` so it maps to a
severity level.

## Adding or improving a language

Each language is one file: `narrative_harm_classifier/data/patterns/<iso-639-1-code>.yaml`. Copy an
existing file's structure — `identity_anchors` and `harm_patterns` are regex pattern lists per
axis/mechanism; `negation_cues`, `reporting_cues`, `condemnation_cues`, and `benign_context_cues` are
plain literal phrase lists (no regex syntax needed — they're auto-escaped and combined); `obfuscation_map`
is a character-substitution table for Latin-script leetspeak evasion (leave it `{}` for non-Latin
scripts, where that specific evasion technique doesn't apply).

Set `confidence: verified` only if you're confident in the vocabulary's correctness (ideally with
native-speaker review); otherwise use `confidence: experimental` — this is surfaced directly to API
consumers via `language_confidence`, so it's not just a label, don't set it to `verified` optimistically.

**A structural pitfall to check for, found while building the Arabic vocabulary**: languages where
articles, plurals, or other morphology attach directly to a word with no space (Arabic's `ال` definite
article, for example) will silently fail to match a plain `\b(word)\b` pattern on the attached form —
`\bمسلم\b` never matches inside `المسلمون`. If your language has this property, make sure patterns account
for it explicitly (see the comment at the top of `ar.yaml`) rather than assuming `\b` alone is enough.

Add a few cases to `narrative_harm_classifier/data/i18n_smoke_tests.yaml` for your language and run
`nhc benchmark i18n` (or `pytest tests/unit/test_i18n_smoke.py`) to confirm basic detection works.

## Adding a dog-whistle entry

Entries live in `narrative_harm_classifier/data/dogwhistles.yaml`. Each needs a `term`, `harm_mechanism`,
`identity_axis`, `signal_weight`, `decision_threshold` (both below 1.0, with headroom between them the
same way taxonomy rows work), and a `source_note` citing where the term is publicly documented (ADL Hate
Symbols Database, SPLC, or academic literature on coded hate speech) — this lexicon only takes
well-documented terms with a citable source, not personal judgment calls about what sounds coded. Use a
lower `signal_weight`/`decision_threshold` for ambiguous terms with legitimate non-bigoted uses, and a
higher one for unambiguous, purpose-built coded terms (numeric codes, explicit slogans).

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
consistency — this **is** a hard gate: a PR that regresses any of those numbers fails CI. CI also enforces
a minimum 80% coverage (`--cov-fail-under=80`) across `tests/unit tests/integration tests/api`.

## Coverage badge

The coverage badge in the README is a static number (currently ~90%), captured from a real
`pytest --cov` run at the time it was last updated — it is **not** a live badge that recalculates itself
on every push. If you add or remove a meaningful chunk of tested code, regenerate it:

```bash
pytest tests/unit tests/integration tests/api --cov=narrative_harm_classifier --cov-report=term-missing
```

and update the percentage in the badge URL in `README.md`. (A live-updating badge would need a service
like Codecov, which requires the maintainer to connect the repo on codecov.io — not set up here yet.)

## Performance numbers

The numbers in the README's [Performance](README.md#performance) section come from running
[`scripts/measure_performance.py`](scripts/measure_performance.py) — re-run it and update the table if
you change anything in the hot classification path (`classifier/rules/engine.py`).

## How the engine handles negation, counter-speech, and obfuscation

The engine is still a regex/rule engine, not a trained model — these are handled with explainable
heuristics in the suppression pipeline (`_rule_negation`, `_rule_counter_speech`, `_rule_benign_context`
in `narrative_harm_classifier/classifier/rules/engine.py`), reading their cue lists/maps from the active
language's `LanguagePatterns` (`data/patterns/<lang>.yaml`) rather than understanding language in general:

- **Negation** — a matched harm pattern is discarded if a `negation_cues` entry (`not`, `never`, `isn't`,
  `false that`, ...) appears in the ~60 characters immediately before the match. This is a local window,
  not full-sentence parsing, so it can be evaded by negation placed far from the trigger word, or fooled
  by an unrelated negation word elsewhere in a long sentence.
- **Counter-speech** — a match is discarded only when the text contains *both* a `reporting_cues` entry
  ("some say", "calling", "rhetoric claiming", ...) *and* a `condemnation_cues` entry ("dangerous",
  "bigoted", "led to violence", ...). Requiring both reduces false suppression, but a genuinely harmful
  post that happens to use one of these words in a non-condemning way could still slip through.
- **Obfuscated spelling** — each language's `obfuscation_map` (a character-substitution table, e.g.
  `0→o`, `1→i`, `3→e` for English/Spanish/French) is applied and matched alongside the original text. It
  only reverses substitutions in that map — homoglyphs, spacing tricks (`v e r m i n`), or substitutions
  outside the map will not be caught until someone extends the map for that language. Non-Latin-script
  languages (Russian, Arabic) currently have an empty map since Latin-style digit-substitution doesn't
  apply the same way — a real gap for whatever the equivalent evasion technique is in those scripts.
- **Benign-context override** — a language's `benign_context_cues` (pest control, wildlife, film,
  academic theory, ...) suppress a match when present, so a trigger word discussed in an unrelated
  literal context doesn't get flagged just because a group is also named nearby. This is a coarse
  allowlist, not sarcasm/context understanding — it covers the specific hard-negative categories in the
  benchmark, not every possible benign context.

Only English, Spanish, French, Russian, and Arabic have these cue lists populated; Igbo, Yoruba, and
Hausa intentionally have them empty (see [Multilingual support](README.md#multilingual-support-in-depth))
rather than guessed.

**If you find real-world text that evades one of these** (and you will — this is fundamentally a
keyword/heuristic system, not semantic understanding), the fix is almost always to extend the relevant
cue list/map in that language's YAML file, or add a new `harm_patterns` entry, then add a benchmark case
for it so the gap can't silently regress. That's the highest-value kind of contribution here: the
benchmark passing cleanly today means it's clean against *this* test suite, not that evasion is a solved
problem in general.

## Database schema changes (pre-1.0)

`classifier/tracking/store.py` uses `metadata.create_all()`, which creates missing tables but does **not**
alter existing ones. If you add/rename a column (as the provenance hash-chain fields did), delete your
local `dev.db`/`tracking.db` rather than expecting an in-place migration — there's no Alembic-style
migration system yet, which is a reasonable gap pre-1.0 but will need addressing before this is used
somewhere a real schema migration matters.
