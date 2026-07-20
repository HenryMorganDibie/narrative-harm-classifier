# Status & Roadmap

## Currently shipped (Phase 1 + Phase 2 + Phase 3)

- Rule-based classification across 6 harm mechanisms / 3 categories, with optional Azure NLP
  amplification
- **Multilingual support**: English, Spanish, French, Russian, Arabic (`verified`), plus Igbo,
  Yoruba, Hausa (`experimental` seed vocabularies) — see [Multilingual Support](features/multilingual.md)
- **Dog-whistle / coded-language lexicon** — a curated, sourced seed list scored through the same
  pipeline as the taxonomy — see [Dog-whistle Lexicon](features/dogwhistles.md)
- **Counter-narrative guidance** — general, templated guidance per harm mechanism on harmful
  classifications — see [Counter-Narrative Guidance](features/counter-narrative.md)
- **Provenance / tamper-evidence** — deterministic content hashing plus a tamper-evident hash chain
  for tracked sources, with `nhc track verify` — see [Provenance & Tamper-Evidence](features/provenance.md)
- Escalation-chain tracking across sources with persistent storage
- A ~190-case templated benchmark suite (precision 1.0 / recall 1.0 / FPR 0.0, 100% cross-group
  consistency, enforced as a CI gate) covering negation, counter-speech, obfuscated spelling, and
  cross-group consistency, plus a smaller per-language smoke test suite (`nhc benchmark i18n`)
- Installable package (`pip`/`docker`), CLI, library API, REST API, CI (91% test coverage, enforced)

## Known limitations

- Only 8 languages total, and 3 of those (Igbo, Yoruba, Hausa) are experimental-tier seed
  vocabularies, not full coverage — see [Limitations](limitations.md)
- The dog-whistle lexicon is a ~12-entry seed list, English-only, not comprehensive or self-updating
- Sarcasm, irony, and general contextual/pragmatic reasoning beyond the specific heuristics
  implemented

## Not yet built (ideas, not commitments)

- An LLM-assisted or hybrid classification path for the cases regex structurally can't handle
  (sarcasm, novel implicit phrasing, coded language outside the seed lexicon)
- Multilingual dog-whistle lexicons (currently English-only)
- Native-speaker review of any of the 8 current languages, and expansion beyond them
- Crowd-sourced or automated dog-whistle lexicon updates

If you want to work on any of these, open an issue or a PR — see [Contributing](contributing.md).
