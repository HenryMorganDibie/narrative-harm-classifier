# Limitations

It's worth being explicit about what a rule/heuristic engine like this one structurally cannot do,
rather than implying "the benchmark is clean" means "there are no limitations":

- **Sarcasm and irony** — text that means the opposite of its literal words ("oh sure, THEY'RE the
  real victims here") reads the same as sincere language to a pattern matcher. There's no heuristic
  for this in the current engine.
- **Coverage is 8 languages, not all languages, and 3 of the 8 are seed-vocabulary-only** — Spanish,
  French, Russian, and Arabic get full detection rigor; Igbo, Yoruba, and Hausa are explicitly
  `experimental` (see [Multilingual Support](features/multilingual.md)). Every other language is
  simply not detected at all.
- **General contextual/pragmatic reasoning** — the negation, counter-speech, and benign-context
  heuristics (see [Contributing](contributing.md#how-the-engine-handles-negation-counter-speech-and-obfuscation))
  cover specific, named patterns. They are not a substitute for actually understanding what a
  sentence means in context, and will miss constructions outside what's been explicitly handled.
- **Indirect implication beyond the patterns already added** — the benchmark's `implicit_positive`
  cases pass because specific phrasings were added to `HARM_PATTERNS` after being identified. A
  genuinely novel way of implying the same harm without using any covered phrase or trigger word will
  not be caught until someone notices the gap and adds a pattern for it.
- **Evolving slang and coded language** — the [dog-whistle lexicon](features/dogwhistles.md) is a
  ~12-entry seed list of well-documented terms, not a comprehensive or self-updating one. New
  euphemisms and community-specific coded terms outpace any static list, English-only for now, and
  there's no crowd-sourcing or model-based generalization mechanism yet — only manual curation via PR.

None of this is hidden in the benchmark numbers on purpose — the benchmark measures what it measures
(this specific, versioned test suite), and a clean pass on it is a floor, not a ceiling. If you're
evaluating this for a real deployment, red-team it against your own adversarial examples before
trusting it, and treat [escalation tracking](features/escalation-tracking.md) (a trend across many
observations) as more load-bearing than any single classification.
