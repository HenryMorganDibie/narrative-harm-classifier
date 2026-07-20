# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Each release on the
[Releases page](https://github.com/HenryMorganDibie/narrative-harm-classifier/releases) also gets
auto-generated notes grouped by category (see `.github/release.yml`).

## [0.1.2] - 2026-07-20

A rigorous red-team pass using real Nigerian sociopolitical text (banditry, ethnic scapegoating,
Boko Haram, #EndSARS, farmer-herder conflict) surfaced a systemic gap well beyond the original
0.1.1 fix, described below.

### Fixed
- **Plural identity anchors.** None of the `religion`, `race_ethnicity`, or `national_origin`
  identity anchors matched plural demonyms — "Muslims", "Christians", "Blacks", "Americans",
  "Russians", "Africans" all failed to anchor at all (only the singular form matched), the same
  bug class already fixed for `political_affiliation` but never applied elsewhere. This affected
  the entire English pattern file, not just the Nigeria-specific terms added in 0.1.1.
- Criminalization pattern required a word *between* "all"/"every" and the criminalizing noun
  ("All X are terrorists" matched, "X are all terrorists" — noun directly adjacent — did not).
- Added "extremist" and "bandit"/"kidnapper" (0.1.1) to the criminalization vocabulary, and
  "snake(s)" to the animalization vocabulary — both common real-world dehumanizing terms with no
  prior coverage.
- Added 4 regression cases (`ANCHOR-PLURAL-01/02`, `CRIM-EXTREMIST-01`, `ANIM-SNAKE-01`) so these
  specific gaps can't silently reopen. Benchmark suite grew from 234 to 238 cases, still
  1.0 precision / 1.0 recall / 0.0 FPR, 37/37 cross-group consistent.

## [0.1.1] - 2026-07-20

### Added
- Documentation site (MkDocs Material) published to GitHub Pages, with a self-hosted, real HTML
  coverage report regenerated on every push to `main`
- Live classify-only demo (no tracking/database) at
  [narrative-harm-classifier-demo.vercel.app](https://narrative-harm-classifier-demo.vercel.app/),
  running the actual published PyPI package
- Polished architecture overview diagram alongside the detailed Mermaid flowcharts
- `race_ethnicity` identity anchors for Fulani, Hausa, Igbo, and Yoruba, plus a `Fulani people`
  benchmark group for cross-group consistency coverage

### Fixed
- Criminalization pattern only matched "all X are/`'re` criminal/rapist/murderer/thief/terrorist" —
  missed the equally common "every X is a Y" phrasing and didn't recognize "bandit"/"kidnapper" as
  criminalizing terms, so real-world text like "Every Fulani man is a bandit and a kidnapper..."
  went undetected. Broadened the pattern and added a regression case (`CRIM-07`).

[0.1.2]: https://github.com/HenryMorganDibie/narrative-harm-classifier/releases/tag/v0.1.2
[0.1.1]: https://github.com/HenryMorganDibie/narrative-harm-classifier/releases/tag/v0.1.1

## [0.1.0] - 2026-07-19

First public release.

### Added
- Rule-based classification engine (D2.4a spec): 6 harm mechanisms across 3 categories
  (dehumanization, incitement, narrative distortion)
- Escalation-chain tracking across sources over time, with persistent storage (SQLite by default,
  Postgres-ready)
- Templated, HateCheck-style benchmark suite (~190 cases covering explicit/implicit positives,
  negation, counter-speech, obfuscated spelling, and cross-group consistency), enforced as a hard CI
  gate
- Multilingual support: English, Spanish, French, Russian, and Arabic (verified confidence), plus
  Igbo, Yoruba, and Hausa (experimental seed vocabularies)
- Curated dog-whistle / coded-language lexicon, scored through the same signal pipeline as the
  taxonomy
- Counter-narrative guidance: general, templated counter-messaging guidance per harm mechanism
- Provenance: deterministic content hashing on every result, plus a tamper-evident hash chain over
  escalation-tracking history (`nhc track verify`)
- Installable package: PyPI (`pip install narrative-harm-classifier`), Docker, CLI (`nhc`), library
  API, and REST API
- 91% test coverage, enforced in CI (`--cov-fail-under=80`)

[0.1.0]: https://github.com/HenryMorganDibie/narrative-harm-classifier/releases/tag/v0.1.0
