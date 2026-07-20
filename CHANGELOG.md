# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Each release on the
[Releases page](https://github.com/HenryMorganDibie/narrative-harm-classifier/releases) also gets
auto-generated notes grouped by category (see `.github/release.yml`).

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
