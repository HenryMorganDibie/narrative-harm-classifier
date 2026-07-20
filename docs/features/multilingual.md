# Multilingual Support

Seven languages beyond English: **Spanish, French, Russian, Arabic** (`verified` confidence) and
**Igbo, Yoruba, Hausa** (`experimental` confidence). Pass `language` on a request
(`nhc classify TEXT --language es`, or `"language": "es"` in the API body) — an unrecognized code
falls back to English with an explicit note in the rationale rather than silently misclassifying.

## What "verified" vs "experimental" actually means

Spanish, French, Russian, and Arabic get the same detection rigor as English — identity anchors, harm
patterns, and the negation/counter-speech/benign-context suppression cues are all populated. Igbo,
Yoruba, and Hausa are **deliberately smaller seed vocabularies** (a handful of core identity and harm
terms, no negation/counter-speech heuristics yet), because the training-data depth for those three
languages doesn't match the others, and none of the eight languages here — including the "verified"
ones — have been reviewed by a native-speaker domain expert. `language_confidence` on every response
makes this distinction visible in the data, not just in documentation.

## Where the vocabulary lives

Each language's vocabulary lives in its own file under `narrative_harm_classifier/data/patterns/`
(`en.yaml`, `es.yaml`, `fr.yaml`, `ru.yaml`, `ar.yaml`, `ig.yaml`, `yo.yaml`, `ha.yaml`) rather than in
code, so adding or correcting a language doesn't require touching `engine.py` — see
[Contributing](../contributing.md) for the format. A smaller, separate smoke-test suite
(`nhc benchmark i18n`, `data/i18n_smoke_tests.yaml`) checks basic detection works per language — it is
**not** a replication of the English 192-case benchmark; building adversarial negation/counter-speech/
obfuscation test cases with confidence requires a fluency that isn't equally available for all eight
languages.

!!! note "A real Arabic-specific bug found while building this"
    A plain `\b(word)\b` regex never matches a prefixed or suffixed Arabic word, because the definite
    article (`ال`) and plural suffixes attach directly with no space (`مسلم` → `المسلمون`) — extremely
    common in ordinary text, not an edge case. Every Arabic pattern explicitly allows for the attached
    article and common plural forms now; see the comment at the top of `ar.yaml` if you're extending it.
